"""Ayudantes de repositorio para gestionar la configuración YAML de SaaS.

Este módulo proporciona utilidades CRUD basadas en archivos sobre ``config/saas.yaml``.
Almacena definiciones de proveedores bajo un mapa ``providers`` de nivel superior y
se mantiene agnóstico del esquema de carga de proveedores para que cada integración
pueda definir sus propios parámetros.

Responsabilidades:
    - Resolver la ruta de ``saas.yaml`` a partir de la estructura del proyecto.
    - Cargar y guardar definiciones de proveedores en almacenamiento YAML.
    - Proporcionar operaciones de inserción, actualización, eliminación, consulta y verificación de existencia.

Formato de almacenamiento:
    - Mapa raíz con una clave ``providers``.
    - ``providers`` contiene un mapa con claves de nombre de proveedor.

Autor:
    Jesus Montero

Fecha:
    2026
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def get_saas_config_path() -> Path:
    """Devuelve la ruta absoluta de ``config/saas.yaml"."""

    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent
    return project_root / "config" / "saas.yaml"


def load_saas_config() -> dict[str, Any]:
    """Carga el archivo de configuración YAML de SaaS."""

    config_path = get_saas_config_path()
    if not config_path.exists():
        return {"providers": {}}

    try:
        with config_path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Error al analizar el archivo saas.yaml: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error al leer el archivo saas.yaml: {exc}") from exc

    if not isinstance(config, dict):
        raise RuntimeError("config/saas.yaml debe contener un mapa YAML en la raíz.")

    providers = config.get("providers", {})
    if providers is None:
        providers = {}
    if not isinstance(providers, dict):
        raise RuntimeError("La clave 'providers' de config/saas.yaml debe ser un mapa.")

    return {"providers": providers}


def _save_saas_config(config: dict[str, Any]) -> bool:
    """Persiste la configuración completa de SaaS en ``saas.yaml``."""

    config_path = get_saas_config_path()

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as file:
            yaml.dump(config, file, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return True
    except Exception as exc:
        print(f"Error al guardar el archivo saas.yaml: {exc}")
        return False


def get_all_providers() -> dict[str, Any]:
    """Devuelve todos los proveedores SaaS configurados."""

    return load_saas_config().get("providers", {})


def get_provider(provider_name: str) -> dict[str, Any] | None:
    """Devuelve una configuración de proveedor por nombre."""

    provider_key = str(provider_name).strip()
    if not provider_key:
        return None

    providers = get_all_providers()
    provider = providers.get(provider_key)
    if isinstance(provider, dict):
        return provider
    return None


def provider_exists(provider_name: str) -> bool:
    """Comprueba si existe un proveedor por nombre."""

    return get_provider(provider_name) is not None


def insert_provider(provider_name: str, provider_config: dict[str, Any]) -> bool:
    """Inserta una nueva configuración de proveedor SaaS.

    La inserción se rechaza si el proveedor ya existe.
    """

    provider_key = str(provider_name).strip()
    if not provider_key:
        print("Error: El nombre del proveedor no puede estar vacío")
        return False

    config = load_saas_config()
    providers = config.get("providers", {})
    if provider_key in providers:
        print(f"Error: El proveedor '{provider_key}' ya existe")
        return False

    providers[provider_key] = provider_config
    config["providers"] = providers
    return _save_saas_config(config)


def update_provider(provider_name: str, provider_config: dict[str, Any]) -> bool:
    """Actualiza una configuración existente de proveedor SaaS."""

    provider_key = str(provider_name).strip()
    if not provider_key:
        print("Error: El nombre del proveedor no puede estar vacío")
        return False

    config = load_saas_config()
    providers = config.get("providers", {})
    if provider_key not in providers:
        print(f"Error: El proveedor '{provider_key}' no existe")
        return False

    providers[provider_key] = provider_config
    config["providers"] = providers
    return _save_saas_config(config)


def delete_provider(provider_name: str) -> bool:
    """Elimina una configuración de proveedor SaaS por nombre."""

    provider_key = str(provider_name).strip()
    if not provider_key:
        print("Error: El nombre del proveedor no puede estar vacío")
        return False

    config = load_saas_config()
    providers = config.get("providers", {})
    if provider_key not in providers:
        print(f"Error: El proveedor '{provider_key}' no existe")
        return False

    del providers[provider_key]
    config["providers"] = providers
    return _save_saas_config(config)
