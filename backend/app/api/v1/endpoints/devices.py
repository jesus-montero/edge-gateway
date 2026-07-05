"""Endpoints para la gestión de la configuración de dispositivos.

Este módulo proporciona endpoints REST para gestionar configuraciones de
dispositivos interactuando con la capa de repositorio devices_config. Permite
al frontend consultar, crear, actualizar y eliminar definiciones de dispositivos.

Endpoints:
    GET /devices - Lista todos los dispositivos
    GET /devices/{device_id} - Obtiene un dispositivo concreto
    GET /devices/{device_id}/status - Obtiene el estado en tiempo de ejecución de un dispositivo
    POST /devices - Crea un nuevo dispositivo
    PUT /devices/{device_id} - Actualiza un dispositivo existente
    DELETE /devices/{device_id} - Elimina un dispositivo

Autor:
    Jesus Montero

Fecha:
    2026
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.repositories import devices_config

router = APIRouter(tags=["devices"])


@router.get("/devices")
def list_devices() -> dict[str, Any]:
    """Recupera todos los dispositivos configurados.
    
    Returns:
        Diccionario que contiene la lista de todos los dispositivos.
        
    Raises:
        HTTPException: Si falla la recuperación.
    """
    try:
        devices = devices_config.get_all_devices()
        return {
            "status": "success",
            "count": len(devices),
            "devices": devices
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudieron recuperar los dispositivos: {str(exc)}") from exc


@router.get("/devices/{device_id}")
def get_device(device_id: int) -> dict[str, Any]:
    """Recupera un dispositivo concreto por ID.
    
    Args:
        device_id: Identificador del dispositivo.
        
    Returns:
        Diccionario que contiene la información del dispositivo.
        
    Raises:
        HTTPException: Si no se encuentra el dispositivo o falla la recuperación.
    """
    try:
        device = devices_config.get_device(device_id)
        if device is None:
            raise HTTPException(status_code=404, detail=f"No se encontró el dispositivo {device_id}")
        return {
            "status": "success",
            "device": device
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo recuperar el dispositivo: {str(exc)}") from exc

@router.get("/devices/{device_id}/status")
def get_device_status(device_id: int, request: Request) -> dict[str, Any]:
    """Obtiene el estado en tiempo de ejecución de un dispositivo configurado.

    Args:
        device_id: Identificador del dispositivo configurado.
        request: Petición FastAPI con acceso a los servicios del estado de la app.

    Returns:
        Payload de ejecución del despachador para el comando getStatus.

    Raises:
        HTTPException: Si falta el dispositivo o falla la ejecución del estado.
    """
    try:
        configured_device = devices_config.get_device(device_id)
        if configured_device is None:
            raise HTTPException(status_code=404, detail=f"No se encontró el dispositivo {device_id}")

        device_type = str(configured_device.get("type", "")).strip()
        if not device_type:
            raise HTTPException(
                status_code=400,
                detail=f"El dispositivo {device_id} no tiene configurado un 'type' válido",
            )

        dispatcher = request.app.state.event_dispatcher
        result = dispatcher.dispatch(
            commands=[
                {
                    "rule": "manual_api_get_status",
                    "device": device_type,
                    "command": "getStatus",
                    "device_id": str(device_id),
                }
            ],
            event={
                "source": "api",
                "action": "getStatus",
                "device_id": str(device_id),
            },
        )

        # Normalizar las respuestas de dispositivos: conservar solo `status` y `online` por dispositivo
        executions = result.get("executions", [])
        simplified: list[dict[str, Any]] = []
        for ex in executions:
            device_id_val = ex.get("device_id")
            name_val = ex.get("target")
            res = ex.get("result") or {}
            status_val = res.get("status") if isinstance(res, dict) else "error"
            online_val = bool(res.get("online")) if isinstance(res, dict) else False
            simplified.append({
                "device_id": device_id_val,
                "name": name_val,
                "status": status_val,
                "online": online_val,
            })

        return {"status": "success", "devices": simplified}
    except HTTPException:
        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo obtener el estado del dispositivo: {str(exc)}") from exc


@router.post("/devices")
def create_device(device: dict[str, Any]) -> dict[str, Any]:
    """Crea una nueva configuración de dispositivo.
    
    Args:
        device: Diccionario de configuración del dispositivo. Debe incluir 'device_id'.
        
    Returns:
        Diccionario con el estado de creación y el siguiente ID de dispositivo disponible.
        
    Raises:
    HTTPException: Si falla la creación del dispositivo (por ejemplo, falta device_id o está duplicado).
    """
    try:
        if "device_id" not in device:
            raise HTTPException(
                status_code=400,
                detail="El dispositivo debe incluir un campo 'device_id'"
            )
        
        success = devices_config.insert_device(device)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo crear el dispositivo (posible device_id duplicado: {device.get('device_id')})"
            )
        
        next_id = devices_config.get_next_available_device_id()
        return {
            "status": "success",
            "message": f"Dispositivo {device.get('device_id')} creado correctamente",
            "device": device,
            "next_device_id": next_id
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el dispositivo: {str(exc)}") from exc


@router.put("/devices/{device_id}")
def update_device(device_id: int, updated_data: dict[str, Any]) -> dict[str, Any]:
    """Actualiza una configuración de dispositivo existente.
    
    Args:
        device_id: Identificador del dispositivo a actualizar.
        updated_data: Diccionario con los campos a actualizar.
        
    Returns:
        Diccionario con el estado de la actualización y el dispositivo actualizado.
        
    Raises:
    HTTPException: Si no se encuentra el dispositivo o falla la actualización.
    """
    try:
        if not devices_config.device_exists(device_id):
            raise HTTPException(status_code=404, detail=f"No se encontró el dispositivo {device_id}")

        success = devices_config.update_device(device_id, updated_data)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo actualizar el dispositivo {device_id}"
            )

        return {
            "status": "success",
            "message": f"Dispositivo {device_id} actualizado correctamente",
            "device": devices_config.get_device(device_id)
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo actualizar el dispositivo: {str(exc)}") from exc


@router.delete("/devices/{device_id}")
def delete_device(device_id: int) -> dict[str, Any]:
    """Elimina una configuración de dispositivo por ID.
    
    Args:
        device_id: Identificador del dispositivo a eliminar.
        
    Returns:
        Diccionario con el estado de eliminación.
        
    Raises:
    HTTPException: Si no se encuentra el dispositivo o falla la eliminación.
    """
    try:
        # Comprobar si el dispositivo existe antes de eliminarlo
        if not devices_config.device_exists(device_id):
            raise HTTPException(status_code=404, detail=f"No se encontró el dispositivo {device_id}")
        
        success = devices_config.delete_device(device_id)
        if not success:
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo eliminar el dispositivo {device_id}"
            )
        
        return {
            "status": "success",
            "message": f"Dispositivo {device_id} eliminado correctamente"
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo eliminar el dispositivo: {str(exc)}") from exc
