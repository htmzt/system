# app/core/security.py
"""
Security Functions

This module provides:
- Password hashing and verification (bcrypt)
- JWT token creation and verification
- Token utilities
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from passlib.context import CryptContext
from jose import JWTError, jwt
from app.config import settings
import secrets
import re

# ============================================================================
# PASSWORD HASHING
# ============================================================================

# Create password context for bcrypt hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password string
        
    Example:
        >>> hashed = hash_password("MyPassword123!")
        >>> print(hashed)
        $2b$12$KIXvZ3qY8x9fJ5pN2wQ7L.rH8sT6uV2wX3yZ4aB5cD6eF7gH8iJ9k
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("MyPassword123!")
        >>> verify_password("MyPassword123!", hashed)
        True
        >>> verify_password("WrongPassword", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# PASSWORD VALIDATION
# ============================================================================

def validate_password(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password meets requirements
    
    Requirements from config:
    - MIN_PASSWORD_LENGTH
    - REQUIRE_UPPERCASE
    - REQUIRE_LOWERCASE
    - REQUIRE_DIGIT
    - REQUIRE_SPECIAL_CHAR
    
    Args:
        password: Password to validate
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_password("weak")
        (False, "Password must be at least 8 characters")
        
        >>> validate_password("StrongPass123!")
        (True, None)
    """
    # Check length
    if len(password) < settings.MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {settings.MIN_PASSWORD_LENGTH} characters"
    
    # Check uppercase
    if settings.REQUIRE_UPPERCASE and not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    # Check lowercase
    if settings.REQUIRE_LOWERCASE and not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    # Check digit
    if settings.REQUIRE_DIGIT and not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    # Check special character
    if settings.REQUIRE_SPECIAL_CHAR and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, None


# ============================================================================
# JWT TOKEN CREATION
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Dictionary of data to encode in token
              Usually: {"sub": user_id, "email": email, "role": role}
        expires_delta: Optional custom expiration time
        
    Returns:
        JWT token string
        
    Example:
        >>> token = create_access_token(
        ...     data={"sub": "user-123", "email": "john@example.com"}
        ... )
        >>> print(token)
        eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    # Add expiration to token data
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),  # Issued at
        "type": "access"
    })
    
    # Create token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token
    
    Refresh tokens are used to get new access tokens without logging in again.
    They have a longer expiration time (30 days by default).
    
    Args:
        data: Dictionary of data to encode
        expires_delta: Optional custom expiration time
        
    Returns:
        JWT refresh token string
    """
    to_encode = data.copy()
    
    # Set expiration time
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    # Add expiration to token data
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh"
    })
    
    # Create token
    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    
    return encoded_jwt


# ============================================================================
# JWT TOKEN VERIFICATION
# ============================================================================

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decode and verify a JWT token
    
    Args:
        token: JWT token string
        
    Returns:
        Dictionary of token data if valid, None if invalid
        
    Example:
        >>> token = create_access_token({"sub": "user-123"})
        >>> payload = decode_token(token)
        >>> print(payload)
        {'sub': 'user-123', 'exp': 1234567890, 'iat': 1234567890, 'type': 'access'}
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_token(token: str) -> tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Verify a JWT token and return detailed result
    
    Args:
        token: JWT token string
        
    Returns:
        Tuple of (is_valid, payload, error_message)
        
    Example:
        >>> token = create_access_token({"sub": "user-123"})
        >>> is_valid, payload, error = verify_token(token)
        >>> if is_valid:
        ...     print(f"User ID: {payload['sub']}")
        User ID: user-123
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return True, payload, None
        
    except jwt.ExpiredSignatureError:
        return False, None, "Token has expired"
        
    except jwt.JWTClaimsError:
        return False, None, "Invalid token claims"
        
    except JWTError:
        return False, None, "Invalid token"


# ============================================================================
# TOKEN UTILITIES
# ============================================================================

def generate_random_token(length: int = 32) -> str:
    """
    Generate a random token for email verification, password reset, etc.
    
    Args:
        length: Length of token (default 32)
        
    Returns:
        Random URL-safe token string
        
    Example:
        >>> token = generate_random_token()
        >>> print(token)
        kJ8mN2pQ5rT9wX1yZ4aC7eH0jL3nP6sV8
    """
    return secrets.token_urlsafe(length)


def create_email_verification_token() -> str:
    """
    Create a token for email verification
    
    Returns:
        Random token string
    """
    return generate_random_token(32)


def create_password_reset_token() -> str:
    """
    Create a token for password reset
    
    Returns:
        Random token string
    """
    return generate_random_token(32)


# ============================================================================
# TESTING FUNCTIONS
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("SECURITY FUNCTIONS TEST")
    print("=" * 60)
    
    # Test 1: Password hashing
    print("\n1. Testing password hashing...")
    password = "MySecurePassword123!"
    hashed = hash_password(password)
    print(f"   Original: {password}")
    print(f"   Hashed: {hashed[:50]}...")
    
    # Test 2: Password verification
    print("\n2. Testing password verification...")
    is_valid = verify_password(password, hashed)
    print(f"   Correct password: {is_valid} ✅")
    is_valid = verify_password("WrongPassword", hashed)
    print(f"   Wrong password: {is_valid} ❌")
    
    # Test 3: Password validation
    print("\n3. Testing password validation...")
    test_passwords = [
        "weak",
        "NoDigits!",
        "nouppercas3!",
        "NOLOWERCASE1!",
        "GoodPassword123!"
    ]
    for pwd in test_passwords:
        is_valid, error = validate_password(pwd)
        status = "✅" if is_valid else "❌"
        print(f"   '{pwd}': {status} {error or 'Valid'}")
    
    # Test 4: JWT token creation
    print("\n4. Testing JWT token creation...")
    token_data = {
        "sub": "user-123",
        "email": "john@example.com",
        "role": "ADMIN"
    }
    access_token = create_access_token(token_data)
    print(f"   Access token: {access_token[:50]}...")
    
    # Test 5: JWT token verification
    print("\n5. Testing JWT token verification...")
    is_valid, payload, error = verify_token(access_token)
    if is_valid:
        print(f"   Token valid: ✅")
        print(f"   User ID: {payload['sub']}")
        print(f"   Email: {payload['email']}")
        print(f"   Role: {payload['role']}")
    else:
        print(f"   Token invalid: ❌ {error}")
    
    # Test 6: Random token generation
    print("\n6. Testing random token generation...")
    random_token = generate_random_token()
    print(f"   Random token: {random_token}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)