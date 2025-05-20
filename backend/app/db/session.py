from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging
from fastapi import HTTPException # <--- IMPORT HTTPException
import sys # <--- IMPORT SYS for sys.exit() in case of critical failure

logger = logging.getLogger(__name__)

engine = None
SessionLocal = None

if not settings.DATABASE_URL:
    logger.error("DATABASE_URL is not set. Please check your environment variables and configuration.")
    # For a critical setup failure like this, we might even exit if the DB is essential
    # sys.exit("Critical Error: DATABASE_URL not configured. Application cannot start properly.")
else:
    # Mask password in log
    display_db_url = settings.DATABASE_URL
    if settings.POSTGRES_PASSWORD:
        display_db_url = display_db_url.replace(settings.POSTGRES_PASSWORD, "********")
    logger.info(f"Attempting to connect to database: {display_db_url}")

    try:
        engine = create_async_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
        )
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("Database engine and SessionLocal configured successfully.")
    except Exception as e:
        logger.error(f"Failed to create database engine or SessionLocal: {e}")
        # If DB is critical for app startup, consider exiting or a more robust error handling
        # sys.exit(f"Critical Error: Failed to initialize database connection: {e}")


async def get_db() -> AsyncSession:
    """
    Dependency to get a database session.
    Ensures the session is closed after the request.
    """
    if not SessionLocal:
        logger.error("SessionLocal is not initialized. Database connection might have failed during app startup.")
        # This indicates a severe configuration or runtime issue if SessionLocal is None here.
        # Raising an HTTPException will stop the request and inform the client.
        raise HTTPException(
            status_code=503, # Service Unavailable
            detail="Database connection is not available."
        )

    # Type hint db as AsyncSession for better autocompletion and type checking
    db: AsyncSession = SessionLocal()
    try:
        yield db
    finally:
        await db.close()