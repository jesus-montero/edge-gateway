"""Ayudas de repositorio para gestionar las credenciales de autenticación del panel.

Las credenciales se almacenan en ``config/auth.yaml`` como un nombre de usuario
y un hash de contraseña PBKDF2 con salt. El repositorio puede crear un conjunto
de credenciales predeterminado en el primer arranque para que el panel tenga un
inicio de sesión inicial conocido.
"""

from __future__ import annotations

import hashlib
import secrets
from pathlib import Path
from typing import Any

import yaml

DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"
DEFAULT_ITERATIONS = 390000
SALT_BYTES = 16


def get_auth_config_path() -> Path:
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent
    return project_root / "config" / "auth.yaml"


def _hash_password(password: str, salt: bytes, iterations: int) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations).hex()


def _bootstrap_auth_payload() -> dict[str, Any]:
    salt = secrets.token_bytes(SALT_BYTES)
    return {
        "username": DEFAULT_USERNAME,
        "password_salt": salt.hex(),
        "password_hash": _hash_password(DEFAULT_PASSWORD, salt, DEFAULT_ITERATIONS),
        "iterations": DEFAULT_ITERATIONS,
    }


def create_initial_auth_yaml() -> bool:
    config_path = get_auth_config_path()

    if config_path.exists():
        return False

    config_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with config_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(_bootstrap_auth_payload(), file, sort_keys=False, allow_unicode=True)
        return True
    except Exception as exc:
        print(f"Error al crear el archivo auth.yaml: {exc}")
        return False


def load_auth_config() -> dict[str, Any]:
    config_path = get_auth_config_path()

    if not config_path.exists():
        create_initial_auth_yaml()

    try:
        with config_path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Sintaxis de la configuración de autenticación no válida: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"No se pudo leer la configuración de autenticación: {exc}") from exc

    if not isinstance(config, dict):
        raise RuntimeError("config/auth.yaml debe contener un mapa YAML.")

    for key in ("username", "password_salt", "password_hash", "iterations"):
        if key not in config:
            raise RuntimeError(f"Falta la clave obligatoria '{key}' en config/auth.yaml.")

    if not str(config.get("username", "")).strip() or not str(config.get("password_salt", "")).strip() or not str(config.get("password_hash", "")).strip():
        bootstrap_payload = _bootstrap_auth_payload()
        save_auth_config(bootstrap_payload)
        return bootstrap_payload

    return config


def save_auth_config(config: dict[str, Any]) -> bool:
    config_path = get_auth_config_path()
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(config, file, sort_keys=False, allow_unicode=True)
        return True
    except Exception as exc:
        print(f"Error al guardar el archivo auth.yaml: {exc}")
        return False


def verify_credentials(username: str, password: str) -> bool:
    config = load_auth_config()
    stored_username = str(config.get("username", "")).strip()
    if username.strip() != stored_username:
        return False

    salt_hex = str(config.get("password_salt", ""))
    hash_hex = str(config.get("password_hash", ""))
    iterations = int(config.get("iterations", DEFAULT_ITERATIONS))
    if not salt_hex or not hash_hex:
        return False

    salt = bytes.fromhex(salt_hex)
    candidate_hash = _hash_password(password, salt, iterations)
    return secrets.compare_digest(candidate_hash, hash_hex)


def get_current_username() -> str:
    config = load_auth_config()
    return str(config.get("username", "")).strip()


def update_credentials(new_username: str, new_password: str) -> bool:
    """Actualiza las credenciales almacenadas sin requerir la contraseña actual.

    Nota: esto omite deliberadamente la verificación de la contraseña actual para
    ajustarse al requisito de UX del frontend de no pedir la contraseña anterior.
    """
    normalized_username = new_username.strip()
    if not normalized_username or not new_password:
        return False

    salt = secrets.token_bytes(SALT_BYTES)
    iterations = DEFAULT_ITERATIONS
    payload = {
        "username": normalized_username,
        "password_salt": salt.hex(),
        "password_hash": _hash_password(new_password, salt, iterations),
        "iterations": iterations,
    }
    return save_auth_config(payload)
