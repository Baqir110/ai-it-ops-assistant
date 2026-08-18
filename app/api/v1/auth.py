from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from app.auth.security import hash_password, verify_password, create_access_token
from app.auth.dependencies import get_current_user, require_role
from app.models.user import UserRole

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Valid full-length 60-character bcrypt dummy hash for pwdlib
DUMMY_HASH = "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6L6595F89I20a656"

# In-memory storage for testing
fake_users_db = {}


class RegisterRequest(BaseModel):
    username: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.VIEWER


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(user_data: RegisterRequest):
    if user_data.username in fake_users_db:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    hashed_pwd = hash_password(user_data.password)

    fake_users_db[user_data.username] = {
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_pwd,
        "role": user_data.role.value,
    }

    return {"message": f"User {user_data.username} created successfully"}


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = fake_users_db.get(form_data.username)

    if user is None:
        verify_password(form_data.password, DUMMY_HASH)
        is_valid = False
    else:
        is_valid = verify_password(form_data.password, user["hashed_password"])

    if not user or not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        data={"sub": user["username"], "role": user["role"]}
    )

    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/users/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return current_user