"""
Controlador para dispositivos Shelly Gen4 (relé/interruptor).

Este módulo implementa un manejador de dispositivos que se comunica con
dispositivos relé inteligentes Shelly Gen4 mediante su API HTTP RPC. Proporciona
consultas de estado y comandos de control (encender/apagar).

Responsabilidades:
- Consultar el estado del dispositivo mediante el endpoint RPC de Shelly (Shelly.GetStatus).
- Enviar comandos de conmutación (turn_on/turn_off) mediante la API HTTP.
- Gestionar la autenticación usando HTTP Digest Auth con las credenciales proporcionadas.
- Analizar respuestas y devolver diccionarios de resultado normalizados.

Configuración del dispositivo (desde devices.yaml):
    - ip: dirección IP del dispositivo
    - username: nombre de usuario para Digest Auth
    - password: contraseña para Digest Auth

Autor: Jesus Montero
Fecha: 2026
"""

import logging
import os
from typing import Any

import requests
from requests.auth import HTTPDigestAuth

from app.devices.base import Device


logger = logging.getLogger(__name__)


class Shelly1_Gen4_Device(Device):
    """
    Manejador para dispositivos Shelly Gen4.

    Se comunica con dispositivos relé Shelly 1 Gen4 usando HTTP RPC.
    Permite consultar el estado del dispositivo y controlar la salida del interruptor.
    """

    DEVICE_TYPE = "Shelly1_Gen4"

    def __init__(self, device_type: str | None = None) -> None:
        """
        Inicializa el manejador de dispositivos Shelly Gen4.

        Args:
            device_type: Sustitución opcional del nombre del tipo de dispositivo.
                Si no se proporciona, usa el valor por defecto de la clase.
        """
        self._device_type = device_type or self.DEVICE_TYPE

    @property
    def device_type(self) -> str:
        """Devuelve el nombre del tipo de dispositivo."""
        return self._device_type

    def _is_switch_on(self, payload: dict[str, Any]) -> bool:
        """
        Analiza la respuesta RPC de Shelly para determinar si el interruptor está encendido.

        Extrae el estado de salida de la sección "switch:0" del payload de
        estado de Shelly.

        Args:
            payload: La respuesta JSON de Shelly.GetStatus.

        Returns:
            True si la salida del interruptor está activada; False en caso contrario.
        """
        switch_payload = payload.get("switch:0")
        if isinstance(switch_payload, dict):
            return bool(switch_payload.get("output"))
        return False

    def getStatus(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Consulta el estado actual del dispositivo Shelly.

        Envía una petición HTTP GET al endpoint RPC del dispositivo para recuperar
        su estado. Valida que el dispositivo destino tenga dirección IP y
        credenciales antes de intentar la petición.

        Args:
            event: Diccionario de evento que contiene:
                - target_device (dict): Información del dispositivo con claves:
                    - ip (str): Dirección IP del dispositivo Shelly.
                    - username (str): Nombre de usuario para Digest Auth.
                    - password (str): Contraseña para Digest Auth.

        Returns:
            dict: Diccionario de resultado con campos:
                - device (str): Tipo de dispositivo.
                - target (dict): Información del dispositivo destino.
                - command (str): "getStatus".
                - status (str): "ok", "error" o "simulated".
                - online (bool): True si el dispositivo es accesible.
                - http_status (int, optional): Código HTTP de respuesta en caso de éxito.
                - response (dict, optional): Respuesta JSON de Shelly.
                - error (str, optional): Mensaje de error si falla.
        """
        target_device = event.get("target_device", {})
        ip = str(target_device.get("ip", "")).strip()
        if not ip:
            return {
                "device": self.device_type,
                "target": target_device,
                "command": "getStatus",
                "status": "error",
                "online": False,
                "error": "Falta la IP del dispositivo destino.",
            }

        username = str(target_device.get("username", "")).strip()
        password = str(target_device.get("password", "")).strip()

        if not username or not password:
            return {
                "device": self.device_type,
                "target": target_device,
                "command": "getStatus",
                "status": "error",
                "online": False,
                "error": "Faltan las credenciales Digest de Shelly (usuario/contraseña).",
            }

        # Por el momento se codifica de forma fija el endpoint para Shelly Gen4.
        url = f"http://{ip}/rpc/Shelly.GetStatus"

        try:
            response = requests.get(
                url,
                auth=HTTPDigestAuth(username, password),
                timeout=8,
            )
            response.raise_for_status()
            payload = response.json()
            return {
                "device": self.device_type,
                "target": target_device,
                "command": "getStatus",
                "status": "ok",
                "online": True,
                "http_status": response.status_code,
                "response": payload,
            }
        except requests.HTTPError as exc:
            error_msg = f"Error HTTP al comprobar el estado de Shelly: {exc}"
            logger.warning("La comprobación de estado de Shelly falló para ip=%s: %s", ip, exc)
        except requests.RequestException as exc:
            error_msg = f"Error de conexión al comprobar el estado de Shelly: {exc}"
            logger.warning("Error en la petición de estado de Shelly para ip=%s: %s", ip, exc)
        except ValueError as exc:
            error_msg = "La respuesta de estado de Shelly no es JSON válido."
            logger.warning("Shelly devolvió JSON no válido para ip=%s: %s", ip, exc)


        return {
                "device": self.device_type,
                "target": target_device,
                "command": "getStatus",
                "status": "error",
                "online": False,
                "error": error_msg,
        }

    def turn_on(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Enciende el interruptor del dispositivo Shelly.

        Primero consulta el estado del dispositivo para verificar que está en línea y
        obtener el estado actual del interruptor. Si ya está encendido, devuelve
        éxito sin enviar otro comando. Si está apagado, envía un comando RPC
        Switch.Set para encenderlo.

        Args:
            event: Diccionario de evento que contiene:
                - target_device (dict): Información del dispositivo con claves:
                    - ip (str): Dirección IP del dispositivo Shelly.
                    - username (str): Nombre de usuario para Digest Auth.
                    - password (str): Contraseña para Digest Auth.

        Returns:
            dict: Diccionario de resultado con campos:
                - device (str): Tipo de dispositivo.
                - target (dict): Información del dispositivo destino.
                - command (str): "turn_on".
                - status (str): "ok" o "error".
                - online (bool): True si el dispositivo es accesible.
                - already_on (bool, optional): True si ya estaba encendido.
                - status_check (dict): Resultado de la consulta getStatus.
                - http_status (int, optional): Código HTTP de respuesta en caso de éxito.
                - response (dict, optional): Respuesta JSON de Shelly.
                - error (str, optional): Mensaje de error si falla.
        """
        status_result = self.getStatus(event)
        if status_result.get("status") != "ok":
            return {
                "device": self.device_type,
                "target": event.get("target_device", {}),
                "command": "turn_on",
                "status": "error",
                "online": False,
                "status_check": status_result,
                "error": "Shelly no es accesible o no está funcionando.",
            }

        payload = status_result.get("response", {})
        if not isinstance(payload, dict):
            return {
                "device": self.device_type,
                "target": event.get("target_device", {}),
                "command": "turn_on",
                "status": "error",
                "online": True,
                "status_check": status_result,
                "error": "La respuesta de estado de Shelly no es válida.",
            }

        is_on = self._is_switch_on(payload)
        if is_on:
            return {
                "device": self.device_type,
                "target": event.get("target_device", {}),
                "command": "turn_on",
                "status": "ok",
                "online": True,
                "already_on": True,
                "status_check": status_result,
                "response": payload,
            }

        target_device = event.get("target_device", {})
        ip = str(target_device.get("ip", "")).strip()
        username = str(target_device.get("username", "")).strip()
        password = str(target_device.get("password", "")).strip()
        url = f"http://{ip}/rpc/Switch.Set"

        try:
            response = requests.get(
                url,
                params={"id": 0, "on": "true"},
                auth=HTTPDigestAuth(username, password),
                timeout=8,
            )
            response.raise_for_status()
            switch_payload = response.json()
            return {
                "device": self.device_type,
                "target": target_device,
                "command": "turn_on",
                "status": "ok",
                "online": True,
                "already_on": False,
                "status_check": status_result,
                "http_status": response.status_code,
                "response": switch_payload,
            }
        except requests.HTTPError as exc:
            error_msg = f"Error HTTP al encender Shelly: {exc}"
            logger.warning("turn_on de Shelly falló para ip=%s: %s", ip, exc)
        except requests.RequestException as exc:
            error_msg = f"Error de conexión al encender Shelly: {exc}"
            logger.warning("Error en la petición turn_on de Shelly para ip=%s: %s", ip, exc)
        except ValueError:
            error_msg = "La respuesta de turn_on de Shelly no es JSON válido."
            logger.warning("turn_on de Shelly devolvió JSON no válido para ip=%s", ip)


        return {
                "device": self.device_type,
                "target": target_device,
                "command": "turn_on",
                "status": "error",
                "online": True,
                "status_check": status_result,
                "error": error_msg,
       }

    def turn_off(self, event: dict[str, Any]) -> dict[str, Any]:
        """
        Apaga el interruptor del dispositivo Shelly.

        Primero consulta el estado del dispositivo para verificar que está en línea y
        obtener el estado actual del interruptor. Si ya está apagado, devuelve
        éxito sin enviar otro comando. Si está encendido, envía un comando RPC
        Switch.Set para apagarlo.

        Args:
            event: Diccionario de evento que contiene:
                - target_device (dict): Información del dispositivo con claves:
                    - ip (str): Dirección IP del dispositivo Shelly.
                    - username (str): Nombre de usuario para Digest Auth.
                    - password (str): Contraseña para Digest Auth.

        Returns:
            dict: Diccionario de resultado con campos:
                - device (str): Tipo de dispositivo.
                - target (dict): Información del dispositivo destino.
                - command (str): "turn_off".
                - status (str): "ok" o "error".
                - online (bool): True si el dispositivo es accesible.
                - already_off (bool, optional): True si ya estaba apagado.
                - status_check (dict): Resultado de la consulta getStatus.
                - http_status (int, optional): Código HTTP de respuesta en caso de éxito.
                - response (dict, optional): Respuesta JSON de Shelly.
                - error (str, optional): Mensaje de error si falla.
        """
        status_result = self.getStatus(event)
        if status_result.get("status") != "ok":
            return {
                "device": self.device_type,
                "target": event.get("target_device", {}),
                "command": "turn_off",
                "status": "error",
                "online": False,
                "status_check": status_result,
                "error": "Shelly no es accesible o no está funcionando.",
            }

        payload = status_result.get("response", {})
        if not isinstance(payload, dict):
            return {
                "device": self.device_type,
                "target": event.get("target_device", {}),
                "command": "turn_off",
                "status": "error",
                "online": True,
                "status_check": status_result,
                "error": "La respuesta de estado de Shelly no es válida.",
            }

        is_on = self._is_switch_on(payload)
        if not is_on:
            return {
                "device": self.device_type,
                "target": event.get("target_device", {}),
                "command": "turn_off",
                "status": "ok",
                "online": True,
                "already_off": True,
                "status_check": status_result,
                "response": payload,
            }

        target_device = event.get("target_device", {})
        ip = str(target_device.get("ip", "")).strip()
        username = str(target_device.get("username", "")).strip()
        password = str(target_device.get("password", "")).strip()
        url = f"http://{ip}/rpc/Switch.Set"

        try:
            response = requests.get(
                url,
                params={"id": 0, "on": "false"},
                auth=HTTPDigestAuth(username, password),
                timeout=8,
            )
            response.raise_for_status()
            switch_payload = response.json()
            return {
                "device": self.device_type,
                "target": target_device,
                "command": "turn_off",
                "status": "ok",
                "online": True,
                "already_off": False,
                "status_check": status_result,
                "http_status": response.status_code,
                "response": switch_payload,
            }
        except requests.HTTPError as exc:
            error_msg = f"Error HTTP al apagar Shelly: {exc}"
            logger.warning("turn_off de Shelly falló para ip=%s: %s", ip, exc)
        except requests.RequestException as exc:
            error_msg = f"Error de conexión al apagar Shelly: {exc}"
            logger.warning("Error en la petición turn_off de Shelly para ip=%s: %s", ip, exc)
        except ValueError:
            error_msg = "La respuesta de turn_off de Shelly no es JSON válido."
            logger.warning("turn_off de Shelly devolvió JSON no válido para ip=%s", ip)


        return {
                "device": self.device_type,
                "target": target_device,
                "command": "turn_off",
                "status": "error",
                "online": True,
                "status_check": status_result,
                "error": error_msg,
        }

    def execute(self, command: str, event: dict[str, Any]) -> dict[str, Any]:
        """
        Ejecuta un comando nombrado en el dispositivo Shelly.

        Despacha el comando al método manejador adecuado. Los comandos
        reconocidos no distinguen mayúsculas y minúsculas: "getstatus", "turn_on",
        "turn_off". Los comandos desconocidos se registran como respuestas simuladas.

        Args:
            command: El nombre del comando (por ejemplo, "getStatus", "turn_on", "turn_off").
            event: Diccionario de evento pasado al manejador del comando.

        Returns:
            dict: Resultado del manejador invocado o una respuesta simulada
                si el comando no se reconoce.
        """
        normalized_command = command.strip().lower()
        if normalized_command in {"getstatus"}:
            return self.getStatus(event)
        if normalized_command == "turn_on":
            return self.turn_on(event)
        if normalized_command == "turn_off":
            return self.turn_off(event)
        
        # Si el comando no se reconoce, devolver una respuesta simulada y registrar una advertencia.
        logger.warning("Se recibió un comando no reconocido '%s' para el dispositivo Shelly.", command)
    
        target_device = event.get("target_device", {})
        return {
            "device": self.device_type,
            "target": target_device,
            "command": command,
            "status": "simulated",
            "event": event,
        }
