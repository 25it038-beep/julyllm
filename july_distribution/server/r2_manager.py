"""
HS AI SOLUTIONS â€” JULY CLOUDFLARE R2 DISTRIBUTION GATEWAY
Layer: STORAGE GATEWAY (july_distribution.server.r2_manager)
Studio Portal: https://hs-ai-studio-4i7i-git-main-harshanseliyan28-1638s-projects.vercel.app/
Product: JULY LLM 3B | Family: HS AI FAMILY

Connects control server to private Cloudflare R2 bucket:
- Verifies remote GGUF metadata via HeadObject.
- Generates short-lived presigned URLs for authenticated clients.
- Enforces private bucket isolation: bucket is NEVER made public.
- Never exposes permanent Cloudflare credentials to clients.
"""

from __future__ import annotations
import os
from typing import Dict, Any, Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


class CloudflareR2DistributionGateway:
    """
    Server-side gateway managing presigned download authorizations to Cloudflare R2.
    """

    def __init__(
        self,
        endpoint_url: str = "https://21e5f9f23e1d60cb56bf1200e89255f3.r2.cloudflarestorage.com/",
        bucket_name: str = "july",
        profile_name: str = "july-r2"
    ):
        self.endpoint_url = os.getenv("JULY_R2_ENDPOINT", endpoint_url)
        self.bucket_name = os.getenv("JULY_R2_BUCKET", bucket_name)
        self.profile_name = os.getenv("AWS_PROFILE", profile_name)
        self._s3_client = None

    def get_client(self):
        if self._s3_client is not None:
            return self._s3_client

        if os.getenv("AWS_ACCESS_KEY_ID") and os.getenv("AWS_SECRET_ACCESS_KEY"):
            session = boto3.Session(
                aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
                aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
                region_name="auto"
            )
        else:
            try:
                session = boto3.Session(profile_name=self.profile_name, region_name="auto")
            except Exception:
                session = boto3.Session(region_name="auto")

        cfg = Config(
            signature_version="s3v4",
            retries={"max_attempts": 3, "mode": "standard"},
            connect_timeout=10,
            read_timeout=30
        )

        self._s3_client = session.client(
            "s3",
            endpoint_url=self.endpoint_url,
            config=cfg
        )
        return self._s3_client

    def verify_object_head(self, object_key: str = "july-final.gguf") -> Dict[str, Any]:
        """Performs HeadObject to verify object presence, length, and ETag."""
        client = self.get_client()
        try:
            head = client.head_object(Bucket=self.bucket_name, Key=object_key)
            return {
                "success": True,
                "bucket": self.bucket_name,
                "key": object_key,
                "content_length": head.get("ContentLength"),
                "etag": head.get("ETag", "").strip('"'),
                "last_modified": str(head.get("LastModified"))
            }
        except ClientError as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_short_lived_download_url(
        self,
        object_key: str = "july-final.gguf",
        expires_in_seconds: int = 900
    ) -> str:
        """
        Generates a 15-minute presigned GET URL for an authorized client.
        The client retrieves the file directly from R2 using Range requests without storing permanent keys.
        """
        client = self.get_client()
        # Cap between 60 seconds and 3600 seconds
        expiry = max(60, min(3600, expires_in_seconds))
        url = client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": object_key},
            ExpiresIn=expiry
        )
        return url

