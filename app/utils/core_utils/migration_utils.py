"""Alembic migration runner for automatic database schema management on startup."""

from pathlib import Path

from alembic import command
from alembic.config import Config

from app.config.log_config import logger


def run_database_migrations() -> bool:
    """Run Alembic migrations programmatically up to 'head'.

    Returns:
        True if migrations executed successfully or were up to date, False otherwise.
    """
    try:
        project_root = Path(__file__).resolve().parents[3]
        alembic_ini_path = project_root / "alembic.ini"

        if not alembic_ini_path.exists():
            logger.warning(
                "Alembic config not found at %s. Skipping auto-migration.",
                alembic_ini_path,
            )
            return False

        alembic_cfg = Config(str(alembic_ini_path))
        alembic_cfg.set_main_option("script_location", str(project_root / "migrations"))

        logger.info("Executing automated Alembic migrations to head...")
        command.upgrade(alembic_cfg, "head")
        logger.info("Database migrations completed successfully.")
        return True
    except Exception as exc:
        logger.warning(
            "Automated Alembic migration encountered an error (%s); falling back to direct schema init.",
            exc,
        )
        return False
