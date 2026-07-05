"""Cliente de integración de SportGo.

Este módulo se encarga de:
- Gestionar la autenticación basada en token contra la API de SportGo.
- Obtener los datos de ocupación de pistas y normalizar las reservas.
- Inferir transiciones del estado de la luz por pista y generar eventos.

La implementación utiliza únicamente módulos de la biblioteca estándar de
Python para construir peticiones HTTP, analizar JSON y registrar logs.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
import json
import logging
from app.core.logging_config import TRACE_LEVEL
from typing import Any, Callable
from urllib import error, parse, request

from app.integrations.base import SaaSIntegration

# Activar el registro de logs
logger = logging.getLogger(__name__)

class SportGoClient(SaaSIntegration):
    """Implementación de la integración SaaS para la API de SportGo.

    El cliente mantiene un token temporal, realiza peticiones autenticadas y
    traduce los datos de reservas en eventos de dominio relacionados con los
    cambios de encendido/apagado de la luz por pista.
    """

    def __init__(
        self,
        base_url: str,

        auth_login_path: str | None = None,
        auth_login_payload: dict[str, Any] | None = None,
        poll_interval_seconds: int = 60,
        token_ttl_seconds: int = 3600,
        request_timeout_seconds: float = 10.0,

        occupancy_path: str | None = None,

    ) -> None:
        """Inicializa el cliente con la configuración de autenticación y ocupación.

        Args:
            base_url: URL base de la API de SportGo.
            auth_login_path: Ruta relativa del endpoint de autenticación.
            auth_login_payload: Cuerpo JSON usado para solicitar un token.
            poll_interval_seconds: Intervalo de sondeo sugerido.
            token_ttl_seconds: Tiempo de vida del token en segundos.
            request_timeout_seconds: Tiempo límite para peticiones HTTP.
            occupancy_path: Ruta relativa del endpoint de ocupación.
        """

        # Guardar parámetros
        self._base_url = base_url

        # Parámetros del token
        self._auth_login_path = auth_login_path
        self._auth_login_payload = auth_login_payload
        self._token_ttl_seconds = token_ttl_seconds
        self._request_timeout_seconds = request_timeout_seconds
        self._poll_interval_seconds = poll_interval_seconds
        self._token: str | None = None
        self._token_expires_at: datetime | None = None

        # Parámetros de ocupación
        self._occupancy_path = occupancy_path
        self._track_light_state: dict[str, bool] = {}
        self._event_processor: Callable[[dict[str, Any]], dict[str, Any]] | None = None

    # TODO: Definir tipos de evento para esta fuente, por ejemplo "light_on", "light_off"
    # _event_types = {"light_on", "light_off"}
    # Esto debe pasarse al frontend como tipos de evento disponibles para usar en reglas. 
    # Por ahora podemos usar el tipo de evento como un campo de texto libre en el payload del evento, 
    # pero idealmente deberíamos tener un conjunto predefinido de tipos de evento por integración con una estructura común.
    
    @property
    def name(self) -> str:
        """Nombre identificador de esta integración."""
        return "sportgo"

#region GESTIÓN DE TOKEN

    # Verificar si el token actual es válido
    def has_valid_token(self) -> bool:
        """Devuelve si existe un token y no ha caducado."""
        if not self._token or not self._token_expires_at:
            return False

        return datetime.now(timezone.utc) < self._token_expires_at

    # Actualizar el token actual y calcular su expiración
    def set_token(self, token: str) -> None:
        """Guarda el token y calcula su fecha de expiración."""
        self._token = token
        self._token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self._token_ttl_seconds
        )

    # Asegurar un token válido
    def ensure_token(self) -> bool:
        """Asegura que exista un token válido.

        Returns:
            True si se solicitó y guardó un token nuevo.
            False si el token actual seguía siendo válido.
        """
        if self.has_valid_token():
            return False

        new_token = self._request_token()
        self.set_token(new_token)
        return True

    # Solicitar un token nuevo a la API de SportGo usando el payload de autenticación configurado.
    def _request_token(self) -> str:
        """Solicita un token nuevo al endpoint de autenticación.

        Raises:
            RuntimeError: Si hay un error de conexión, JSON inválido o falta el token.

        Returns:
            Token extraído de la respuesta de SportGo.
        """

        # Construir la petición con el payload de autenticación codificado en JSON
        payload = json.dumps(self._auth_login_payload).encode("utf-8")
        auth_url = parse.urljoin(self._base_url, self._auth_login_path)
        req = request.Request(
            auth_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        logger.debug("Solicitando un nuevo token a la API de SportGo en %s", auth_url)

        # Conectar con la URL de la API de SportGo
        try:
            with request.urlopen(req, timeout=self._request_timeout_seconds) as response:
                raw_data = response.read().decode("utf-8")
        except error.URLError as exc:
            logger.error("No se pudo conectar con la API de SportGo para recuperar el token: %s", exc)
            raise RuntimeError(f"No se pudo obtener el token de SportGo: {exc}") from exc

        # Analizar la respuesta como JSON
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as exc:
            logger.error("Respuesta JSON no válida de la API de SportGo: %s", exc)
            raise RuntimeError("La respuesta de autenticación de SportGo no es JSON válido.") from exc
        
        # Extraer el token
        token = self._extract_token(data)
        if not token:
            logger.error("La respuesta de autenticación de SportGo no incluye un token.")
            raise RuntimeError("La respuesta de autenticación de SportGo no incluye un token.")

        logger.debug("Token recuperado correctamente de la API de SportGo.")

        return token

    def _extract_token(self, payload: Any) -> str | None:
        """Extrae un token de estructuras JSON heterogéneas.

        Busca una cadena de token simple, una clave token directa o, de forma
        recursiva, dentro de un campo response.
        """

        logger.log(TRACE_LEVEL, "Intentando extraer el token del payload: %s", payload)

        # Validar si el payload es una cadena no vacía, que puede ser directamente el token.
        if isinstance(payload, str):
            return payload if payload.strip() else None

        # Si el payload no es un diccionario, no podemos extraer un token de él.
        if not isinstance(payload, dict):
            return None

        # La respuesta puede incluir el token directamente en el payload. Se usa descenso recursivo.
        direct_token = payload.get("token")
        if isinstance(direct_token, str) and direct_token.strip():
            return direct_token

        # La respuesta puede anidar el token dentro de un campo "response".
        nested_payload = payload.get("response")
        if isinstance(nested_payload, dict):
            logger.log(TRACE_LEVEL, "Intentando extraer el token del payload anidado: %s", nested_payload)
            return self._extract_token(nested_payload)

        return None

#endregion 

#region OCUPACIÓN

    # Obtener datos de ocupación de la API de SportGo, asegurando que haya un token válido antes de hacer la petición.
    def get_occupancy_data(self) -> bool:
        """Obtiene los datos de ocupación, los procesa y genera eventos cuando es necesario.

        Raises:
            RuntimeError: Si se solicita ocupación sin un token válido.

        Returns:
            True si la información de ocupación se obtuvo y procesó.
            False si la respuesta no incluía reservas normalizadas.
        """
        
        if not self.has_valid_token():
            raise RuntimeError("No se pueden obtener los datos de ocupación: no hay un token válido disponible.")

        # Cargar los datos de ocupación desde la API.
        logger.debug("Obteniendo datos de ocupación desde la API de SportGo.")
        data_occupancy = self._request_occupancy()
        if not data_occupancy:
            logger.info("La respuesta de ocupación de SportGo no incluye reservas normalizadas.")
            return False

        logger.debug("Datos de ocupación obtenidos correctamente desde la API de SportGo.")
        logger.log(TRACE_LEVEL,"Datos de ocupación de SportGo normalizados: %s", data_occupancy)

        # TODO: Procesar los datos de ocupación según sea necesario. Por ahora solo los registramos.
        # La idea es que exista un proceso que verifique y lance eventos si es necesario.
        # Ojo con la pista que está encendida y hay que apagarla, y viceversa. Veremos cómo controlarlo.
        # Entiendo que lo adecuado será tomar las horas de inicio y fin.
        self._process_occupancy_data(data_occupancy)


        return True

    def _process_occupancy_data(self, data_occupancy: dict[str, list[dict[str, str]]]) -> None:
        """Evalúa las ventanas de ocupación y genera eventos de encendido/apagado cuando cambia el estado de la pista.

        La estructura esperada es:
            {"<idPista>": [{"inicio": "HH:MM", "fin": "HH:MM", "luz": "true|false"}, ...]}

        Una pista se considera con la luz encendida cuando la hora local actual está dentro de al menos una
        ventana de reserva que requiere luz.
        """

        # Obtener la hora local actual para comparar
        now_local = datetime.now().time()

        # Recorrer cada pista y sus reservas para determinar el estado de luz deseado.
        for track_id, reservations in data_occupancy.items():
            desired_state = False
            active_window: tuple[str, str] | None = None

            # Recorrer las reservas
            for reservation in reservations:
                
                # Extraer horas de inicio y fin
                start_in_text = reservation.get("inicio", "")
                end_in_text = reservation.get("fin", "")
                light_text = reservation.get("luz", "")
                start_time = self._parse_hhmm_time(start_in_text)
                end_time = self._parse_hhmm_time(end_in_text)
                if start_time is None or end_time is None:
                    logger.debug("Omitiendo reserva con rango horario no válido pista=%s inicio=%s fin=%s", track_id, start_in_text, end_in_text)
                    continue

                # Extraer el requisito de luz
                requires_light = self._parse_bool(light_text)
                if not requires_light:
                    continue

                # Verificar si la hora actual está dentro de la ventana de reserva
                if self._is_time_in_range(now_local, start_time, end_time):
                    desired_state = True
                    active_window = (start_in_text, end_in_text)
                    break

            # Determinar el estado actual y cambiarlo si es necesario
            previous_state = self._track_light_state.get(track_id)
            self._track_light_state[track_id] = desired_state
            if previous_state is not None and previous_state == desired_state:
                logger.debug("No hay cambio de estado de luz para la pista=%s estado_actual=%s", track_id, desired_state)
                # No hay cambio de estado, no se genera evento.
                continue

            # Generar un evento por el cambio de estado
            event_type = "light_on" if desired_state else "light_off"
            event_payload: dict[str, Any] = {
                "source": self.name,
                "type": event_type,
                "track_id": track_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "meta": {
                    "active_window": {
                        "inicio": active_window[0],
                        "fin": active_window[1],
                    }
                    if active_window
                    else None,
                },
            }
            
            ## Enviar el evento
            result = self.send_event(event_payload)
            logger.log(
                TRACE_LEVEL,
                "Transición de ocupación procesada pista=%s anterior=%s actual=%s tipo_evento=%s resultado=%s",
                track_id,
                previous_state,
                desired_state,
                event_type,
                result,
            )

    def _parse_hhmm_time(self, value: str) -> time | None:
        """Convierte una cadena HH:MM en un objeto time.

        Devuelve None cuando el valor no se puede interpretar.
        """
        try:
            return datetime.strptime(value.strip(), "%H:%M").time()
        except (ValueError, AttributeError):
            return None

    def _parse_bool(self, value: Any) -> bool:
        """Normaliza distintas representaciones verdaderas/falsas a bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "on"}
        return False

    def _is_time_in_range(self, now_value: time, start_value: time, end_value: time) -> bool:
        """Comprueba si una hora cae dentro de un intervalo.

        Soporta tanto ventanas del mismo día como ventanas que cruzan medianoche.
        """
        # Soporta ventanas del mismo día y ventanas que cruzan medianoche.
        if start_value <= end_value:
            return start_value <= now_value < end_value
        return now_value >= start_value or now_value < end_value
    
    def _request_occupancy(self) -> dict[str, Any] | None:
        """Solicita la ocupación a SportGo y devuelve las reservas normalizadas.

        Returns:
            Diccionario de reservas por pista, o None si hay errores o no hay datos.
        """

        # Construir la petición con fecha dinámica e idPista fijo
        # TODO: Reemplazar idPista=4 fijo por una selección dinámica de pista desde la petición/configuración
        current_date = datetime.now().strftime("%Y-%m-%d")
        params = {
            "idPista": "4",
            "date": current_date,
        }
        occupancy_url = parse.urljoin(self._base_url, self._occupancy_path)

        if params:
            query = parse.urlencode(params, doseq=True)
            separator = "&" if "?" in occupancy_url else "?"
            occupancy_url = f"{occupancy_url}{separator}{query}"

        req = request.Request(
            occupancy_url,
            headers={
                "Accept": "application/json",
                "Authorization": f"Bearer {self._token}",
            },
            method="GET",
        )

        # Conectar con la URL de la API de SportGo.
        try:
            with request.urlopen(req, timeout=self._request_timeout_seconds) as response:
                raw_data = response.read().decode("utf-8")
        except error.URLError as exc:
            logger.error("No se pudo conectar con la API de SportGo para recuperar la ocupación: %s", exc)
            return None
        
        # Analizar la respuesta como JSON.
        try:
            data = json.loads(raw_data)
        except json.JSONDecodeError as exc:
            logger.error("Respuesta JSON no válida de la API de SportGo: %s", exc)
            return None

        # TODO: Aquí hago una trampa y cambio data por el contenido de ejemplo_reservas.json
        with open("../config/ejemplo_reservas.json", "r", encoding="utf-8") as f:
            data = json.load(f) 

        # Extraer pista, horas y luz.
        data_hours = self._extract_hours(data)
        if not data_hours:
            logger.info("La respuesta de ocupación de SportGo no incluye horas.")
        else:
            logger.log(TRACE_LEVEL, "Horas de ocupación de SportGo extraídas: %s", data_hours)
        
        return data_hours

    def _extract_hours(self, payload: Any) -> dict[str, list[dict[str, str]]] | None:
        """Normaliza reservas desde múltiples formatos de respuesta.

        Soporta estructuras tipo lista o diccionario con claves alternativas:
        - pista: idPista o pista
        - reservas: reservas u horas
        - campos de horario: start/inicio, end/fin, light/luz
        """
        
        logger.log(TRACE_LEVEL, "Intentando extraer las horas del payload: %s", payload)

        # Buscar una lista de pistas con sus reservas. El primer nivel es un diccionario.
        if isinstance(payload, list):
            normalized: dict[str, list[dict[str, str]]] = {}
            
            # Recorrer cada pista.
            for item in payload:
                if not isinstance(item, dict):
                    continue

                pista = item.get("idPista") or item.get("pista")
                reservas = item.get("reservas") or item.get("horas")

                if pista is None or not isinstance(reservas, list):
                    continue

                normalized_reservas: list[dict[str, str]] = []
                
                # Dentro de la pista, recorrer cada reserva.
                for reserva in reservas:
                    if not isinstance(reserva, dict):
                        continue

                    inicio = reserva.get("start") or reserva.get("inicio")
                    fin = reserva.get("end") or reserva.get("fin")
                    luz = reserva.get("light") or reserva.get("luz")
                    
                    if not isinstance(inicio, str) or not inicio.strip():
                        continue
                    if not isinstance(fin, str) or not fin.strip():
                        continue
                    if not isinstance(luz, str) or not luz.strip():
                        continue

                    normalized_reservas.append({"inicio": inicio, "fin": fin, "luz": luz})

                if normalized_reservas:
                    normalized[str(pista)] = normalized_reservas

            # Aquí devolvemos los datos normalizados de pistas y sus reservas.
            return normalized or None

        # Si el payload no es un diccionario, no podemos extraer datos de él.
        # No podemos verificar este caso al inicio de la función porque algunas respuestas pueden ser una lista directamente.
        if not isinstance(payload, dict):
            return None

        # La respuesta puede incluir los datos directamente en el payload. Se usa descenso recursivo.
        direct_data = payload.get("horas")
        if isinstance(direct_data, (list, dict)):
            return self._extract_hours(direct_data)

        # La respuesta puede anidar los datos dentro de un campo "response".
        nested_payload = payload.get("response")
        if isinstance(nested_payload, (list, dict)):
            logger.log(TRACE_LEVEL, "Intentando extraer las horas del payload anidado: %s", nested_payload)
            return self._extract_hours(nested_payload)

        if "idPista" in payload or "reservas" in payload:
            return self._extract_hours([payload])

        return None


#endregion

#region OBTENER PISTAS DE EMPRESA (Servirá para configurar los dispositivos por pista que se deberán añadir automáticamente en devices.yaml)

#endregion

#region ENVIAR EVENTOS

    def set_event_processor(
        self,
        processor: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Registra un callable que enruta los eventos de integración al pipeline de dominio."""
        self._event_processor = processor


    def send_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Envía un evento a través del procesador configurado o cae en simulación."""
        if self._event_processor is not None:
            return self._event_processor(event)

        return {
            "integration": self.name,
            "status": "simulated",
            "base_url": self._base_url,
            "has_valid_token": self.has_valid_token(),
            "event": event,
        }

#endregion