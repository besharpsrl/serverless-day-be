import boto3
import chalicelib.config as config

client = boto3.client('cognito-idp')


def get_user_from_authorizer(context):
    """
    Extract the authorized user from the request context
    :param context: The object passed by API Gateway integration
    :return: a python dict with the users attributes
    """
    if context.get("authorizer"):
        return {
            "email": context["authorizer"]["claims"]["email"],
            "name": context["authorizer"]["claims"]["given_name"],
            "surname": context["authorizer"]["claims"]["family_name"],
            "nickname": context["authorizer"]["claims"].get("nickname"),
            "cognito_name": context["authorizer"]["claims"]["sub"]
        }
    else:
        return False


def get_users_list():
    """
    Get all users from the Cognito user pool
    :return: a list of user objects
    """
    users = client.list_users(UserPoolId=config.COGNITO_USER_POOL_ID)

    result = []
    if users.get("Users"):

        for user in users["Users"]:

            email = ""
            name = ""
            surname = ""

            for attr in user["Attributes"]:
                if attr["Name"] == "email":
                    email = attr["Value"]
                if attr["Name"] == "given_name":
                    name = attr["Value"]
                if attr["Name"] == "family_name":
                    surname = attr["Value"]

            result.append(
                {
                    "email": email,
                    "name": name,
                    "surname": surname,
                }
            )

        return result

    else:
        return False


def find_user_from_uuid(uuid):
    """
    if inds ad returns a user dict given the user uuid (cognito name)
    :param uuid: the uuid (cognito name/sub) of the user to find
    :return: a python dict with user details
    """
    users = client.list_users(UserPoolId=config.COGNITO_USER_POOL_ID, Filter="username=\"%s\"" % uuid)
    if users.get("Users"):

        email = ""
        name = ""
        surname = ""
        nickname = ""
        cognito_name = ""

        for attr in users["Users"][0]["Attributes"]:
            if attr["Name"] == "email":
                email = attr["Value"]
            if attr["Name"] == "given_name":
                name = attr["Value"]
            if attr["Name"] == "family_name":
                surname = attr["Value"]
            if attr["Name"] == "sub":
                cognito_name = attr["Value"]
            if attr["Name"] == "nickname":
                nickname = attr["Value"]

        return {
            "email": email,
            "name": name,
            "surname": surname,
            "nickname": nickname,
            "cognito_name": cognito_name
        }

    else:
        return False

