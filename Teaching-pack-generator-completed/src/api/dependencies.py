"""
Shared dependencies for API routes
"""
from fastapi import Depends
from typing import Annotated
from sqlalchemy.orm import Session

from api.auth import get_current_active_user
from models.database import get_db
from models.database_models import User

# Dependency shortcuts
CurrentUser = Annotated[User, Depends(get_current_active_user)]
DBSession = Annotated[Session, Depends(get_db)]
