"""Planificador de sondeo de SportGo para el mantenimiento del token y la ocupación.

Este módulo coordina la tarea en segundo plano responsable de mantener válido el
token de acceso de SportGo, obtener datos de ocupación y reenviar los eventos
generados al motor de reglas y al despachador de eventos de la aplicación.

Responsabilidades:
	- Inicializar el cliente de SportGo a partir de la configuración SaaS.
	- Iniciar un bucle combinado de sondeo para refrescar el token y recuperar la ocupación.
	- Conectar los eventos generados por SportGo con el motor de reglas y el despachador.
	- Cancelar y limpiar la tarea en segundo plano durante el apagado de la aplicación.

Flujo de sondeo:
	1. Validar la configuración del proveedor y los payloads requeridos.
	2. Crear el cliente de SportGo y registrar la función de procesamiento de eventos.
	3. Ejecutar un único bucle en segundo plano que renueva el token y consulta datos.
	4. En el apagado, cancelar la tarea en segundo plano y esperar su limpieza.

Autor:
	Jesus Montero

Fecha:
	2026

Ejemplo:
	>>> from app.integrations.sportgo.sportgo_scheduler import startup_sportgo_polling

"""

from __future__ import annotations

# Importaciones de la biblioteca estándar
import asyncio
import logging
from typing import Any

# Importaciones de terceros
from fastapi import FastAPI

# Importaciones locales de la aplicación
from app.integrations.sportgo.sportgo_client import SportGoClient

# Activar el registro de logs
logger = logging.getLogger(__name__)


async def _sportgo_polling_loop(app: FastAPI) -> None:
	"""Mantiene válido el token de SportGo y consulta datos de ocupación en un único bucle.

	Args:
	    app: Instancia de FastAPI que contiene el cliente compartido de SportGo.
	"""

	client: SportGoClient = app.state.sportgo_client

	# Mantener el token válido y obtener la ocupación en cada iteración.
	while True:
		try:
			refreshed = await asyncio.to_thread(client.ensure_token)
			if refreshed:
				logger.info("Token de SportGo renovado correctamente.")
			else:
				logger.debug("El token de SportGo sigue siendo válido.")

			result_occupancy = await asyncio.to_thread(client.get_occupancy_data)
			if result_occupancy:
				logger.info("Datos de ocupación de SportGo obtenidos correctamente.")
			else:
				logger.info("Los datos de ocupación de SportGo están vacíos o no se pudieron obtener.")

		except Exception as exc:
			logger.error("El sondeo de SportGo falló: %s", exc)

		await asyncio.sleep(client._poll_interval_seconds)


async def startup_sportgo_polling(
	app: FastAPI,
	saas_config: dict[str, Any],
) -> None:
	"""Inicializa el cliente de SportGo e inicia el bucle combinado de sondeo.

	Esta función valida la configuración de SportGo, crea el cliente,
	registra el procesador de eventos de integración y lanza la tarea en segundo plano.

	Args:
	    app: Instancia de FastAPI utilizada para guardar el estado compartido en tiempo de ejecución.
	    saas_config: Configuración del proveedor SaaS cargada desde ``saas.yaml``.

	Notes:
	    - El sondeo se desactiva cuando falta la configuración requerida de SportGo.
	    - El procesador de eventos conecta los eventos de SportGo con el motor de reglas.
	"""

	sportgo_config = saas_config.get("providers", {}).get("sportgo", {})
	if not sportgo_config:
		logger.warning("Falta la configuración del proveedor SportGo; el sondeo de SportGo se desactiva.")
		return

	auth_payload = sportgo_config.get("auth_login_payload", {})
	if not isinstance(auth_payload, dict) or not auth_payload:
		logger.warning("Falta el payload de autenticación de SportGo; el sondeo de SportGo se desactiva.")
		return


	# Lectura compatible con versiones anteriores para la clave de configuración mal escrita usada en el YAML actual.
	occupancy_path = sportgo_config.get("occupancy_path") 
	if not occupancy_path:
		logger.warning("Falta la ruta de ocupación de SportGo; el sondeo de SportGo se desactiva.")
		return

	# Crear el cliente de SportGo.
	app.state.sportgo_client = SportGoClient(
		base_url=str(sportgo_config.get("base_url", "")),
		auth_login_path=str(sportgo_config.get("auth_login_path", "/authLoginEmpresa")),
		auth_login_payload=auth_payload,
		poll_interval_seconds=int(sportgo_config.get("poll_interval_seconds", 60)),
		token_ttl_seconds=int(sportgo_config.get("token_ttl_seconds", 3600)),
		request_timeout_seconds=float(sportgo_config.get("request_timeout_seconds", 10)),
		occupancy_path=str(sportgo_config.get("occupancy_path", "/appts/getHoursOccupied")),
	)

	# Definir la devolución de llamada del procesador de eventos para manejar eventos entrantes y despachar comandos.
	# Esta función es el puente entre el cliente de SportGo, la evaluación de reglas y el despacho.
	def _process_integration_event(event: dict[str, Any]) -> dict[str, Any]:
		"""Procesa eventos de integración de SportGo a través del motor de reglas.

		Args:
		    event: Payload del evento entrante de SportGo.

		Returns:
		    Resultado del despachador tras evaluar reglas y enviar comandos.
		"""

		rule_engine = app.state.rule_engine
		dispatcher = app.state.event_dispatcher
		
		# Evaluar reglas y enviar comandos al despachador.
		commands = rule_engine.evaluate(event)
		return dispatcher.dispatch(commands, event)


	# Insertar el procesador de eventos en el cliente de SportGo.
	app.state.sportgo_client.set_event_processor(_process_integration_event)

	# Iniciar el bucle combinado de sondeo.
	app.state.sportgo_task = asyncio.create_task(_sportgo_polling_loop(app))


async def shutdown_sportgo_polling(app: FastAPI) -> None:
	"""Cancela y limpia la tarea en segundo plano del sondeo de SportGo.

	Args:
	    app: Instancia de FastAPI que contiene la tarea en segundo plano.
	"""

	task: asyncio.Task | None = app.state.sportgo_task
	if task is None:
		return

	task.cancel()
	try:
		await task
	except asyncio.CancelledError:
		pass
