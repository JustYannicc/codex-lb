from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from app.core.config.settings import Settings
from app.core.prestop import PRESTOP_REQUEST_TIMEOUT_SECONDS
from app.core.server import POST_DRAIN_CLEANUP_TIMEOUT_SECONDS


def _compose(path: str = "docker-compose.yml") -> dict[str, Any]:
    repo_root = Path(__file__).resolve().parents[2]
    return yaml.safe_load((repo_root / path).read_text(encoding="utf-8"))


def test_postgres18_compose_upgrade_helper_is_digest_pinned() -> None:
    services = _compose()["services"]
    postgres = services["postgres"]
    upgrade = services["postgres-upgrade"]

    assert postgres["image"] == "postgres:18-alpine"
    assert postgres["volumes"] == ["codex-lb-postgres-data:/var/lib/postgresql"]

    entrypoint = postgres["entrypoint"]
    assert entrypoint[:2] == ["sh", "-ceu"]
    guard = entrypoint[2]
    assert "/var/lib/postgresql/PG_VERSION" in guard
    assert "/var/lib/postgresql/data/PG_VERSION" in guard
    assert "docker-entrypoint.sh" in guard

    image = upgrade["image"]
    assert image.startswith("pgautoupgrade/pgautoupgrade:18-alpine@sha256:")
    assert len(image.rsplit("@sha256:", 1)[1]) == 64
    assert upgrade["profiles"] == ["postgres-upgrade"]
    assert upgrade["environment"]["PGAUTO_ONESHOT"] == "yes"
    assert upgrade["volumes"] == ["codex-lb-postgres-data:/var/lib/postgresql"]
    assert upgrade["restart"] == "no"


def _drain_budget_seconds() -> float:
    settings = Settings()
    return (
        settings.shutdown_drain_timeout_seconds
        + PRESTOP_REQUEST_TIMEOUT_SECONDS
        + POST_DRAIN_CLEANUP_TIMEOUT_SECONDS
        + 5
    )


def _parse_compose_duration_seconds(raw_value: Any) -> float:
    assert isinstance(raw_value, str)
    if raw_value.endswith("s"):
        raw_value = raw_value[:-1]
    return float(raw_value)


def test_prod_compose_has_stop_grace_above_drain_budget() -> None:
    services = _compose("docker-compose.prod.yml")["services"]
    server = services["server"]

    stop_grace_seconds = _parse_compose_duration_seconds(server["stop_grace_period"])
    assert stop_grace_seconds >= _drain_budget_seconds()
