import logging
from typing import Any

from app.devices.registry import DeviceRegistry


logger = logging.getLogger(__name__)


class EventDispatcher:
    def __init__(self, device_registry: DeviceRegistry) -> None:
        self._device_registry = device_registry
        logger.debug("EventDispatcher inicializado.")

    def dispatch(
        self,
        commands: list[dict[str, Any]],
        event: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        logger.info("Ejecutando %d comando(s).", len(commands))
        executions: list[dict[str, Any]] = []

        for command_spec in commands:
            if not isinstance(command_spec, dict):
                logger.error("Especificación de comando inválida: %s", command_spec)
                raise RuntimeError("Cada comando debe ser un objeto.")

            rule_name = str(command_spec.get("rule", "unnamed"))
            device_type = command_spec.get("device")
            command = command_spec.get("command")
            if not device_type or not command:
                logger.error("El comando '%s' no es válido: %s", rule_name, command_spec)
                raise RuntimeError(f"El comando '{rule_name}' no es válido.")

            routing_event = event or {}
            device_id = self._extract_device_id(command_spec, routing_event)
            selector = self._extract_selector(command_spec, routing_event)

            targets: list[tuple[Any, dict[str, Any]]]
            if device_id is not None:
                logger.debug(
                    "Executing command from rule '%s' on device_id=%s device_type=%s command=%s.",
                    rule_name,
                    device_id,
                    device_type,
                    command,
                )
                device, target_config = self._device_registry.resolve_by_device_id(
                    device_id,
                    expected_device_type=device_type,
                )
                targets = [(device, target_config)]
            else:
                if not selector:
                    logger.error("Falta el destino de enrutado en comando/evento. command=%s event=%s", command_spec, routing_event)
                    raise RuntimeError(
                        "Falta el destino de enrutado en comando/evento. Proporcione device_id "
                        "o selector para resolver el comando."
                    )
                logger.debug(
                    "Executing command from rule '%s' by selector=%s device_type=%s command=%s.",
                    rule_name,
                    selector,
                    device_type,
                    command,
                )
                targets = self._device_registry.resolve_many(
                    device_type=device_type,
                    selector=selector,
                )

            for device, target_config in targets:
                execution_event = {**routing_event, "target_device": target_config}
                
                # IMPORTANTE: Enviar el comando al dispositivo y capturar el resultado.
                result = device.execute(command, execution_event)
                logger.info(
                    "Executed command from rule '%s' on device_id=%s type=%s command=%s.",
                    rule_name,
                    target_config.get("device_id"),
                    device_type,
                    command,
                )
                executions.append(
                    {
                        "rule": rule_name,
                        "device": device_type,
                        "device_id": target_config.get("device_id"),
                        "target": target_config.get("name"),
                        "command": command,
                        "selector": selector,
                        "result": result,
                    }
                )

        if (len(executions) > 0):
            logger.info("Ejecución de comandos completada con %d ejecución(es).", len(executions))
        else:
            logger.warning("La ejecución de comandos terminó sin ejecuciones. Revise el enrutado de comandos y la resolución del dispositivo: %s", event)
        
        return {
            "status": "processed",
            "commands": len(commands),
            "executions": executions,
        }

    def _extract_device_id(
        self,
        command: dict[str, Any],
        event: dict[str, Any],
    ) -> str | None:
        command_device_id = command.get("device_id")
        if command_device_id is not None:
            value = str(command_device_id).strip()
            if value:
                logger.debug("Usando command.device_id=%s.", value)
                return value

        command_target = command.get("target")
        if isinstance(command_target, dict):
            command_target_device_id = command_target.get("device_id")
            if command_target_device_id is not None:
                value = str(command_target_device_id).strip()
                if value:
                    logger.debug("Usando command.target.device_id=%s.", value)
                    return value

        event_target = event.get("target")
        if isinstance(event_target, dict):
            event_target_device_id = event_target.get("device_id")
            if event_target_device_id is not None:
                value = str(event_target_device_id).strip()
                if value:
                    logger.debug("Usando event.target.device_id=%s.", value)
                    return value

        event_device_id = event.get("device_id")
        if event_device_id is not None:
            value = str(event_device_id).strip()
            if value:
                logger.debug("Usando event.device_id=%s.", value)
                return value

        return None

    def _extract_selector(
        self,
        command: dict[str, Any],
        event: dict[str, Any],
    ) -> dict[str, Any] | None:
        command_selector = command.get("selector")
        if isinstance(command_selector, dict) and command_selector:
            return dict(command_selector)

        command_target = command.get("target")
        if isinstance(command_target, dict):
            command_target_selector = command_target.get("selector")
            if isinstance(command_target_selector, dict) and command_target_selector:
                return dict(command_target_selector)

        event_target = event.get("target")
        if isinstance(event_target, dict):
            event_target_selector = event_target.get("selector")
            if isinstance(event_target_selector, dict) and event_target_selector:
                return dict(event_target_selector)

        return None
