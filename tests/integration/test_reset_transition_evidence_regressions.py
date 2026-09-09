from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from app.core.crypto import TokenEncryptor
from app.core.usage.refresh_scheduler import _resolve_long_window_reset_evidence
from app.core.utils.time import naive_utc_to_epoch
from app.db.models import Account, AccountStatus
from app.db.session import SessionLocal
from app.modules.accounts.repository import AccountsRepository
from app.modules.usage.repository import UsageRepository

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_transition", [None, "first", "last"])
async def test_scheduler_selects_latest_valid_persisted_reset(db_setup, invalid_transition: str | None) -> None:
    """SQLite rounding must neither invent a reset nor hide a later valid one."""
    del db_setup
    start = datetime(2026, 9, 9, 12)
    epoch = naive_utc_to_epoch(start)
    week = 10_080 * 60
    encryptor = TokenEncryptor()
    account = Account(
        id="reset-evidence-regression",
        email="reset-evidence@example.com",
        plan_type="plus",
        access_token_encrypted=encryptor.encrypt("access"),
        refresh_token_encrypted=encryptor.encrypt("refresh"),
        id_token_encrypted=encryptor.encrypt("id"),
        last_refresh=start,
        status=AccountStatus.RATE_LIMITED,
        reset_at=epoch + 1_000,
        blocked_at=epoch,
    )
    async with SessionLocal() as session:
        if invalid_transition is not None and session.get_bind().dialect.name != "sqlite":
            pytest.skip("Regression covers SQLite rounding fractional timestamps")
        await AccountsRepository(session).upsert(account)
        repo = UsageRepository(session)
        baseline = await repo.add_entry(
            account.id,
            100.0,
            window="secondary",
            recorded_at=start + timedelta(seconds=50),
            reset_at=account.reset_at,
            window_minutes=10_080,
        )
        first = await repo.add_entry(
            account.id,
            0.0,
            window="secondary",
            recorded_at=start + timedelta(seconds=100, microseconds=-1 if invalid_transition == "first" else 0),
            reset_at=epoch + week + 100,
            window_minutes=10_080,
        )
        before_last = await repo.add_entry(
            account.id,
            90.0,
            window="secondary",
            recorded_at=start + timedelta(seconds=150),
            reset_at=first.reset_at,
            window_minutes=10_080,
        )
        last = await repo.add_entry(
            account.id,
            0.0,
            window="secondary",
            recorded_at=start + timedelta(seconds=200, microseconds=-1 if invalid_transition == "last" else 0),
            reset_at=epoch + week + 200,
            window_minutes=10_080,
        )
        # An unchanged refresh forces the scheduler to recover persisted evidence.
        evidence = await _resolve_long_window_reset_evidence(
            accounts=[account],
            usage_repo=repo,
            before_primary={},
            before_secondary={account.id: last},
            after_primary={},
            after_secondary={account.id: last},
            before_monthly={},
            after_monthly={},
        )

    assert account.id in evidence
    recovered = evidence[account.id]
    assert recovered.baseline.id == baseline.id
    expected_before = baseline if invalid_transition == "last" else before_last
    expected_after = first if invalid_transition == "last" else last
    assert (recovered.before.id, recovered.after.id) == (expected_before.id, expected_after.id)
