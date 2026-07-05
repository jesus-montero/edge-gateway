"""Composición del enrutador de la API versión 1 para el backend edge gateway.

Este módulo agrupa los endpoints públicos de la versión 1 expuestos por la API
del backend. Combina los routers de salud y eventos en un único router
versionado para que el router de API de nivel superior pueda montarlo bajo el
prefijo ``/api/v1``.

Responsabilidades:
	- Crear el ``APIRouter`` versionado para la API pública.
	- Registrar los endpoints de salud.
	- Registrar los endpoints de eventos.

Autor:
	Jesus Montero

Fecha:
	2026

Ejemplo:
	>>> from app.api.v1.router import router

"""

from fastapi import APIRouter

from app.api.v1.endpoints.auth import router as auth_router
from app.api.v1.endpoints.devices import router as devices_router
from app.api.v1.endpoints.events import router as events_router
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.rules import router as rules_router
from app.api.v1.endpoints.saas import router as saas_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(health_router)
router.include_router(events_router)
router.include_router(devices_router)
router.include_router(rules_router)
router.include_router(saas_router)
