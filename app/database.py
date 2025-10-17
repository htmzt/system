# app/database.py
"""
Database Connection & Session Management

This module handles:
- Database engine creation
- Session management
- Base class for all models
- Database dependency for FastAPI routes
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from typing import Generator
from app.config import settings

# ============================================================================
# CREATE DATABASE ENGINE
# ============================================================================

# Create the database engine
# This is the connection to PostgreSQL database
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # Test connections before using them
    pool_size=10,            # Keep 10 connections in the pool
    max_overflow=20,         # Allow 20 additional connections if pool is full
    echo=settings.DEBUG,     # Log all SQL queries if DEBUG=True
    future=True              # Use SQLAlchemy 2.0 style
)

# ============================================================================
# CREATE SESSION FACTORY
# ============================================================================

# SessionLocal is a factory for creating database sessions
# Each session represents a "conversation" with the database
SessionLocal = sessionmaker(
    autocommit=False,  # Don't auto-commit changes (we control when to commit)
    autoflush=False,   # Don't auto-flush changes (we control when to flush)
    bind=engine        # Bind to our database engine
)

# ============================================================================
# BASE CLASS FOR MODELS
# ============================================================================

# All database models will inherit from this Base class
# Example: class User(Base):
Base = declarative_base()

# ============================================================================
# DATABASE DEPENDENCY FOR FASTAPI
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency for FastAPI routes
    
    This function:
    1. Creates a new database session
    2. Yields it to the route
    3. Closes it when the route is done
    
    Usage in routes:
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    
    The session is automatically closed after the request,
    even if an exception occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# CREATE ALL TABLES
# ============================================================================

def create_tables():
    """
    Create all database tables
    
    This creates tables for all models that inherit from Base.
    Usually called on application startup.
    
    Usage:
        from app.database import create_tables
        create_tables()
    
    Note: In production, use Alembic migrations instead!
    """
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created successfully")

# ============================================================================
# DROP ALL TABLES (DANGER!)
# ============================================================================

def drop_tables():
    """
    Drop all database tables
    
    ⚠️ WARNING: This deletes ALL data!
    Only use in development/testing!
    
    Usage:
        from app.database import drop_tables
        drop_tables()
    """
    Base.metadata.drop_all(bind=engine)
    print("⚠️  All database tables dropped")

# ============================================================================
# TEST DATABASE CONNECTION
# ============================================================================

def test_connection():
    """
    Test database connection
    
    Usage:
        python -c "from app.database import test_connection; test_connection()"
    """
    try:
        # Try to connect
        with engine.connect() as connection:
            print("✅ Database connection successful!")
            print(f"   Connected to: {settings.DATABASE_URL.split('@')[1]}")
            return True
    except Exception as e:
        print("❌ Database connection failed!")
        print(f"   Error: {str(e)}")
        return False


# ============================================================================
# RUN TESTS IF EXECUTED DIRECTLY
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("DATABASE CONNECTION TEST")
    print("=" * 60)
    test_connection()
    print("=" * 60)