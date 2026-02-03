"""
Authentication and Authorization Module
JWT-based authentication for Teaching Pack Generator API
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, field_validator
import os
from sqlalchemy.orm import Session

from models.database import get_db
from models.database_models import User, UserRole
from models.database_service import get_user_by_email, create_user

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# HTTP Bearer token
security = HTTPBearer()


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class User(BaseModel):
    email: str
    full_name: str
    role: str


class UserInDB(User):
    hashed_password: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool

class LoginRequest(BaseModel):
    email: str
    password: str

class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str

    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('Invalid email format')
        return v

    @field_validator('password')
    @classmethod
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        return v

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Full name must be at least 2 characters long')
        return v.strip()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError as e:
        if "password cannot be longer than 72 bytes" in str(e):
            # Password is too long, this shouldn't happen with proper truncation
            # For existing long passwords, try verifying with truncated version
            truncated_password = plain_password[:72]
            return pwd_context.verify(truncated_password, hashed_password)
        raise


def get_password_hash(password: str) -> str:
    """Hash a password"""
    try:
        return pwd_context.hash(password)
    except ValueError as e:
        if "password cannot be longer than 72 bytes" in str(e):
            # Truncate password if it's too long
            truncated_password = password[:72]
            return pwd_context.hash(truncated_password)
        raise


def get_user(db: Session, email: str) -> Optional[User]:
    """Get user from database"""
    return get_user_by_email(db, email)


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Authenticate a user"""
    user = get_user(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):#type: ignore
        return None
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)) -> User:
    """Get current user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")#type: ignore
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email)
    except JWTError:
        raise credentials_exception

    user = get_user(db, email=token_data.email)#type: ignore
    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """Get current active user"""
    if not current_user.is_active:#type: ignore
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Optional: Role-based access control
def require_role(required_role: str):
    """Decorator to require specific role"""
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role.value != required_role and current_user.role.value != "admin":#type: ignore
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{required_role}' required"
            )
        return current_user
    return role_checker


# Authentication endpoints
def login_for_access_token(db: Session, login_data: LoginRequest) -> Token:
    """Login endpoint logic"""
    user = authenticate_user(db, login_data.email, login_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")


def register_user(db: Session, email: str, password: str, full_name: str, role: UserRole = UserRole.TEACHER) -> User:
    """Register a new user"""
    # Check if user already exists
    existing_user = get_user_by_email(db, email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Hash password and create user
    hashed_password = get_password_hash(password)
    user = create_user(db, email, hashed_password, full_name, role)
    return user
