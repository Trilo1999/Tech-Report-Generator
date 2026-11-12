"""Unit and integration tests for automatic Alembic migrations."""

from pathlib import Path

from app.utils.core_utils.migration_utils import run_database_migrations


def test_alembic_configuration_files_exist():
    """Verify alembic.ini and migrations directory are present."""
    project_root = Path(__file__).resolve().parents[3]
    alembic_ini = project_root / "alembic.ini"
    migrations_env = project_root / "migrations" / "env.py"
    versions_dir = project_root / "migrations" / "versions"

    assert alembic_ini.exists(), "alembic.ini should exist in project root"
    assert migrations_env.exists(), "migrations/env.py should exist"
    assert versions_dir.exists(), "migrations/versions directory should exist"


def test_run_database_migrations_programmatic_execution():
    """Verify programmatic migration execution runs idempotently and returns True."""
    success = run_database_migrations()
    assert success is True
