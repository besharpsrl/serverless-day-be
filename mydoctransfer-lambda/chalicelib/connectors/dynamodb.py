import boto3
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta
import chalicelib.config as config
import uuid
import time

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(config.DYNAMODB_FILE_TABLE_NAME)
audit_table = dynamodb.Table(config.DYNAMODB_AUDIT_TABLE_NAME)


# ====================================== # Files # ======================================
def get_documents(user_email):
    raw_data = table.query(KeyConditionExpression=Key('owner').eq(str(user_email)))

    if raw_data and int(raw_data["Count"]) > 0:
        return raw_data['Items']
    else:
        return []


def get_document(user, share_id):
    raw_data = table.scan(FilterExpression=Attr('share_id').eq(str(share_id)) & Attr('owner').eq(str(user["email"])))

    if raw_data and int(raw_data["Count"]) > 0:
        return raw_data['Items'][0]
    else:
        return False


def delete_document(user, share_id):
    return table.delete_item(Key={"owner": user["email"], "share_id": share_id})


def get_documents_shared_with(full_user):
    raw_data = table.scan(FilterExpression=Attr('people').contains(full_user))

    if raw_data and int(raw_data["Count"]) > 0:
        return raw_data['Items']
    else:
        return []


def insert_document(user, file_name, file_key, size):
    file_object = {
        "owner": user["email"],
        "owner_name": user["name"],
        "owner_surname": user["surname"],
        "display_name": file_name,
        "s3_key": file_key,
        "share_id": uuid.uuid4().hex,
        "sub": user["cognito_name"],
        "size": size,
        "uploaded_at": str(datetime.now()),
        "expires_at": str(datetime.now() + timedelta(hours=1))
    }

    response = table.put_item(Item=file_object)

    # Insert audit log for uploaded file
    insert_audit_log(user, file_object["share_id"], file_key, file_name, "uploaded")

    return response


def get_file_by_share(share_id):
    raw_data = table.query(IndexName='share_id-index', KeyConditionExpression=Key('share_id').eq(str(share_id)))

    if raw_data and int(raw_data["Count"]) > 0:
        return raw_data['Items'][0]
    else:
        return False


def share_document(owner, share_id, users):
    return table.update_item(
        Key={"owner": owner, "share_id": share_id},
        UpdateExpression="SET people=:users",
        ExpressionAttributeValues={':users': users}
    )


def rename_document(owner, share_id, display_name):
    return table.update_item(
        Key={"owner": owner, "share_id": share_id},
        UpdateExpression="SET display_name=:name",
        ExpressionAttributeValues={':name': display_name}
    )


def scan_documents():
    raw_data = table.scan()

    if raw_data and int(raw_data["Count"]) > 0:
        return raw_data['Items']
    else:
        return []


# ====================================== # Audit # ======================================
def insert_audit_log(user, share_id, file_key, file_display_name, action):

    audit_object = {
        "owner": user["email"],
        "owner_name": user["name"],
        "owner_surname": user["surname"],
        "display_name": file_display_name,
        "s3_key": file_key,
        "share_id": share_id,
        "action_time": str(time.time()),
        "display_time": str(datetime.now()),
        "action": action
    }

    response = audit_table.put_item(Item=audit_object)

    return response


def get_audit_logs():
    raw_data = audit_table.scan()
    return raw_data['Items']
