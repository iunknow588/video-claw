from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from departments.CIO.services.config_platform.discovery import ConfigDiscovery
from departments.CIO.services.config_platform.errors import ConfigValidationError
from departments.CIO.skills.config_read import ConfigReadSkill
from departments.CIO.skills.config_transform import ConfigTransformSkill
from departments.CIO.skills.config_validate import ConfigValidateSkill


@dataclass(slots=True)
class CacheEntry:
    domain: str
    path: Path
    model_class: str
    config: Any
    mtime_ns: int
    size: int
    fingerprint: str


class ConfigManager:
    """Central agent that coordinates config skills, caching, and versioning."""

    def __init__(self, discovery: ConfigDiscovery | None = None) -> None:
        self.discovery = discovery or ConfigDiscovery()
        self._cache: dict[str, CacheEntry] = {}
        self._versions: dict[str, int] = {}
        self._read_skill = ConfigReadSkill()
        self._validate_skill = ConfigValidateSkill()
        self._transform_skill = ConfigTransformSkill()

    def load_config(
        self,
        *,
        domain: str,
        model_class: str,
        path: Path | None = None,
        force_reload: bool = False,
    ) -> Any:
        config_path = path or self.discovery.resolve(domain)
        stat_result = config_path.stat()
        current_mtime_ns = stat_result.st_mtime_ns
        current_size = stat_result.st_size
        cached = self._cache.get(domain)
        if (
            not force_reload
            and cached is not None
            and cached.path == config_path
            and cached.model_class == model_class
            and cached.mtime_ns == current_mtime_ns
            and cached.size == current_size
        ):
            current_fingerprint = self._fingerprint(config_path)
            if cached.fingerprint == current_fingerprint:
                return cached.config

        read_result = self._read_skill.execute({"path": str(config_path)})
        current_fingerprint = self._fingerprint(config_path)
        validate_result = self._validate_skill.execute(
            {
                "data": read_result["data"],
                "model_class": model_class,
            }
        )
        if not validate_result["valid"]:
            raise ConfigValidationError(domain, validate_result["errors"])

        transform_result = self._transform_skill.execute(
            {
                "data": validate_result["normalized_data"],
                "model_class": model_class,
            }
        )
        self._cache[domain] = CacheEntry(
            domain=domain,
            path=config_path,
            model_class=model_class,
            config=transform_result["instance"],
            mtime_ns=current_mtime_ns,
            size=current_size,
            fingerprint=current_fingerprint,
        )
        self._versions[domain] = self._versions.get(domain, 0) + 1
        return transform_result["instance"]

    def invalidate_cache(self, domain: str | None = None) -> None:
        if domain is not None:
            self._cache.pop(domain, None)
            self._versions[domain] = self._versions.get(domain, 0) + 1
            return

        domains = set(self.discovery.discover()) | set(self._versions) | set(self._cache)
        self._cache.clear()
        for name in domains:
            self._versions[name] = self._versions.get(name, 0) + 1

    def reload_domain(self, *, domain: str, model_class: str, path: Path | None = None) -> Any:
        return self.load_config(domain=domain, model_class=model_class, path=path, force_reload=True)

    def version(self, domain: str) -> int:
        return self._versions.get(domain, 0)

    @staticmethod
    def _fingerprint(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()
