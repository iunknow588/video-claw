"""
Video storage backends.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Dict, Optional
import uuid

import httpx

from app.CEO.core.config import settings
from app.CIO.config.schema import StorageConfig
from app.CIO.services.runtime_assets import resolve_project_path


@dataclass(slots=True)
class GitHubStorageRuntime:
    owner: str
    repo: str
    token: str
    release_tag: str


@dataclass(slots=True)
class IPFSStorageRuntime:
    api_url: str
    gateway_url: str
    pin_on_add: bool


@dataclass(slots=True)
class S3StorageRuntime:
    endpoint_url: str
    access_key_id: str
    secret_access_key: str
    bucket: str
    region: str
    object_prefix: str
    public_base_url: str


@dataclass(slots=True)
class StorageRuntime:
    backend: str
    media_root: str
    media_url_prefix: str
    media_base_url: str | None
    github: GitHubStorageRuntime
    ipfs: IPFSStorageRuntime
    s3_compatible: S3StorageRuntime

    @property
    def media_root_path(self) -> Path:
        return resolve_project_path(self.media_root)

    def resolve_path(self, *parts: str) -> Path:
        return self.media_root_path.joinpath(*parts)

    def build_public_url(self, relative_path: str) -> str:
        normalized = relative_path.replace("\\", "/").lstrip("/")
        if self.media_base_url:
            return f"{self.media_base_url.rstrip('/')}/{normalized}"
        return f"{self.media_url_prefix.rstrip('/')}/{normalized}"

    def asset_exists(self, asset_url: str) -> bool:
        if asset_url.startswith(("http://", "https://")):
            return True
        media_prefix = self.media_url_prefix.rstrip("/")
        if media_prefix and asset_url.startswith(media_prefix):
            relative = asset_url[len(media_prefix) :].lstrip("/\\")
            return self.resolve_path(relative).exists()
        return resolve_project_path(asset_url).exists()


def get_storage_runtime() -> StorageRuntime:
    storage: StorageConfig = settings.storage
    return StorageRuntime(
        backend=str(storage.video_backend or "local").lower(),
        media_root=str(storage.media_root or "runtime/media"),
        media_url_prefix=str(storage.media_url_prefix or "/media"),
        media_base_url=storage.media_base_url,
        github=GitHubStorageRuntime(
            owner=str(storage.github.owner or ""),
            repo=str(storage.github.repo or ""),
            token=str(storage.github.token or ""),
            release_tag=str(storage.github.release_tag or "video-assets"),
        ),
        ipfs=IPFSStorageRuntime(
            api_url=str(storage.ipfs.api_url or ""),
            gateway_url=str(storage.ipfs.gateway_url or ""),
            pin_on_add=bool(storage.ipfs.pin_on_add),
        ),
        s3_compatible=S3StorageRuntime(
            endpoint_url=str(storage.s3_compatible.endpoint_url or ""),
            access_key_id=str(storage.s3_compatible.access_key_id or ""),
            secret_access_key=str(storage.s3_compatible.secret_access_key or ""),
            bucket=str(storage.s3_compatible.bucket or ""),
            region=str(storage.s3_compatible.region or ""),
            object_prefix=str(storage.s3_compatible.object_prefix or ""),
            public_base_url=str(storage.s3_compatible.public_base_url or ""),
        ),
    )


def resolve_media_path(*parts: str) -> Path:
    return get_storage_runtime().resolve_path(*parts)


def asset_exists(asset_url: str) -> bool:
    return get_storage_runtime().asset_exists(asset_url)


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

    def __init__(self, runtime: StorageRuntime | None = None) -> None:
        self.runtime = runtime or get_storage_runtime()

    async def save_video(
        self,
        *,
        task_uuid: str,
        content: bytes,
        extension: str = ".mp4",
        content_type: str = "video/mp4",
    ) -> str:
        video_dir = self.runtime.resolve_path("videos")
        video_dir.mkdir(parents=True, exist_ok=True)

        filename = f"{task_uuid}{extension}"
        file_path = video_dir / filename
        file_path.write_bytes(content)
        return self.runtime.build_public_url(f"videos/{filename}")


class GitHubReleaseVideoStorage(VideoStorage):
    """Upload video assets to a GitHub release.

    Suitable only for small demo assets, not for production video workloads.
    """

    def __init__(self, runtime: StorageRuntime | None = None) -> None:
        self.runtime = runtime or get_storage_runtime()

    async def save_video(
        self,
        *,
        task_uuid: str,
        content: bytes,
        extension: str = ".mp4",
        content_type: str = "video/mp4",
    ) -> str:
        owner = self.runtime.github.owner
        repo = self.runtime.github.repo
        token = self.runtime.github.token
        tag = self.runtime.github.release_tag
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

    def __init__(self, runtime: StorageRuntime | None = None) -> None:
        self.runtime = runtime or get_storage_runtime()

    async def save_video(
        self,
        *,
        task_uuid: str,
        content: bytes,
        extension: str = ".mp4",
        content_type: str = "video/mp4",
    ) -> str:
        filename = f"{task_uuid}{extension}"
        params = {"pin": str(self.runtime.ipfs.pin_on_add).lower()}
        files = {
            "file": (filename, content, content_type),
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.runtime.ipfs.api_url.rstrip('/')}/api/v0/add",
                params=params,
                files=files,
            )
            response.raise_for_status()
            cid = response.json()["Hash"]
        return f"{self.runtime.ipfs.gateway_url.rstrip('/')}/{cid}"


class S3CompatibleVideoStorage(VideoStorage):
    """Upload videos to an S3-compatible object storage service."""

    def __init__(self, runtime: StorageRuntime | None = None) -> None:
        self.runtime = runtime or get_storage_runtime()

    async def save_video(
        self,
        *,
        task_uuid: str,
        content: bytes,
        extension: str = ".mp4",
        content_type: str = "video/mp4",
    ) -> str:
        bucket = self.runtime.s3_compatible.bucket
        access_key = self.runtime.s3_compatible.access_key_id
        secret_key = self.runtime.s3_compatible.secret_access_key
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
        prefix = self.runtime.s3_compatible.object_prefix.strip("/")
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
            endpoint_url=self.runtime.s3_compatible.endpoint_url or None,
            region_name=self.runtime.s3_compatible.region or None,
            aws_access_key_id=self.runtime.s3_compatible.access_key_id,
            aws_secret_access_key=self.runtime.s3_compatible.secret_access_key,
        )
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=content,
            ContentType=content_type,
        )

    def _build_public_url(self, *, bucket: str, key: str) -> str:
        if self.runtime.s3_compatible.public_base_url:
            return f"{self.runtime.s3_compatible.public_base_url.rstrip('/')}/{key}"

        region = self.runtime.s3_compatible.region.strip()
        if self.runtime.s3_compatible.endpoint_url:
            endpoint = self.runtime.s3_compatible.endpoint_url.rstrip("/")
            return f"{endpoint}/{bucket}/{key}"
        if region:
            return f"https://{bucket}.s3.{region}.amazonaws.com/{key}"
        return f"https://{bucket}.s3.amazonaws.com/{key}"


def get_video_storage(runtime: StorageRuntime | None = None) -> VideoStorage:
    """Factory for configured video storage backend."""
    storage_runtime = runtime or get_storage_runtime()
    backend = storage_runtime.backend
    if backend == "local":
        return LocalVideoStorage(storage_runtime)
    if backend == "github_release":
        return GitHubReleaseVideoStorage(storage_runtime)
    if backend == "ipfs":
        return IPFSVideoStorage(storage_runtime)
    if backend == "s3_compatible":
        return S3CompatibleVideoStorage(storage_runtime)
    raise ValueError(f"Unsupported video storage backend: {storage_runtime.backend}")


def describe_video_storage(runtime: StorageRuntime | None = None) -> Dict[str, Any]:
    """Return a sanitized snapshot of the current storage configuration."""
    storage_runtime = runtime or get_storage_runtime()
    backend = storage_runtime.backend
    result: Dict[str, Any] = {
        "backend": backend,
        "media_url_prefix": storage_runtime.media_url_prefix,
        "recommended_for_current_stage": "local" if backend == "local" else "s3_compatible",
    }

    if backend == "local":
        result.update(
            {
                "configured": True,
                "media_root": storage_runtime.media_root,
                "public_base_url": storage_runtime.media_base_url,
            }
        )
        return result

    if backend == "github_release":
        result.update(
            {
                "configured": bool(
                    storage_runtime.github.owner
                    and storage_runtime.github.repo
                    and storage_runtime.github.token
                ),
                "owner": storage_runtime.github.owner or None,
                "repo": storage_runtime.github.repo or None,
                "release_tag": storage_runtime.github.release_tag,
                "note": "Only suitable for small demo assets.",
            }
        )
        return result

    if backend == "ipfs":
        result.update(
            {
                "configured": bool(storage_runtime.ipfs.api_url and storage_runtime.ipfs.gateway_url),
                "ipfs_api_url": storage_runtime.ipfs.api_url,
                "ipfs_gateway_url": storage_runtime.ipfs.gateway_url,
                "pin_on_add": storage_runtime.ipfs.pin_on_add,
                "note": "IPFS needs pinning or a self-hosted node for stable persistence.",
            }
        )
        return result

    if backend == "s3_compatible":
        result.update(
            {
                "configured": bool(
                    storage_runtime.s3_compatible.bucket
                    and storage_runtime.s3_compatible.access_key_id
                    and storage_runtime.s3_compatible.secret_access_key
                ),
                "bucket": storage_runtime.s3_compatible.bucket or None,
                "endpoint_url": storage_runtime.s3_compatible.endpoint_url or None,
                "region": storage_runtime.s3_compatible.region or None,
                "object_prefix": storage_runtime.s3_compatible.object_prefix,
                "public_base_url": storage_runtime.s3_compatible.public_base_url or None,
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
