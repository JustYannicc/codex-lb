"""One-off diagnostic runner. Never changes the PR source tree."""

from __future__ import annotations

import os
import platform
import subprocess
import sys
from pathlib import Path

SOURCE_COMMIT = "c9aeb6b9dd5de1b609274cd8544b1efea59272cd"
SOURCE_TREE = "7f7b8620fc82373af67bd7ae67e1d8dbf116e5f1"
source_dir = Path.cwd()
expected_url = f"sqlite+aiosqlite:///{os.environ['RUNNER_TEMP']}/pr1954-core3/tests.db"

assert platform.system() == "Linux"
assert platform.machine() == "x86_64"
assert sys.version_info[:3] == (3, 13, 15)
assert os.environ["CODEX_LB_DATABASE_URL"] == expected_url
assert os.environ["CODEX_LB_TEST_DATABASE_URL"] == expected_url
for revision, expected in (("HEAD", SOURCE_COMMIT), ("HEAD^{tree}", SOURCE_TREE)):
    actual = subprocess.check_output(["git", "rev-parse", revision], text=True).strip()
    assert actual == expected, (revision, actual)
subprocess.run(["git", "diff", "--exit-code"], check=True)
print(f"Verified source commit {SOURCE_COMMIT}, tree {SOURCE_TREE}", flush=True)
print(f"Verified native {platform.system()} {platform.machine()}, Python {platform.python_version()}", flush=True)

sys.path.insert(0, str(source_dir))
from app.db import session  # noqa: E402
from tests import conftest  # noqa: E402

session.init_background_db()
for name, engine in (
    ("foreground", session.engine),
    ("background", session._background_engine),
    ("conftest", conftest.engine),
):
    assert engine is not None
    assert str(engine.url) == expected_url
    print(f"Verified {name} dedicated temporary database", flush=True)

sharder = [sys.executable, ".github/scripts/pytest_shards.py", "--shard-count", "3"]
subprocess.run([*sharder, "--verify"], check=True)
selected = subprocess.check_output([*sharder, "--shard", "3"], text=True).splitlines()
assert selected
import pytest  # noqa: E402

raise SystemExit(
    pytest.main(
        [
            "-vv",
            "-x",
            "-ra",
            "--tb=long",
            "-o",
            "faulthandler_timeout=300",
            "-o",
            "faulthandler_exit_on_timeout=true",
            "--timeout=180",
            "--timeout-method=thread",
            "--durations=20",
            *selected,
        ]
    )
)
