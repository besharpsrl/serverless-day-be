import boto3
import chalicelib.config as config

s3 = boto3.resource('s3')


def delete_file(key):
    return s3.Object(config.S3_UPLOADS_BUCKET_NAME, key).delete()
