import chalicelib.connectors.dynamodb as dynamodb
import boto3
import chalicelib.services.s3_service as s3_service
import chalicelib.config as config
from datetime import datetime
from dateutil import parser

client = boto3.client('cognito-idp')
s3 = boto3.client('s3')


def get_documents(user):
    own_docs = dynamodb.get_documents(user["email"])
    shared_docs = dynamodb.get_documents_shared_with("%s#%s#%s" % (user["email"], user["name"], user["surname"]))
    view_data = []

    if own_docs:
        for shared_file in own_docs:

            shares = (shared_file["people"] if shared_file.get("people") else set())
            people = []

            for u in shares:
                attrs = u.split('#')
                people.append({"name": attrs[1], "surname": attrs[2], "email": attrs[0]})

            view_data.append(
                {
                    "share_id": shared_file["share_id"],
                    "uploaded_at": shared_file["uploaded_at"],
                    "expires_at": shared_file["expires_at"],
                    "display_name": shared_file["display_name"],
                    "size": shared_file["size"],
                    "owner": {
                        "name": shared_file["owner_name"],
                        "surname": shared_file["owner_surname"],
                        "email": shared_file["owner"]
                    },
                    "shared_with_others": True if shared_file.get("people") else False,
                    "share_with_you": user["email"] in {item.split('#')[0] for item in shares},
                    "people": people
                }
            )

    if shared_docs:
        for shared_file in shared_docs:

            shares = (shared_file["people"] if shared_file.get("people") else set())
            people = []

            for u in shares:
                attrs = u.split('#')
                people.append({"name": attrs[1], "surname": attrs[2], "email": attrs[0]})

            view_data.append(
                {
                    "share_id": shared_file["share_id"],
                    "uploaded_at": shared_file["uploaded_at"],
                    "expires_at": shared_file["expires_at"],
                    "display_name": shared_file["display_name"],
                    "size": shared_file["size"],
                    "owner": {
                        "name": shared_file["owner_name"],
                        "surname": shared_file["owner_surname"],
                        "email": shared_file["owner"]
                    },
                    "shared_with_others": True if shared_file.get("people") else False,
                    "share_with_you": user["email"] in {item.split('#')[0] for item in shares},
                    "people": people
                }
            )

    return view_data


def delete_document(user, share_id):
    document = dynamodb.get_document(user, share_id)
    if document:
        if s3_service.delete_file(document["s3_key"]):
            dynamodb.insert_audit_log(user, share_id, document["s3_key"], document["display_name"], "deleted")
            return dynamodb.delete_document(user, share_id)
        else:
            return False
    else:
        return False


def get_download_link(user, share_id):
    document = dynamodb.get_file_by_share(share_id)

    people = document.get("people")
    is_shared_with_me = False

    if people:
        is_shared_with_me = ("%s#%s#%s" % (user["email"], user["name"], user["surname"])) in people

    # Security check
    if document["owner"] == user["email"] or is_shared_with_me:

        url = s3.generate_presigned_url(
            ClientMethod='get_object',
            Params={
                'Bucket': config.S3_UPLOADS_BUCKET_NAME,
                'Key': document["s3_key"],
                "ResponseContentDisposition": "attachment; filename=%s" % (document["display_name"])
            }
        )

        dynamodb.insert_audit_log(user, share_id, document["s3_key"], document["display_name"], "downloaded")

        return url

    else:
        return {"Message": "Error, not authorized"}


def share_document(user, share_id, users):
    document = dynamodb.get_document(user, share_id)
    if document:
        # Check sharable
        if 'nosharable@gmail.com' in {mail.split("#")[0] for mail in users}:

            clean_users = [user for user in users if user.split('#')[0] != 'nosharable@gmail.com']
            dynamodb.insert_audit_log(user, share_id, document["s3_key"], document["display_name"],
                                      "sharing with nosharable@gmail.com denied")
            dynamodb.insert_audit_log(user, share_id, document["s3_key"], document["display_name"],
                                      "shared with %s" % clean_users)
            dynamodb.share_document(user["email"], share_id, clean_users)
            return {'forbidden': ['nosharable@gmail.com']}
        else:
            dynamodb.insert_audit_log(user, share_id, document["s3_key"],
                                      document["display_name"], "shared with %s" % users)
            return dynamodb.share_document(user["email"], share_id, users)

    return False


def rename_document(user, share_id, display_name):
    document = dynamodb.get_document(user, share_id)
    if document:
        dynamodb.insert_audit_log(user, share_id, document["s3_key"], document["display_name"],
                                  "renamed to %s" % display_name)
        return dynamodb.rename_document(user["email"], share_id, display_name)

    return False


def expire_old_documents():
    documents = dynamodb.scan_documents()
    now = datetime.now()

    for doc in documents:
        expire_date = parser.parse(doc["expires_at"])

        if expire_date < now:
            if s3_service.delete_file(doc["s3_key"]):
                dynamodb.insert_audit_log({"email": "N/A", "name": "System", "surname": "Daemon"}, doc["share_id"], doc["s3_key"], doc["display_name"], "automatically deleted because expired")
                dynamodb.delete_document({"email": doc["owner"], "name": doc["owner_name"], "surname": doc["owner_surname"]}, doc["share_id"])

