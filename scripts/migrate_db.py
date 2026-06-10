import logging
from pathlib import Path
from alembic import command
from alembic.config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    project_root = Path(__file__).resolve().parents[1]
    alembic_ini = project_root / "backend" / "alembic.ini"

    if not alembic_ini.exists():
        logger.error("Alembic config not found at %s", alembic_ini)
        raise FileNotFoundError(f"Missing alembic.ini: {alembic_ini}")

    logger.info("Running Alembic migrations from %s", alembic_ini)
    config = Config(str(alembic_ini))

    try:
        command.upgrade(config, "head")
        logger.info("Alembic migrations completed successfully")
    except Exception as e:
        logger.error("Alembic migration failed: %s", e)
        raise

if __name__ == "__main__":
    main()
