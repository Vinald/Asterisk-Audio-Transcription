#!/usr/bin/env python3
"""
Apply Alembic migrations to initialize or upgrade the database.
Run from the project root: python scripts/migrate_db.py
"""

import os
import sys
from alembic.config import Config
from alembic.command import upgrade
from dotenv import load_dotenv


def migrate_db():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(project_dir, ".env"))
    alembic_ini = os.path.join(project_dir, "alembic.ini")

    if not os.path.exists(alembic_ini):
        print(f"✗ alembic.ini not found at {alembic_ini}")
        return False

    try:
        config = Config(alembic_ini)
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            print("✗ DATABASE_URL not set in environment or .env file")
            return False
        config.set_main_option("sqlalchemy.url", database_url)

        print(f"[*] Running Alembic migrations...")
        print(f"    Database: {database_url.split('/')[-1]}")
        upgrade(config, "head")
        print("✓ Database migrations completed successfully")
        return True

    except Exception as e:
        print(f"✗ Migration error: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = migrate_db()
    sys.exit(0 if success else 1)
