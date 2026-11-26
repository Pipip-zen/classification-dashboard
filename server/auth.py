"""
Module: server/auth.py
Deskripsi:
    Sistem otentikasi dan otorisasi berbasis peran (RBAC) tanpa dependensi eksternal:
    - 3 Akun Fix: Admin Drone ('drone'), Admin ROV ('rov'), Spectator ('spectator')
    - Token stateless bertanda tangan HMAC-SHA256 dengan masa berlaku terukur
    - Guard FastAPI untuk membatasi akses REST API dan WebSocket sesuai peran
"""

import os
import hmac
import time
import json
import base64
import hashlib
import secrets
from typing import Dict, Any, Optional
from fastapi import Depends, Header, Query, HTTPException


VALID_ROLES = ("drone", "rov", "spectator")
TOKEN_TTL_SECONDS = 12 * 3600


def _get_auth_secret() -> bytes:
    return os.getenv("AUTH_SECRET", "vanguard-tactical-gcs-dev-secret-change-me").encode("utf-8")


def get_configured_accounts() -> Dict[str, Dict[str, str]]:
    """Membaca konfigurasi 3 akun role dari environment variables."""
    return {
        os.getenv("DRONE_USERNAME", "drone").strip(): {
            "role": "drone",
            "password": os.getenv("DRONE_PASSWORD", "drone123"),
            "display_name": "Admin Drone",
        },
        os.getenv("ROV_USERNAME", "rov").strip(): {
            "role": "rov",
            "password": os.getenv("ROV_PASSWORD", "rov123"),
            "display_name": "Admin ROV",
        },
        os.getenv("SPECTATOR_USERNAME", "spectator").strip(): {
            "role": "spectator",
            "password": os.getenv("SPECTATOR_PASSWORD", "spectator123"),
            "display_name": "Spectator",
        },
    }


def authenticate_credentials(username: str, password: str) -> Optional[Dict[str, str]]:
    """Memvalidasi username & password menggunakan perbandingan constant-time."""
    accounts = get_configured_accounts()
    clean_user = username.strip()
    acc = accounts.get(clean_user)
    if acc is None:
        return None
    if not secrets.compare_digest(password.encode("utf-8"), acc["password"].encode("utf-8")):
        return None
    return {
        "username": clean_user,
        "role": acc["role"],
        "display_name": acc["display_name"],
    }


def create_access_token(user: Dict[str, Any], ttl_seconds: int = TOKEN_TTL_SECONDS) -> str:
    """Membuat token sesi HMAC-SHA256 compact berisi peran dan waktu kedaluwarsa."""
    exp = int(time.time()) + ttl_seconds
    payload = {
        "sub": user["username"],
        "role": user["role"],
        "name": user["display_name"],
        "exp": exp,
    }
    raw_json = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_b64 = base64.urlsafe_b64encode(raw_json).decode("ascii").rstrip("=")
    sig = hmac.new(_get_auth_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{payload_b64}.{sig}"


def verify_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    """Memverifikasi tanda tangan HMAC dan masa berlaku token."""
    if not token or "." not in token:
        return None
    try:
        payload_b64, sig = token.split(".", 1)
        expected_sig = hmac.new(_get_auth_secret(), payload_b64.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected_sig):
            return None
        padded = payload_b64 + ("=" * (-len(payload_b64) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        if int(payload.get("exp", 0)) <= int(time.time()):
            return None
        if payload.get("role") not in VALID_ROLES:
            return None
        return {
            "username": payload["sub"],
            "role": payload["role"],
            "display_name": payload.get("name", payload["role"]),
            "exp": payload["exp"],
        }
    except Exception:
        return None


def extract_bearer_or_query(
    authorization: Optional[str] = None,
    token: Optional[str] = None,
) -> Optional[str]:
    if authorization:
        parts = authorization.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1].strip()
    if token:
        return token.strip()
    return None


def get_current_user(
    authorization: Optional[str] = Header(default=None),
    token: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    raw_token = extract_bearer_or_query(authorization, token)
    user = verify_token(raw_token)
    if user is None:
        raise HTTPException(status_code=401, detail="Sesi tidak valid atau belum login.")
    return user


def require_operator_role(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    if user["role"] not in ("drone", "rov"):
        raise HTTPException(
            status_code=403,
            detail="Akses ditolak: fitur ini hanya untuk Admin Drone atau Admin ROV.",
        )
    return user


def ensure_channel_operator(channel_id: str, user: Dict[str, Any]) -> None:
    cid = channel_id.lower()
    if user["role"] != cid:
        raise HTTPException(
            status_code=403,
            detail=f"Akses ditolak: akun '{user['role']}' tidak berhak mengendalikan channel '{cid}'.",
        )


def can_view_channel(channel_id: str, user: Dict[str, Any]) -> bool:
    return user["role"] in ("spectator", channel_id.lower())
