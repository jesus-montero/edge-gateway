"""Endpoints para la gestión de la configuración SaaS.

Este módulo expone operaciones CRUD para ``config/saas.yaml``. El mapa de
proveedores es intencionalmente agnóstico al esquema para que cada proveedor
SaaS pueda conservar su propio conjunto de parámetros, por ejemplo ``sportgo``
y ``ahoraone``.

Endpoints:
    GET /saas - Lista todos los proveedores SaaS
    GET /saas/{provider_name} - Obtiene la configuración de un proveedor
    POST /saas/{provider_name} - Crea una configuración de proveedor
    PUT /saas/{provider_name} - Sustituye una configuración de proveedor
    DELETE /saas/{provider_name} - Elimina una configuración de proveedor

Autor:
    Jesus Montero

Fecha:
    2026
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.repositories import saas_config

router = APIRouter(tags=["saas"])


@router.get("/saas")
def list_providers() -> dict[str, Any]:
    """Lista todos los proveedores SaaS configurados."""

    try:
        providers = saas_config.get_all_providers()
        return {
            "status": "success",
            "count": len(providers),
            "providers": providers,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudieron listar los proveedores SaaS: {exc}") from exc


@router.get("/saas/{provider_name}")
def get_provider(provider_name: str) -> dict[str, Any]:
    """Obtiene la configuración de un proveedor por nombre."""

    try:
        provider = saas_config.get_provider(provider_name)
        if provider is None:
            raise HTTPException(status_code=404, detail=f"No se encontró el proveedor '{provider_name}'")

        return {
            "status": "success",
            "provider_name": provider_name,
            "provider": provider,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo leer el proveedor '{provider_name}': {exc}") from exc


@router.post("/saas/{provider_name}")
def create_provider(provider_name: str, provider_config: dict[str, Any], request: Request) -> dict[str, Any]:
    """Crea una nueva configuración de proveedor SaaS."""

    try:
        if saas_config.provider_exists(provider_name):
            raise HTTPException(status_code=400, detail=f"El proveedor '{provider_name}' ya existe")

        success = saas_config.insert_provider(provider_name, provider_config)
        if not success:
            raise HTTPException(status_code=400, detail=f"No se pudo crear el proveedor '{provider_name}'")

        request.app.state.configs["saas"] = saas_config.load_saas_config()
        return {
            "status": "success",
            "message": f"Proveedor '{provider_name}' creado correctamente",
            "provider_name": provider_name,
            "provider": provider_config,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el proveedor '{provider_name}': {exc}") from exc


@router.put("/saas/{provider_name}")
def update_provider(provider_name: str, provider_config: dict[str, Any], request: Request) -> dict[str, Any]:
    """Sustituye la configuración de un proveedor SaaS existente."""

    try:
        if not saas_config.provider_exists(provider_name):
            raise HTTPException(status_code=404, detail=f"No se encontró el proveedor '{provider_name}'")

        success = saas_config.update_provider(provider_name, provider_config)
        if not success:
            raise HTTPException(status_code=400, detail=f"No se pudo actualizar el proveedor '{provider_name}'")

        request.app.state.configs["saas"] = saas_config.load_saas_config()
        return {
            "status": "success",
            "message": f"Proveedor '{provider_name}' actualizado correctamente",
            "provider_name": provider_name,
            "provider": provider_config,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo actualizar el proveedor '{provider_name}': {exc}") from exc


@router.delete("/saas/{provider_name}")
def delete_provider(provider_name: str, request: Request) -> dict[str, Any]:
    """Elimina una configuración de proveedor SaaS."""

    try:
        if not saas_config.provider_exists(provider_name):
            raise HTTPException(status_code=404, detail=f"No se encontró el proveedor '{provider_name}'")

        success = saas_config.delete_provider(provider_name)
        if not success:
            raise HTTPException(status_code=400, detail=f"No se pudo eliminar el proveedor '{provider_name}'")

        request.app.state.configs["saas"] = saas_config.load_saas_config()
        return {
            "status": "success",
            "message": f"Proveedor '{provider_name}' eliminado correctamente",
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo eliminar el proveedor '{provider_name}': {exc}") from exc