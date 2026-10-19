'''
Reads and writes shared files by key, e.g. "models/latest.json".
With S3_BUCKET set (AWS) the files live in S3, otherwise in the local
artifacts/ folder, so the same code runs on a laptop and in the cloud.

On AWS no keys are needed: boto3 uses the EC2 instance's IAM role.
'''

import json
import shutil
from pathlib import Path

from .config import S3_BUCKET, AWS_REGION, LOCAL_ARTIFACTS_DIR

_s3 = None

def _client():
    global _s3
    if _s3 is None:
        import boto3 # Only needed on AWS
        _s3 = boto3.client('s3', region_name=AWS_REGION)
    return _s3

def location(key: str) -> str:
    '''Where a key lives, for logs and for tools like DuckDB that read paths'''
    return f's3://{S3_BUCKET}/{key}' if S3_BUCKET else str(LOCAL_ARTIFACTS_DIR / key)

def upload(local_path, key: str):
    if S3_BUCKET:
        _client().upload_file(str(local_path), S3_BUCKET, key)
    else:
        target = LOCAL_ARTIFACTS_DIR / key
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(local_path, target)

def download(key: str, local_path) -> Path:
    local_path = Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)
    if S3_BUCKET:
        _client().download_file(S3_BUCKET, key, str(local_path))
    else:
        shutil.copyfile(LOCAL_ARTIFACTS_DIR / key, local_path)
    return local_path

def write_json(key: str, data: dict):
    body = json.dumps(data, indent=2)
    if S3_BUCKET:
        _client().put_object(Bucket=S3_BUCKET, Key=key, Body=body.encode(), ContentType='application/json')
    else:
        target = LOCAL_ARTIFACTS_DIR / key
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body)

def read_json(key: str) -> dict | None:
    '''Returns None if the key doesn't exist'''
    if S3_BUCKET:
        try:
            body = _client().get_object(Bucket=S3_BUCKET, Key=key)['Body'].read()
        except _client().exceptions.NoSuchKey:
            return None
        return json.loads(body)
    path = LOCAL_ARTIFACTS_DIR / key
    return json.loads(path.read_text()) if path.exists() else None
