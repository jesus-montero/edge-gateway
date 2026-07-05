"""Endpoints de autenticación para las credenciales del panel."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.repositories import auth_config

router = APIRouter(tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UpdateCredentialsRequest(BaseModel):
    new_username: str = Field(min_length=1)
    new_password: str = Field(min_length=1)


@router.get("/auth/credentials")
def get_credentials() -> dict[str, Any]:
    try:
        return {
            "status": "success",
            "username": auth_config.get_current_username(),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudieron leer las credenciales: {exc}") from exc


@router.post("/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    try:
        if not auth_config.verify_credentials(payload.username, payload.password):
            raise HTTPException(status_code=401, detail="Usuario o contraseña inválidos")

        return {
            "status": "success",
            "username": auth_config.get_current_username(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo autenticar: {exc}") from exc


@router.put("/auth/credentials")
def update_credentials(payload: UpdateCredentialsRequest) -> dict[str, Any]:
    try:
        success = auth_config.update_credentials(payload.new_username, payload.new_password)
        if not success:
            raise HTTPException(status_code=400, detail="No se proporcionó un nuevo usuario o contraseña vacío")

        return {
            "status": "success",
            "username": auth_config.get_current_username(),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudieron actualizar las credenciales: {exc}") from exc
