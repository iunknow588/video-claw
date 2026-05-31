"""
Video storage backends.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional
import uuid

import httpx

from app.core.config import settings


class VideoStorage(ABC):
    """Abstract video storage backend."""

    @abstractmethod
    async def save_video(
        self,
        *,
        task_uuid: str,
        content: bytes,
        extension: str = ".mp4",
        content_type: str = "video/mp4",
    ) -> str:
        """Persist video bytes and return a public URL."""


class LocalVideoStorage(VideoStorage):
    """Store video files under the local media directory."""

    async def save_video(
        self,
        *,
        task_uuid: str,
        content: bytes,
        extension: str = ".mp4",
        content_type: str = "video/mp4",
    ) -> str:
        root = Path(settings.MEDIA_ROOT)
        video_dir = root / "videos"
        video_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{task_uuid}{extension}"
        file_path = video_dir / filename
        file_path.write_bytes(content)

        if settings.MEDIA_BASE_URL:
            base_url = settings.MEDIA_BASE_URL.rstrip("/")
            return f"{base_url}/videos/{filename}"
        return f"{settings.MEDIA_URL_PREFIX.rstrip('/')}/videos/{filename}"


class GitHubReleaseVideoStorage(VideoStorage):
    """Upload video assets to a GitHub release.

    Suitable only for small demo assets, not for production video workloads.
    """

    async def save_video(
        self,
        *,
        task_uuid: str,
        content: bytes,
        extension: str = ".mp4",
        content_type: str = "video/mp4",
    ) -> str:
        owner = settings.GITHUB_STORAGE_OWNER
        repo = settings.GITHUB_STORAGE_REPO
        token = settings.GITHUB_STORAGE_TOKEN
        tag = settings.GITHUB_STORAGE_RELEASE_TAG
        if not owner or not repo or not token:
            raise ValueError("GitHub storage is not fully configured")

        asset_name = f"{task_uuid}{extension}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            release_resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}",
                headers=headers,
            )
            release_resp.raise_for_status()
            upload_url = release_resp.json()["upload_url"].split("{", 1)[0]
            upload_resp = await client.post(
                f"{upload_url}?name={asset_name}",
                headers={**headers, "Content-Type": content_type},
                content=content,
            )
            upload_resp.raise_for_status()
            return upload_resp.json()["browser_download_url"]


class IPFSVideoStorage(VideoStorage):
    """Upload videos to an IPFS node through the Kubo HTTP API."""

    async def save_video(
        self,
        *,
        task_uuid: str,
        content: bytes,
        extension: str = ".mp4",
        content_type: str = "video/mp4",
    ) -> str:
        filename = f"{task_uuid}{extension}"
        params = {"pin": str(settings.IPFS_PIN_ON_ADD).lower()}
        files = {
            "file": (filename, content, content_type),
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.IPFS_API_URL.rstrip('/')}/api/v0/add",
                params=params,
                files=files,
            )
            response.raise_for_status()
            cid = response.json()["Hash"]
        return f"{settings.IPFS_GATEWAY_URL.rstrip('/')}/{cid}"


class S3CompatibleVideoStorage(VideoStorage):
    """Upload videos to an S3-compatible object storage service."""

    async def save_video(
        self,
        *,
        task_uuid: str,
        content: bytes,
        extension: str = ".mp4",
        content_type: str = "video/mp4",
    ) -> str:
        bucket = settings.S3_BUCKET
        access_key = settings.S3_ACCESS_KEY_ID
        secret_key = settings.S3_SECRET_ACCESS_KEY
        if not bucket or not access_key or not secret_key:
            raise ValueError("S3-compatible storage is not fully configured")

        filename = f"{task_uuid}{extension}"
        key = self._build_object_key(filename)
        await asyncio.to_thread(
            self._put_object,
            bucket=bucket,
            key=key,
            content=content,
            content_type=content_type,
        )
        return self._build_public_url(bucket=bucket, key=key)

    def _build_object_key(self, filename: str) -> str:
        prefix = settings.S3_OBJECT_PREFIX.strip("/")
        if prefix:
            return f"{prefix}/{filename}"
        return filename

    def _put_object(
        self,
        *,
        bucket: str,
        key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for the s3_compatible video storage backend"
            ) from exc

        session = boto3.session.Session()
        client = session.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            region_name=settings.S3_REGION or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    def _build_public_url(self, *, bucket: str, key: str) -> str:
        if settings.S3_PUBLIC_BASE_URL:
            return f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{key}"

        region = settings.S3_REGION.strip()
        if settings.S3_ENDPOINT_URL:
            endpoint = settings.S3_ENDPOINT_URL.rstrip("/")
            return f"{endpoint}/{bucket}/{key}"
        if region:
            return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        return f"https://{bucket}.s3.amazonaws.com/{key}"


def get_video_storage() -> VideoStorage:
    """Factory for configured video storage backend."""
    backend = settings.VIDEO_STORAGE_BACKEND.lower()
    if backend == "local":
        return LocalVideoStorage()
    if backend == "github_release":
        return GitHubReleaseVideoStorage()
    if backend == "ipfs":
        return IPFSVideoStorage()
    if backend == "s3_compatible":
        return S3CompatibleVideoStorage()
    raise ValueError(f"Unsupported video storage backend: {settings.VIDEO_STORAGE_BACKEND}")


def describe_video_storage() -> Dict[str, Any]:
    """Return a sanitized snapshot of the current storage configuration."""
    backend = settings.VIDEO_STORAGE_BACKEND.lower()
    result: Dict[str, Any] = {
        "backend": backend,
        "media_url_prefix": settings.MEDIA_URL_PREFIX,
        "recommended_for_current_stage": "local" if backend == "local" else "s3_compatible",
    }

    if backend == "local":
        result.update(
            {
                "configured": True,
                "media_root": settings.MEDIA_ROOT,
                "public_base_url": settings.MEDIA_BASE_URL,
            }
        )
        return result

    if backend == "github_release":
        result.update(
            {
                "configured": bool(
                    settings.GITHUB_STORAGE_OWNER
                    and settings.GITHUB_STORAGE_REPO
                    and settings.GITHUB_STORAGE_TOKEN
                ),
                "owner": settings.GITHUB_STORAGE_OWNER or None,
                "repo": settings.GITHUB_STORAGE_REPO or None,
                "release_tag": settings.GITHUB_STORAGE_RELEASE_TAG,
                "note": "Only suitable for small demo assets.",
            }
        )
        return result

    if backend == "ipfs":
        result.update(
            {
                "configured": bool(settings.IPFS_API_URL and settings.IPFS_GATEWAY_URL),
                "ipfs_api_url": settings.IPFS_API_URL,
                "ipfs_gateway_url": settings.IPFS_GATEWAY_URL,
                "pin_on_add": settings.IPFS_PIN_ON_ADD,
                "note": "IPFS needs pinning or a self-hosted node for stable persistence.",
            }
        )
        return result

    if backend == "s3_compatible":
        result.update(
            {
                "configured": bool(
                    settings.S3_BUCKET
                    and settings.S3_ACCESS_KEY_ID
                    and settings.S3_SECRET_ACCESS_KEY
                ),
                "bucket": settings.S3_BUCKET or None,
                "endpoint_url": settings.S3_ENDPOINT_URL or None,
                "region": settings.S3_REGION or None,
                "object_prefix": settings.S3_OBJECT_PREFIX,
                "public_base_url": settings.S3_PUBLIC_BASE_URL or None,
                "note": "Recommended for formal multi-instance deployment.",
            }
        )
        return result

    result.update(
        {
            "configured": False,
            "note": "Unknown backend configuration.",
        }
    )
    return result


async def download_video_bytes(url: str) -> bytes:
    """Download remote video content."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.content


def build_placeholder_video_bytes(task_uuid: Optional[str] = None) -> bytes:
    """Create placeholder bytes for demo environments without a real video provider."""
    task_ref = task_uuid or str(uuid.uuid4())
    rendered = _build_ffmpeg_placeholder_video_bytes(task_ref)
    if rendered is not None:
        return rendered
    return f"placeholder video content for {task_ref}\n".encode("utf-8")


def _build_ffmpeg_placeholder_video_bytes(task_ref: str) -> bytes | None:
    ffmpeg_binary = shutil.which("ffmpeg")
    if not ffmpeg_binary:
        return None

    with tempfile.TemporaryDirectory(prefix="lobster-video-placeholder-") as temp_dir:
        output_path = Path(temp_dir) / f"{task_ref}.mp4"
        command = [
            ffmpeg_binary,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=540x960:d=1",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=16000:cl=mono",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
        try:
            subprocess.run(
                command,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return output_path.read_bytes()
        except Exception:
            return None
