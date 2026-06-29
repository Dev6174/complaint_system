# pyrefly: ignore [missing-import]
import os
import logging
import uuid
from typing import Optional

logger = logging.getLogger("complaint_system.storage")

# ---------------------------------------------------------------------------
# Storage backend selection
#
# If S3_BUCKET_NAME + AWS credentials are set in env, files go to S3/MinIO.
# Otherwise falls back to local disk (same behaviour as Phase 1/2/3).
# This means the app works in local dev with zero AWS config, and switches
# to object storage automatically in production just by setting env vars.
# ---------------------------------------------------------------------------

_S3_BUCKET = os.getenv("S3_BUCKET_NAME", "")
_S3_REGION = os.getenv("S3_REGION", "ap-south-1")
_S3_ENDPOINT = os.getenv("S3_ENDPOINT_URL", "")   # Set for MinIO; leave blank for AWS
_PRESIGNED_EXPIRY = int(os.getenv("S3_PRESIGNED_EXPIRY_SECONDS", "3600"))  # 1 hour

LOCAL_UPLOAD_DIR = "uploads"
os.makedirs(LOCAL_UPLOAD_DIR, exist_ok=True)

_s3_client = None


def _get_s3_client():
    """Lazy-initialise the boto3 S3 client. Returns None if not configured."""
    global _s3_client
    if _s3_client is not None:
        return _s3_client

    if not _S3_BUCKET:
        return None

    try:
        import boto3
        kwargs = dict(region_name=_S3_REGION)
        if _S3_ENDPOINT:
            kwargs["endpoint_url"] = _S3_ENDPOINT  # MinIO or custom endpoint
        _s3_client = boto3.client("s3", **kwargs)
        logger.info("S3 storage client initialised", extra={"bucket": _S3_BUCKET})
        return _s3_client
    except ImportError:
        logger.warning("boto3 not installed — falling back to local disk storage")
        return None
    except Exception as e:
        logger.error("S3 client init failed — falling back to local disk", extra={"error": str(e)})
        return None


def is_s3_enabled() -> bool:
    return bool(_S3_BUCKET) and _get_s3_client() is not None


# ---------------------------------------------------------------------------
# Save file
# ---------------------------------------------------------------------------

def save_file(content: bytes, ext: str) -> str:
    """
    Saves validated file bytes to the configured storage backend.
    Returns the storage key (filename) used — callers store this in the DB.
    The key is a UUID so filenames are never guessable.
    """
    filename = f"{uuid.uuid4()}{ext}"

    s3 = _get_s3_client()
    if s3 and _S3_BUCKET:
        try:
            content_type_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
                ".mp4": "video/mp4",
            }
            s3.put_object(
                Bucket=_S3_BUCKET,
                Key=filename,
                Body=content,
                ContentType=content_type_map.get(ext, "application/octet-stream"),
                # Files are private — served via presigned URLs only
                ACL="private",
            )
            logger.info("File saved to S3", extra={"key": filename, "bucket": _S3_BUCKET})
            return filename
        except Exception as e:
            logger.error("S3 upload failed, falling back to local disk", extra={"error": str(e)})

    # Local disk fallback
    path = os.path.join(LOCAL_UPLOAD_DIR, filename)
    with open(path, "wb") as f:
        f.write(content)
    logger.info("File saved to local disk", extra={"path": path})
    return filename


# ---------------------------------------------------------------------------
# Generate access URL
# ---------------------------------------------------------------------------

def get_file_url(filename: str, base_url: str = "") -> str:
    """
    Returns a URL for accessing the file.

    S3 mode: returns a presigned URL valid for S3_PRESIGNED_EXPIRY_SECONDS.
    Local mode: returns the /uploads/{filename} route on this server.

    Presigned URLs mean:
    - Files are never publicly accessible by default (ACL=private)
    - Each URL is time-limited — no permanent guessable links
    - The app server is not in the data path for downloads (S3 serves directly)
    """
    s3 = _get_s3_client()
    if s3 and _S3_BUCKET:
        try:
            url = s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": _S3_BUCKET, "Key": filename},
                ExpiresIn=_PRESIGNED_EXPIRY,
            )
            logger.info(
                "Presigned URL generated",
                extra={"key": filename, "expiry_seconds": _PRESIGNED_EXPIRY},
            )
            return url
        except Exception as e:
            logger.error("Presigned URL generation failed", extra={"error": str(e)})

    # Local fallback
    return f"{base_url}/uploads/{filename}"


# ---------------------------------------------------------------------------
# Delete file (used when an issue is deleted)
# ---------------------------------------------------------------------------

def delete_file(filename: str) -> None:
    """Deletes a file from whichever backend is active. Silent on missing files."""
    s3 = _get_s3_client()
    if s3 and _S3_BUCKET:
        try:
            s3.delete_object(Bucket=_S3_BUCKET, Key=filename)
            logger.info("File deleted from S3", extra={"key": filename})
            return
        except Exception as e:
            logger.error("S3 delete failed", extra={"error": str(e)})

    path = os.path.join(LOCAL_UPLOAD_DIR, filename)
    if os.path.exists(path):
        os.remove(path)
        logger.info("File deleted from local disk", extra={"path": path})
