"""
Authentification JWT pour les professionnels.

Flux :
  POST /auth/register → crée le compte + retourne le token
  POST /auth/login    → vérifie email/password → retourne le token
  GET  /auth/me       → retourne le profil du pro connecté

Le token JWT contient : {"sub": pro_id, "email": email, "exp": ...}
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.base import get_db
from api.models.professionnel import Professionnel
from config.settings import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())

# OAuth2 scheme — le frontend envoie le token dans le header Authorization: Bearer <token>
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


# ─── Schemas ────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: str
    password: str
    raison_sociale: str
    siret: str | None = None
    siren: str | None = None
    telephone: str | None = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    pro_id: str
    expires_in: int


# ─── JWT helpers ────────────────────────────────────────────────────────────

def _create_access_token(pro_id: UUID, email: str) -> tuple[str, int]:
    """Crée un JWT signé. Retourne (token, expires_in_seconds)."""
    settings = get_settings()
    if not settings.app_secret_key:
        raise RuntimeError("APP_SECRET_KEY non configure — impossible de signer le JWT")

    expire_minutes = settings.jwt_access_token_expire_minutes
    expire = datetime.utcnow() + timedelta(minutes=expire_minutes)
    payload = {
        "sub": str(pro_id),
        "email": email,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.app_secret_key, algorithm=settings.jwt_algorithm)
    return token, expire_minutes * 60


def _verify_token(token: str) -> dict:
    """Vérifie et décode un JWT. Lève une exception si invalide."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expire",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# ─── Dépendance : pro courant ──────────────────────────────────────────────

async def get_current_pro(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Professionnel:
    """
    Dépendance FastAPI : extrait le professionnel depuis le JWT.
    Utilisable dans n'importe quel endpoint via Depends(get_current_pro).
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentification requise",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _verify_token(token)
    pro_id = payload.get("sub")
    if not pro_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide")

    pro = await db.get(Professionnel, pro_id)
    if not pro:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Compte introuvable")
    if not pro.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte desactive")

    return pro


async def get_optional_pro(
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> Professionnel | None:
    """
    Comme get_current_pro mais retourne None si pas de token.
    Utile pour les endpoints qui fonctionnent avec ou sans auth (transition).
    """
    if not token:
        return None
    try:
        return await get_current_pro(token=token, db=db)
    except HTTPException:
        return None


async def get_current_pro_transition(
    token: str | None = Depends(oauth2_scheme),
    pro_id: UUID | None = None,
    db: AsyncSession = Depends(get_db),
) -> Professionnel:
    """
    Dépendance de transition : accepte JWT OU pro_id en query param.
    Priorité au JWT. Le pro_id sera supprimé quand le frontend enverra le JWT.
    """
    # 1. JWT si présent
    if token:
        try:
            return await get_current_pro(token=token, db=db)
        except HTTPException:
            pass

    # 2. Fallback pro_id query param (transition)
    if pro_id:
        pro = await db.get(Professionnel, pro_id)
        if not pro:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Professionnel non trouve")
        if not pro.is_active:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Compte desactive")
        return pro

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentification requise (JWT ou pro_id)",
    )


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Crée un compte pro et retourne un token JWT."""
    # Vérifier unicité email
    result = await db.execute(select(Professionnel).where(Professionnel.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(409, "Un compte existe deja avec cet email")

    # Vérifier unicité SIRET (si fourni)
    if req.siret:
        result = await db.execute(select(Professionnel).where(Professionnel.siret == req.siret))
        if result.scalar_one_or_none():
            raise HTTPException(409, "Un compte existe deja avec ce SIRET")

    pro = Professionnel(
        raison_sociale=req.raison_sociale,
        siret=req.siret or None,
        siren=req.siren or (req.siret[:9] if req.siret else None),
        email=req.email,
        telephone=req.telephone,
        password_hash=hash_password(req.password),
    )
    db.add(pro)
    await db.flush()

    token, expires_in = _create_access_token(pro.id, pro.email)
    logger.info(f"[Auth] Nouveau compte pro={pro.id} email={req.email}")

    return TokenResponse(access_token=token, pro_id=str(pro.id), expires_in=expires_in)


@router.post("/login", response_model=TokenResponse)
async def login(form: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Login avec email + password. Retourne un token JWT."""
    result = await db.execute(select(Professionnel).where(Professionnel.email == form.username))
    pro = result.scalar_one_or_none()

    if not pro or not hasattr(pro, "password_hash") or not pro.password_hash:
        raise HTTPException(401, "Email ou mot de passe incorrect")

    if not verify_password(form.password, pro.password_hash):
        raise HTTPException(401, "Email ou mot de passe incorrect")

    if not pro.is_active:
        raise HTTPException(403, "Compte desactive")

    token, expires_in = _create_access_token(pro.id, pro.email)
    logger.info(f"[Auth] Login pro={pro.id}")

    return TokenResponse(access_token=token, pro_id=str(pro.id), expires_in=expires_in)


@router.get("/me")
async def me(pro: Professionnel = Depends(get_current_pro)):
    """Retourne le profil du pro connecté."""
    return {
        "id": str(pro.id),
        "email": pro.email,
        "raison_sociale": pro.raison_sociale,
        "siret": pro.siret,
        "nom_commerce": pro.nom_commerce,
        "type_compte": pro.type_compte,
        "setup_complete": pro.setup_complete,
        "is_active": pro.is_active,
    }
