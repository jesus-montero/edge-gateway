"""Punto de entrada de la aplicación backend de edge gateway.

Este módulo crea y configura la aplicación FastAPI utilizada por el servicio
backend. Se encarga de cargar la configuración de arranque, inicializar el
registro, registrar los dispositivos disponibles, crear el motor de reglas y el dispatcher de
eventos, montar el router de la API y gestionar el mantenimiento en segundo
plano de SportGo mediante el ciclo de vida de la aplicación.

Responsabilidades:
	- Cargar la configuración en tiempo de ejecución y la configuración de arranque desde la capa de configuración.
	- Configurar el registro de logs antes de atender peticiones.
	- Crear la instancia de FastAPI y exponerla como ``app``.
	- Registrar CORS para permitir el acceso del frontend durante el desarrollo.
	- Inicializar los servicios de dispositivos, reglas y dispatcher de eventos a partir de la configuración.
	- Iniciar y detener las tareas de mantenimiento de SportGo mediante hooks del lifespan.
	- Incluir el router versionado de la API.

Arquitectura:
	Este módulo actúa como raíz de composición de la aplicación, conectando los
	componentes de infraestructura y exponiendo la app ASGI.

Tareas secundarias:
	- Carga la configuración.
	- Configura el logging.
	- Registra objetos compartidos en ``app.state`` para su uso por dependencias.
	- Dispara rutinas de arranque y apagado para las integraciones de SportGo.

Autor:
	Jesús Montero

Fecha:
	2026


"""

# Importaciones de la biblioteca estándar
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importaciones locales de la aplicación
from app.api.router import api_router
from app.core.config_loader import get_settings, load_startup_configs
from app.core.logging_config import configure_logging
from app.devices.registry import DeviceRegistry
from app.integrations.sportgo.sportgo_scheduler import (
	shutdown_sportgo_polling,
	startup_sportgo_polling,
)
from app.services.event_dispatcher import EventDispatcher
from app.services.rule_engine import RuleEngine

# Activar el registro de logs
logger = logging.getLogger(__name__)

# Cargar la configuración e inicializar
settings = get_settings()
configs = load_startup_configs()
configure_logging(configs["logging"])

# Arranque de los programadores
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
	"""Gestiona los hooks de arranque y apagado de los servicios en segundo plano.

	Este contexto de ciclo de vida inicia las rutinas de mantenimiento de
	SportGo antes de atender peticiones y garantiza un apagado ordenado de
	las tareas cuando la aplicación se detiene.

	Args:
		app: Instancia de FastAPI usada para guardar y compartir el estado de ejecución.

	Yields:
		None: El control vuelve a FastAPI mientras la aplicación está en ejecución.
	"""

	await startup_sportgo_polling(
		app=app,
		saas_config=configs["saas"],
	)
	try:
		yield
	finally:
		await shutdown_sportgo_polling(app)

# Crear la aplicación FastAPI
app = FastAPI(title=str(configs["app"]["app_name"]), lifespan=lifespan)
app.state.settings = settings
app.state.configs = configs
app.state.sportgo_client = None
app.state.sportgo_task = None

# Registrar el middleware CORS
app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://localhost:5173",
		"http://127.0.0.1:5173",
		"http://localhost:5174",
		"http://127.0.0.1:5174",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

# Inicializar el registro de dispositivos
device_registry = DeviceRegistry()
device_registry.register_from_config(configs["devices"])

# Inicializar el motor de reglas
rule_engine = RuleEngine(configs["rules"])

# Inicializar el despachador de eventos
app.state.rule_engine = rule_engine
app.state.event_dispatcher = EventDispatcher(device_registry)

# Montar el router de la API
app.include_router(api_router)
