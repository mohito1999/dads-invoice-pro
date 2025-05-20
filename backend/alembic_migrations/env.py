import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine # Ensure this is imported

from alembic import context

# --- ADD THESE IMPORTS ---
import sys
from pathlib import Path
# Add the project root to sys.path to allow imports from 'app'
# Assuming env.py is in backend/alembic_migrations, project root is two levels up
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path: # Avoid adding duplicate paths
    sys.path.append(str(PROJECT_ROOT))

from app.db.base_class import Base  # Your SQLAlchemy declarative base
from app.core.config import settings # Your application settings
# Import all your models here so Alembic detects them for autogenerate
# Ensure these modules actually import the model classes so they are registered with Base.metadata
from app.models import organization # Or more specifically: from app.models.organization import Organization
from app.models import user
from app.models import customer
from app.models import item
# Add other model imports as you create them, e.g.:
# from app.models.user import User # Example: from app.models.user import User
# from app.models.item import Item
# (ensure __init__.py files in app/models allow these imports or import specific classes)
# --- END ADDED IMPORTS ---

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in application settings and is required for offline mode.")
    
    url = str(settings.DATABASE_URL) # Use our settings for offline mode too
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Shared function to configure and run migrations.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # compare_type=True, # Optional: enable type comparison if you have complex types
        # include_schemas=True, # Optional: if you use schemas other than the default (e.g., 'public')
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Ensure DATABASE_URL is available from app settings
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is not set in the application settings (app.core.config.settings).")

    # Create an AsyncEngine using the DATABASE_URL from our settings
    connectable = create_async_engine(
        str(settings.DATABASE_URL), # Ensure it's a string
        poolclass=pool.NullPool,    # Recommended for Alembic operations
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

# Main Alembic entry point
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())