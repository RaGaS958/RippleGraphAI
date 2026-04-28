"""
Backend config — fully local, zero cloud.
Edit configs/backend_config.yaml or set env vars to override.
"""
from __future__ import annotations
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str     = "RippleGraph AI Backend"
    ENV: str          = "development"
    DEBUG: bool       = True
    GEMINI_API_KEY: str  = ""
    GOOGLE_API_KEY: str = "" 
    SECRET_KEY: str   = "local-dev-secret-change-in-production-32chars"
    LOG_LEVEL: str    = "INFO"
    HOST: str         = "0.0.0.0"
    PORT: int         = 8080

    # ── Database (SQLite — replaces Firestore + BigQuery) ─────────────────────
    DB_PATH: str      = "data/ripple_backend.db"
    DB_ECHO:  bool    = False

    # ── Auth (local JWT — replaces Firebase Auth) ──────────────────────────────
    JWT_SECRET: str        = "jwt-secret-change-in-production-32chars"
    JWT_ALGORITHM: str     = "HS256"
    JWT_EXPIRE_MINUTES: int = 1440        # 24 hours

    # ── ML prediction server (local — replaces Vertex AI endpoint) ────────────
    ML_SERVER_URL: str  = "http://localhost:8081"
    ML_PREDICT_PATH: str = "/predict"
    ML_TIMEOUT_SEC: int  = 10

    # ── WebSocket (replaces Firebase Realtime DB) ──────────────────────────────
    WS_HEARTBEAT_SEC: int = 30

    # ── Risk thresholds ───────────────────────────────────────────────────────
    HIGH_RISK_THRESHOLD: float   = 0.70
    MEDIUM_RISK_THRESHOLD: float = 0.40

    # ── CORS ──────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost:5173",
        "https://ripple-graph-ai.vercel.app",
        "http://localhost:3000",
        "http://localhost:4173",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
