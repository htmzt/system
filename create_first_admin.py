# create_first_admin.py
"""
Create first admin account

Run this script once to create the initial admin user:
    python create_first_admin.py
"""

from app.database import SessionLocal
from app.models.auth import InternalUser
from app.core.security import hash_password
from app.core.permissions import UserRole
from app.config import settings

def create_first_admin():
    """Create first admin account"""
    print("=" * 60)
    print("CREATE FIRST ADMIN ACCOUNT")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Check if admin already exists
        existing_admin = db.query(InternalUser).filter(
            InternalUser.email == settings.FIRST_ADMIN_EMAIL
        ).first()
        
        if existing_admin:
            print(f"⚠️  Admin account already exists: {settings.FIRST_ADMIN_EMAIL}")
            print(f"   Role: {existing_admin.role}")
            print(f"   Active: {existing_admin.is_active}")
            return False
        
        # Create admin account
        admin = InternalUser(
            email=settings.FIRST_ADMIN_EMAIL,
            password_hash=hash_password(settings.FIRST_ADMIN_PASSWORD),
            full_name=settings.FIRST_ADMIN_NAME,
            role=UserRole.ADMIN,
            can_approve=True,
            can_create_assignments=True,
            can_create_users=True,
            is_active=True,
            email_verified=True
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("\n✅ Admin account created successfully!")
        print(f"\n📧 Email: {admin.email}")
        print(f"🔑 Password: {settings.FIRST_ADMIN_PASSWORD}")
        print(f"👤 Name: {admin.full_name}")
        print(f"🎭 Role: {admin.role}")
        print(f"\n⚠️  IMPORTANT: Change the password after first login!")
        print("\n" + "=" * 60)
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin: {str(e)}")
        db.rollback()
        return False
    finally:
        db.close()


if __name__ == "__main__":
    create_first_admin()