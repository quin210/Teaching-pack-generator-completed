"""
Authentication routes
Handles user login, registration, and user information retrieval
"""
from fastapi import APIRouter, Depends, Form, HTTPException
from api.auth import (
    Token, LoginRequest, UserResponse, login_for_access_token, 
    register_user, UserRole, RegisterRequest
)
from api.dependencies import CurrentUser, DBSession

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/login", response_model=Token)
async def login(login_data: LoginRequest, db: DBSession):
    """Login endpoint"""
    return login_for_access_token(db, login_data)


@router.post("/register", response_model=UserResponse)
async def register(
    db: DBSession,
    email: str = Form(None),
    password: str = Form(None),
    full_name: str = Form(None),
    register_data: RegisterRequest = None
):
    """Register a new user"""
    # Handle both form data and JSON data
    if register_data:
        # JSON request
        user_email = register_data.email
        user_password = register_data.password
        user_full_name = register_data.full_name
    elif email and password and full_name:
        # Form data - validate manually
        if '@' not in email:
            raise HTTPException(status_code=422, detail="Invalid email format")
        if len(password) < 6:
            raise HTTPException(status_code=422, detail="Password must be at least 6 characters long")
        if len(full_name.strip()) < 2:
            raise HTTPException(status_code=422, detail="Full name must be at least 2 characters long")

        user_email = email
        user_password = password
        user_full_name = full_name.strip()
    else:
        raise HTTPException(status_code=422, detail="Missing required fields")

    # Default role is TEACHER for new registrations
    user = register_user(db, user_email, user_password, user_full_name, UserRole.TEACHER)
    return UserResponse(
        id=user.id,  # type: ignore
        email=user.email,  # type: ignore
        full_name=user.full_name,  # type: ignore
        role=user.role.value,  # type: ignore
        is_active=user.is_active  # type: ignore
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,  # type: ignore
        email=current_user.email,  # type: ignore
        full_name=current_user.full_name,  # type: ignore
        role=current_user.role.value,  # type: ignore
        is_active=current_user.is_active  # type: ignore
    )
