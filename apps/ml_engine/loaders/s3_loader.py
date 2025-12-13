import boto3
import os

class S3ModelLoader:

    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )

    def download(self, bucket, key, local_path):
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self.s3.download_file(bucket, key, local_path)
        return local_path

s3_loader = S3ModelLoader()
