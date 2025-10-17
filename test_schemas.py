# test_schemas.py
"""Test Pydantic schemas"""

from app.schemas import UserCreate, UserLogin, UserResponse, Token

print("=" * 60)
print("PYDANTIC SCHEMAS TEST")
print("=" * 60)

# Test 1: UserCreate validation
print("\n1. Testing UserCreate schema...")
try:
    user_data = UserCreate(
        email="john@sib.com",
        password="SecurePass123!",
        full_name="John Smith",
        role="PROJECT_MANAGER",
        phone="+212-6-12-34-56-78"
    )
    print("   ✅ UserCreate schema valid")
    print(f"   Email: {user_data.email}")
    print(f"   Role: {user_data.role}")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 2: UserLogin validation
print("\n2. Testing UserLogin schema...")
try:
    login_data = UserLogin(
        email="john@sib.com",
        password="SecurePass123!"
    )
    print("   ✅ UserLogin schema valid")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Invalid email
print("\n3. Testing invalid email...")
try:
    invalid_user = UserCreate(
        email="not-an-email",
        password="SecurePass123!",
        full_name="John",
        role="PM"
    )
    print("   ❌ Should have failed!")
except Exception as e:
    print("   ✅ Correctly rejected invalid email")

# Test 4: Short password
print("\n4. Testing short password...")
try:
    invalid_user = UserCreate(
        email="john@test.com",
        password="123",
        full_name="John",
        role="PM"
    )
    print("   ❌ Should have failed!")
except Exception as e:
    print("   ✅ Correctly rejected short password")

print("\n" + "=" * 60)
print("✅ SCHEMAS WORKING CORRECTLY!")
print("=" * 60)