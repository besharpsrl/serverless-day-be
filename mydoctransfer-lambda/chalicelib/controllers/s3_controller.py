import chalicelib.connectors.dynamodb as dynamodb
from chalicelib.services.user_service import find_user_from_uuid
import boto3
import uuid

s3 = boto3.resource('s3')


def transform_s3_upload(event):
    """
    Transform the uploaded file moving it in a secure place and hiding it's original name.
    Object metadata such as ownership, display name and s3 key are stored in a dynamodb table
    :param event:
    :return:
    """
    # check path
    path = event.key.split('/')

    if path[0] == "private":
        user = find_user_from_uuid(path[-2])
        new_key = "secure_store/%s" % (str(uuid.uuid4()))
        size = s3.Object(event.bucket, event.key).content_length
        s3.Object(event.bucket, new_key).copy_from(CopySource="%s/%s" % (event.bucket, event.key))
        s3.Object(event.bucket, event.key).delete()

        return dynamodb.insert_document(user, path[-1], new_key, size)
    else:
        return False

