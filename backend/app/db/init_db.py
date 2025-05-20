import asyncio
import logging
from app.db.session import engine, SessionLocal # engine is imported here for init_db's use
from app.db.base_class import Base
# Import your models here so Base knows about them
# from app.models.user import User # Example, uncomment when User model exists
from app.models.organization import Organization # etc.

# Logger for the init_db function and module-level messages
logger = logging.getLogger(__name__)

async def init_db():
    logger.info("Initializing database...")
    # This 'engine' refers to the one imported at the top of the file
    if not engine:
        logger.error("Database engine (from app.db.session) is not initialized. Cannot create tables.")
        return

    async with engine.begin() as conn:
        try:
            # For development, you might want to drop tables first
            # logger.info("Dropping all tables...")
            # await conn.run_sync(Base.metadata.drop_all)
            # logger.info("Tables dropped.")

            logger.info("Creating all tables...")
            await conn.run_sync(Base.metadata.create_all)
            logger.info("Tables created successfully.")
        except Exception as e:
            logger.error(f"Error during table creation: {e}")
            raise # Re-raise the exception after logging

    # You can add initial data seeding here if needed
    # async with SessionLocal() as db:
    #     # Check if admin user exists
    #     # Create admin user
    #     pass
    logger.info("Database initialization complete.")

if __name__ == "__main__":
    # --- BASIC LOGGING CONFIGURATION ---
    # This configures logging for the entire script when run directly.
    # Messages from 'logger' (app.db.init_db) and 'main_logger' (__main__) will be affected.
    logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s:%(message)s')
    # --- END BASIC LOGGING CONFIGURATION ---

    # Logger for messages specific to this __main__ execution block
    main_logger = logging.getLogger("__main__")

    # Import settings here to ensure they are loaded before dependent modules like session.engine might be re-evaluated
    # or for the checks below.
    from app.core.config import settings # To ensure settings (and DATABASE_URL) are loaded

    # Re-import 'engine' from app.db.session here.
    # This ensures that the 'engine' variable used for the check below
    # is the one from the app.db.session module, after 'settings' has been loaded.
    # Due to Python's module caching, this will be the same 'engine' object as the one
    # imported at the top if app.db.session correctly initializes its engine based on settings.
    from app.db.session import engine as engine_from_session_for_check

    if not settings.DATABASE_URL:
        main_logger.error("DATABASE_URL not set in settings. Exiting.")
    elif not engine_from_session_for_check: # Check the engine instance from app.db.session
        main_logger.error("Database engine in app.db.session is None. Exiting.")
    else:
        # Use the redaction logic from the feedback
        # It's assumed settings.DATABASE_URL is a string or string-like.
        # If settings.POSTGRES_PASSWORD is None or empty, or DATABASE_URL is None/empty, it shows DATABASE_URL as is.
        db_url_display = str(settings.DATABASE_URL) # Default to showing the URL
        if settings.POSTGRES_PASSWORD and settings.DATABASE_URL:
            # Ensure DATABASE_URL is a string for .replace()
            db_url_display = str(settings.DATABASE_URL).replace(str(settings.POSTGRES_PASSWORD), '********')

        main_logger.info(f"Attempting DB initialization for: {db_url_display}")
        try:
            asyncio.run(init_db())
        except Exception as e:
            main_logger.error(f"An error occurred during asyncio.run(init_db()): {e}")
            import traceback
            main_logger.error(traceback.format_exc())