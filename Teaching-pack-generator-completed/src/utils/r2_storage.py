import os

import boto3
from botocore.config import Config


def _get_bucket() -> str:
    bucket = os.getenv("R2_BUCKET")
    if not bucket:
        raise RuntimeError("Missing R2_BUCKET")
    return bucket


def r2_client():
    endpoint = os.getenv("R2_ENDPOINT")
    access_key = os.getenv("R2_ACCESS_KEY_ID")
    secret_key = os.getenv("R2_SECRET_ACCESS_KEY")
    if not endpoint or not access_key or not secret_key:
        raise RuntimeError(
            "Missing R2 config. Required: R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY"
        )
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def upload_bytes_to_r2(
    data: bytes,
    key: str,
    content_type: str = "application/octet-stream",
):
    bucket = _get_bucket()
    s3 = r2_client()
    s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    return key


def upload_fileobj_to_r2(fileobj, key: str, content_type: str = "application/octet-stream"):
    bucket = _get_bucket()
    s3 = r2_client()
    s3.upload_fileobj(fileobj, bucket, key, ExtraArgs={"ContentType": content_type})
    return key


def download_r2_to_path(key: str, local_path: str):
    bucket = _get_bucket()
    s3 = r2_client()
    s3.download_file(bucket, key, local_path)
    return local_path
