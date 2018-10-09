from chalice import Chalice, CognitoUserPoolAuthorizer, CORSConfig, Rate
import chalicelib.controllers.docs_controller as doc_controller
import chalicelib.controllers.audit_controller as audit_controller
import chalicelib.controllers.s3_controller as s3_controller
import chalicelib.services.user_service as user_service
import chalicelib.config as config
import logging

############## Chalice CONFIG ##########

app = Chalice(app_name='mydoctransfer')
app.debug = True
app.log.setLevel(logging.DEBUG)

authorizer = CognitoUserPoolAuthorizer(config.COGNITO_USER_POOL_NAME, provider_arns=[config.COGNITO_USER_POOL_ARN])

CORS_CONFIG = CORSConfig(
    allow_origin="*",
    allow_headers=['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token'],
    max_age=600,
    expose_headers=['Content-Type', 'X-Amz-Date', 'Authorization', 'X-Api-Key', 'X-Amz-Security-Token'],
    allow_credentials=True
)

########################################


@app.route('/docs', methods=['GET'], authorizer=authorizer, cors=CORS_CONFIG)
def show_documents():
    """
    Shows all available documents for the current authorized users

    :return: an array of document objects or an ampty array if not documents are available
    """
    user = user_service.get_user_from_authorizer(app.current_request.context)
    if user:
        app.log.debug(user)
        documents = doc_controller.get_documents(user)
        return documents if documents else []
    else:
        return {'status': 'Forbidden'}


@app.route('/docs/{share_id}', methods=['POST'], authorizer=authorizer, cors=CORS_CONFIG)
def manage_document(share_id):
    """
    This method is used to fulfill edit or delete action on a particular document.
    A special 'action' field in the request body is required to choose between delete or rename
    If rename action is requested 'new_name' attribute is required.

    :param share_id: the uuid of the document to delete or rename
    :return: An object containing details about the correct operation or a generic forbidden message
    """
    user = user_service.get_user_from_authorizer(app.current_request.context)

    if user and (app.current_request.json_body.get("action") == 'delete'):
        return doc_controller.delete_document(user, share_id)

    if user and (app.current_request.json_body.get("action") == 'rename'):
        return doc_controller.rename_document(user, share_id, app.current_request.json_body.get("new_name"))

    return {'status': 'Forbidden'}


@app.route('/share/{share_id}', methods=['POST'], authorizer=authorizer, cors=CORS_CONFIG)
def share_document(share_id):
    """
    Share a specified document with other users.
    The request body contains an array of users email in 'users' attribute

    :param share_id: the document uuid
    :return: a message with the result of the operation
    """
    user = user_service.get_user_from_authorizer(app.current_request.context)
    inputs = app.current_request.json_body

    users = inputs.get("users")
    result = doc_controller.share_document(user, share_id, users)

    if result and result.get('forbidden') is None:
        return {"message": "Ok"}
    elif result and result.get('forbidden'):
        return {'message': 'Ok', 'forbidden': result.get('forbidden')}
    else:
        return {"message": "Error"}


@app.route('/share/{share_id}', methods=['GET'], authorizer=authorizer, cors=CORS_CONFIG)
def get_download_link(share_id):
    """
    Obtain a signed download link to dirctly download the requested file from Amazon S3
    The link is obtainable only if authentication and authorizations are successfully passed
    :param share_id: the uuid of the document to download
    :return: the link or an error message
    """
    user = user_service.get_user_from_authorizer(app.current_request.context)

    link = doc_controller.get_download_link(user, share_id)
    if link:
        return {
            "download_link": link
        }
    else:
        return {"message": "Forbidden"}


@app.route('/share/users', methods=['GET'], authorizer=authorizer, cors=CORS_CONFIG)
def get_users():
    """
    Get all the users, this method is used by the frontend to populate the select used for the share function
    :return: a list of users with all the required details
    """
    users = user_service.get_users_list()

    if users:
        return users
    else:
        return []


@app.route('/audit', methods=['GET'], authorizer=authorizer, cors=CORS_CONFIG)
def get_audit():
    """
    Retrieve a list of audit objects
    :return: an array of audit objects
    """
    user = user_service.get_user_from_authorizer(app.current_request.context)
    if user:
        audits = audit_controller.get_audit(user)
        return audits if audits else []
    else:
        return {'status': 'Forbidden'}


# ================================ # Triggers # ================================
@app.on_s3_event(bucket=config.S3_UPLOADS_BUCKET_NAME, events=['s3:ObjectCreated:*'])
def react_to_s3_upload(event):
    """
    This method is invoked by CloudWatch events when an object is created in the specified bucket.
    The purpose of this endpint is to move the uploaded document in a safe place, hide it's real name
    and record the ownership and other metadata to the dynamodb table
    :param event: The event context
    :return: The result
    """
    app.log.debug("Object uploaded for bucket: %s, key: %s" % (event.bucket, event.key))
    return s3_controller.transform_s3_upload(event)


@app.schedule(Rate(5, unit=Rate.MINUTES))
def expire_files(event):
    """
    This method is invoked by CloudWatch events every 5 minutes.
    This will delete old files based on the expiration date set
    :param event: the event context
    :return: Th result
    """
    doc_controller.expire_old_documents()
