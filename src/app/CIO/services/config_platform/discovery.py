from __future__ import annotations

from pathlib import Path

from app.CIO.services.config_platform.errors import ConfigDomainNotFoundError


class ConfigDiscovery:
    """Discover configuration domains from the filesystem layout."""

    def __init__(self, base_path: Path | None = None) -> None:
        self.base_path = base_path or Path(__file__).resolve().parents[4] / "config"

    def discover(self) -> dict[str, Path]:
        domains: dict[str, Path] = {}

        departments_dir = self.base_path / "departments"
        if departments_dir.exists():
            for department_dir in sorted(path for path in departments_dir.iterdir() if path.is_dir()):
                for config_file in sorted(department_dir.glob("*.yaml")):
                    domain_name = f"{department_dir.name.lower()}_{config_file.stem}"
                    domains[domain_name] = config_file

        infrastructure_dir = self.base_path / "infrastructure"
        if infrastructure_dir.exists():
            for config_file in sorted(infrastructure_dir.glob("*.yaml")):
                domains[f"cio_{config_file.stem}"] = config_file

        governance_dir = self.base_path / "governance"
        if governance_dir.exists():
            for config_file in sorted(governance_dir.glob("*.yaml")):
                domains[f"ceo_{config_file.stem}"] = config_file

        return domains

    def resolve(self, domain: str) -> Path:
        discovered = self.discover()
        if domain not in discovered:
            raise ConfigDomainNotFoundError(f"Unknown configuration domain: {domain}")
        return discovered[domain]
