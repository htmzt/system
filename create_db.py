# create_tables.py
"""
Create all database tables

Run this script to create tables in your database:
    python create_tables.py
"""

from app.database import Base, engine, test_connection
from app.models import (
    InternalUser,
    UserSession,
    LoginHistory,
    PermissionChangeLog
)

def create_all_tables():
    """Create all database tables"""
    print("=" * 60)
    print("DATABASE SETUP")
    print("=" * 60)
    
    # Test connection first
    print("\n1. Testing database connection...")
    if not test_connection():
        print("❌ Cannot connect to database. Exiting.")
        return False
    
    # Create tables
    print("\n2. Creating database tables...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ All tables created successfully!")
        
        # Show created tables
        print("\n3. Created tables:")
        for table in Base.metadata.sorted_tables:
            print(f"   - {table.name}")
        
        print("\n" + "=" * 60)
        print("✅ DATABASE SETUP COMPLETE!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False


if __name__ == "__main__":
    create_all_tables()