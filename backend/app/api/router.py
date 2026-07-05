"""Composición del enrutador principal de la API para el backend edge gateway.

Este módulo crea el punto de entrada del enrutador principal para la API HTTP
y monta el router versionado v1 bajo el prefijo ``/api/v1``. Mantiene la
estructura de rutas centralizada para que el arranque de la aplicación pueda
incluir un único enrutador de API.

Responsabilidades:
	- Crear el ``APIRouter`` raíz usado por la API del backend.
	- Montar el router versionado v1 bajo su prefijo público.
	- Proporcionar un único objetivo de importación para ``app.main``.

Autor:
	Jesus Montero

Fecha:
	2026

Ejemplo:
	>>> from app.api.router import api_router

"""

from fastapi import APIRouter

from app.api.v1.router import router as v1_router

api_router = APIRouter()
api_router.include_router(v1_router, prefix="/api/v1")

