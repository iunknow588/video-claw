from __future__ import annotations

import os
from pathlib import Path

from app.CEO.core.config import settings
from app.CEO.services.application_runtime import get_application_runtime
from app.CEO.services.control_plane import control_plane
from app.CFO.services.finance_runtime import get_finance_runtime
from app.CIO.services.config_platform import ConfigDiscovery, ConfigManager
from app.CIO.services.database_runtime import get_database_runtime
from app.CIO.services.redis_runtime import get_redis_runtime


def test_split_config_domains_are_discoverable():
    discovery = ConfigDiscovery()
    domains = discovery.discover()

    assert "ceo_application" in domains
    assert "cio_database" in domains
    assert "cio_storage" in domains
    assert "cfo_finance" in domains
    assert "coo_production" in domains
    assert "cso_hotspot" in domains


def test_settings_are_loaded_from_split_config_runtime():
    assert settings.APP_NAME == "AI Video Auto Production Line"
    assert settings.SERVER_PORT == 8000
    assert settings.DAILY_BUDGET == 1000.0
    assert settings.VIDEO_STORAGE_BACKEND == "local"
    assert settings.leaders.scope == "company_system"
    assert settings.leaders.leaders["lead.production"].model == "glm-5.1"
    assert settings.workflow.main_route[0] == "lead.cfo"


def test_config_manager_resolves_env_placeholders(tmp_path: Path, monkeypatch):
    config_root = tmp_path / "config"
    infra_dir = config_root / "infrastructure"
    infra_dir.mkdir(parents=True)
    (infra_dir / "database.yaml").write_text(
        "\n".join(
            [
                'url: "${TEST_DATABASE_URL}"',
                "pool_size: 5",
                "max_overflow: 10",
                "pool_timeout: 20",
                "echo: false",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///tmp/test.db")

    manager = ConfigManager(discovery=ConfigDiscovery(base_path=config_root))
    database_config = manager.load_config(
        domain="cio_database",
        model_class="app.CIO.config.schema.DatabaseConfig",
    )

    assert database_config.url == "sqlite+aiosqlite:///tmp/test.db"


def test_reload_domain_picks_up_updated_config(tmp_path: Path):
    config_root = tmp_path / "config"
    infra_dir = config_root / "infrastructure"
    infra_dir.mkdir(parents=True)
    config_file = infra_dir / "database.yaml"
    config_file.write_text(
        "\n".join(
            [
                'url: "sqlite+aiosqlite:///tmp/first.db"',
                "pool_size: 5",
                "max_overflow: 10",
                "pool_timeout: 20",
                "echo: false",
            ]
        ),
        encoding="utf-8",
    )

    manager = ConfigManager(discovery=ConfigDiscovery(base_path=config_root))
    first = manager.load_config(
        domain="cio_database",
        model_class="app.CIO.config.schema.DatabaseConfig",
    )
    first_version = manager.version("cio_database")

    config_file.write_text(
        "\n".join(
            [
                'url: "sqlite+aiosqlite:///tmp/second.db"',
                "pool_size: 8",
                "max_overflow: 12",
                "pool_timeout: 25",
                "echo: true",
            ]
        ),
        encoding="utf-8",
    )
    second = manager.reload_domain(
        domain="cio_database",
        model_class="app.CIO.config.schema.DatabaseConfig",
    )

    assert first.url == "sqlite+aiosqlite:///tmp/first.db"
    assert second.url == "sqlite+aiosqlite:///tmp/second.db"
    assert second.pool_size == 8
    assert manager.version("cio_database") > first_version


def test_config_manager_invalidates_cache_when_content_changes_without_mtime_change(tmp_path: Path):
    config_root = tmp_path / "config"
    infra_dir = config_root / "infrastructure"
    infra_dir.mkdir(parents=True)
    config_file = infra_dir / "database.yaml"
    config_file.write_text(
        "\n".join(
            [
                'url: "sqlite+aiosqlite:///tmp/alpha.db"',
                "pool_size: 5",
                "max_overflow: 10",
                "pool_timeout: 20",
                "echo: false",
            ]
        ),
        encoding="utf-8",
    )

    manager = ConfigManager(discovery=ConfigDiscovery(base_path=config_root))
    first = manager.load_config(
        domain="cio_database",
        model_class="app.CIO.config.schema.DatabaseConfig",
    )
    first_stat = config_file.stat()

    config_file.write_text(
        "\n".join(
            [
                'url: "sqlite+aiosqlite:///tmp/bravo.db"',
                "pool_size: 5",
                "max_overflow: 10",
                "pool_timeout: 20",
                "echo: false",
            ]
        ),
        encoding="utf-8",
    )
    os.utime(config_file, ns=(first_stat.st_atime_ns, first_stat.st_mtime_ns))

    second = manager.load_config(
        domain="cio_database",
        model_class="app.CIO.config.schema.DatabaseConfig",
    )

    assert first.url == "sqlite+aiosqlite:///tmp/alpha.db"
    assert second.url == "sqlite+aiosqlite:///tmp/bravo.db"


def test_control_plane_defaults_are_loaded_from_governance_config():
    control_plane.reset_defaults()

    leaders = control_plane.list_leaders()
    leader_names = {item["name"] for item in leaders}

    assert control_plane.mission == settings.leaders.mission
    assert control_plane.managed_scope == settings.leaders.scope
    assert "lead.cfo" in leader_names
    assert "lead.production" in leader_names


def test_finance_runtime_is_loaded_from_cfo_config():
    runtime = get_finance_runtime()

    assert runtime.daily_budget == 1000.0
    assert runtime.warning_threshold == 0.8
    assert runtime.alert_threshold == 1.0
    assert runtime.critical_threshold == 1.2
    assert runtime.usage_ratio(500.0) == 0.5
    assert runtime.alert_level(1300.0) == "critical"


def test_application_runtime_is_loaded_from_ceo_config():
    runtime = get_application_runtime()

    assert runtime.name == "AI Video Auto Production Line"
    assert runtime.version == "1.0.0"
    assert runtime.server.port == 8000
    assert runtime.server.resolved_workers() >= 1
    assert runtime.logging.file == "runtime/logs/app.log"


def test_cio_infrastructure_runtimes_are_loaded_from_owned_config():
    database_runtime = get_database_runtime()
    redis_runtime = get_redis_runtime()

    assert database_runtime.url == settings.database.url
    assert database_runtime.pool_size == settings.database.pool_size
    assert database_runtime.version == settings.version("cio_database")
    assert redis_runtime.host == settings.redis.host
    assert redis_runtime.build_url().startswith("redis://")
