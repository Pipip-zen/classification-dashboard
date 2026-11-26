"""
Module: server/routes/auth.py
Deskripsi:
    Endpoint otentikasi login, pengecekan profil aktif, dan logout sesi.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from server.auth import authenticate_credentials, create_access_token, get_current_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


class LoginRequest(BaseModel):
    username: str
    password: str


@router.post("/login")
def login(req: LoginRequest):
    user = authenticate_credentials(req.username, req.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Username atau password salah.")

    access_token = create_access_token(user)
    return {
        "success": True,
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


@router.get("/me")
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    return {"user": user}


@router.post("/logout")
def logout(user: Dict[str, Any] = Depends(get_current_user)):
    return {"success": True, "username": user["username"]}
