import chalicelib.connectors.dynamodb as dynamodb


def get_audit(user):
    if user["nickname"] == "admin":
        return dynamodb.get_audit_logs()

    return False
