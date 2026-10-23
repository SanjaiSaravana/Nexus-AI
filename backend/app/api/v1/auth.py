from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User, Profile
from app.schemas.user import UserCreate, UserLogin, UserResponse, Token

router = APIRouter()

@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user with this email exists
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists."
        )

    # Check username if provided
    if user_in.username:
        stmt_user = select(User).where(User.username == user_in.username)
        res_user = await db.execute(stmt_user)
        if res_user.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this username already exists."
            )

    # Create user
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        is_active=True
    )
    db.add(user)
    await db.flush()

    # Create associated profile
    profile = Profile(
        user_id=user.id,
        full_name=user_in.username or user_in.email.split("@")[0],
        bio="",
        preferences={"theme": "dark", "notifications_enabled": True}
    )
    db.add(profile)
    await db.commit()

    # Reload with profile
    stmt = select(User).options(selectinload(User.profile)).where(User.id == user.id)
    user_loaded = (await db.execute(stmt)).scalar_one()

    access_token = create_access_token(subject=str(user.id))
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user_loaded)
    )

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(User).options(selectinload(User.profile)).where(User.email == credentials.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")

    access_token = create_access_token(subject=str(user.id))
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )
