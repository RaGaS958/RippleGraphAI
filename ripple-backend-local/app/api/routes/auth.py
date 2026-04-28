"""Local JWT auth routes — replaces Firebase Auth."""
from fastapi import APIRouter, HTTPException, Depends
from app.core.auth import hash_password, verify_password, create_access_token, get_current_user
from app.models.schemas import RegisterRequest, LoginRequest, AuthResponse
from app.services.database import Database

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(req: RegisterRequest):
    if Database.get_user_by_email(req.email):
        raise HTTPException(400, "Email already registered")
    user = Database.create_user(req.email, hash_password(req.password), req.name)
    token = create_access_token(user["id"], user["email"], user["name"])
    return AuthResponse(access_token=token, user_id=user["id"],
                        email=user["email"], name=user["name"])


@router.post("/login", response_model=AuthResponse)
def login(req: LoginRequest):
    user = Database.get_user_by_email(req.email)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Invalid email or password")
    token = create_access_token(user["id"], user["email"], user.get("name",""))
    return AuthResponse(access_token=token, user_id=user["id"],
                        email=user["email"], name=user.get("name",""))


@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return {"user_id": current_user["sub"], "email": current_user["email"],
            "name": current_user.get("name","")}
