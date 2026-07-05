"""Motor de evaluación de reglas para el backend de edge gateway.

Este módulo carga definiciones de reglas desde la configuración, valida su
estructura y evalúa eventos entrantes para producir comandos de dispositivo.
Actúa como la capa de decisión entre eventos de integración entrantes y las
carga útiles de comando de dispositivo que la aplicación distribuye.

Responsabilidades:
    - Analizar y validar la configuración de reglas desde ``config/rules.yaml``.
    - Evaluar eventos entrantes contra reglas configuradas.
    - Construir cargas de comando normalizadas para distribución descendente.
    - Resolver identificadores de dispositivo objetivo y selectores desde reglas o eventos.

Flujo de reglas:
    1. Cargar definiciones de reglas en el momento de inicialización.
    2. Hacer coincidir eventos entrantes usando ``source`` y ``type``.
    3. Construir una o más cargas de comando para acciones coincidentes.
    4. Devolver la lista de comandos al distribuidor de eventos.

Autor:
    Jesus Montero

Fecha:
    2026

Ejemplo:
    >>> engine = RuleEngine({"rules": []})
    >>> engine.evaluate({"source": "sportgo", "type": "occupancy"})

"""

# Standard library imports
from typing import Any


class RuleEngine:
    """Evalúa reglas configuradas y produce comandos de dispositivo.

    El motor valida definiciones de reglas en el momento de construcción y expone un
    único método ``evaluate`` que transforma eventos coincidentes en comandos.
    """

    def __init__(self, rules_config: dict[str, Any]) -> None:
        """Crea un motor de reglas a partir de la configuración proporcionada.

        Args:
            rules_config: Diccionario de configuración analizado que contiene una
                lista ``rules`` de nivel superior.
        """
        # Guardar reglas en memoria
        self._rules = self._parse_rules(rules_config)

    def _parse_rules(self, rules_config: dict[str, Any]) -> list[dict[str, Any]]:
        """Valida y normaliza la lista de reglas desde la configuración.

        Args:
            rules_config: Diccionario de configuración analizado que contiene reglas.

        Returns:
            Una lista validada de diccionarios de reglas.

        Raises:
            RuntimeError: Si la configuración carece de campos de regla requeridos.
        """

        rules = rules_config.get("rules")
        if not isinstance(rules, list):
            raise RuntimeError("config/rules.yaml debe definir una lista 'rules'.")

        # Reglas validadas y añadidas a la lista parsed_rules
        parsed_rules: list[dict[str, Any]] = []
        for index, rule in enumerate(rules):
            if not isinstance(rule, dict):
                raise RuntimeError(f"La regla en el índice {index} debe ser un objeto.")

            when = rule.get("when")
            if not isinstance(when, dict):
                raise RuntimeError(f"La regla '{rule.get('name', index)}' debe incluir un objeto 'when'.")

            source = when.get("source")
            event_type = when.get("type")
            if not source or not event_type:
                raise RuntimeError(
                    f"La regla '{rule.get('name', index)}' debe incluir when.source y when.type."
                )

            actions = rule.get("actions")
            if not isinstance(actions, list) or not actions:
                raise RuntimeError(
                    f"La regla '{rule.get('name', index)}' debe incluir una lista de acciones no vacía."
                )

            parsed_rules.append(rule)

        return parsed_rules


    def evaluate(self, event: dict[str, Any]) -> list[dict[str, Any]]:
        """Evalúa un evento entrante contra todas las reglas configuradas.

        Args:
            event: Carga de evento entrante que contiene al menos ``source`` y
                ``type``.

        Returns:
            Una lista de cargas de comando normalizadas producidas por reglas coincidentes.

        Raises:
            RuntimeError: Si al evento le faltan campos de enrutamiento requeridos.
        """

        source = event.get("source")
        event_type = event.get("type")

        if not source or not event_type:
            raise RuntimeError("El evento entrante debe incluir 'source' y 'type'.")

        commands: list[dict[str, Any]] = []
        for rule in self._rules:
            when = rule["when"]
            if when.get("source") == source and when.get("type") == event_type:
                commands.extend(self._build_commands(rule, event))

        return commands


    def _build_commands(self,rule: dict[str, Any],event: dict[str, Any]) -> list[dict[str, Any]]:
        """Construye cargas de comando para una regla que coincidió con un evento.

        Args:
            rule: Diccionario de regla que coincidió con el evento.
            event: Carga de evento entrante utilizada para resolver objetivos y selectores.

        Returns:
            Una lista de diccionarios de carga de comando listos para despacho.

        Raises:
            RuntimeError: Si una acción está malformada o no puede resolver su objetivo.
        """

        rule_name = str(rule.get("name", "unnamed"))
        commands: list[dict[str, Any]] = []

        for action in rule.get("actions", []):
            if not isinstance(action, dict):
                raise RuntimeError(f"La regla '{rule_name}' tiene una acción inválida: {action}")

            device_type = action.get("device")
            command = action.get("command")
            if not device_type or command is None:
                raise RuntimeError(f"La regla '{rule_name}' tiene un dispositivo o comando inválido: {device_type} - {command}")

            device_id = self._extract_device_id(action, event)
            selector = self._extract_selector(action)
            if selector is None:
                selector = self._infer_selector_from_event(
                    device_type=str(device_type),
                    event=event,
                )

            # Para crear comando es necesario tener un device_id o un selector
            if device_id is None and not selector:
                raise RuntimeError("Objetivo faltante en acción/evento. No se proporciona device_id ni selector. ")

            # Crear comando
            command_payload: dict[str, Any] = {
                "rule": rule_name,
                "device": device_type,
                "command": command,
            }

            # Device_id se prefiere sobre selector
            if device_id is not None:
                command_payload["device_id"] = device_id
            if selector:
                command_payload["selector"] = selector

            commands.append(command_payload)

        return commands


# region UTILS

    def _extract_device_id(
        self,
        action: dict[str, Any],
        event: dict[str, Any],
    ) -> str | None:
        """Resuelve el identificador de dispositivo objetivo desde datos de acción o evento.

        Args:
            action: Diccionario de acción de regla.
            event: Carga de evento entrante.

        Returns:
            El primer identificador de dispositivo no vacío encontrado, o ``None``.
        """

        action_device_id = action.get("device_id")
        if action_device_id is not None:
            value = str(action_device_id).strip()
            if value:
                return value

        action_target = action.get("target")
        if isinstance(action_target, dict):
            action_target_device_id = action_target.get("device_id")
            if action_target_device_id is not None:
                value = str(action_target_device_id).strip()
                if value:
                    return value

        event_target = event.get("target")
        if isinstance(event_target, dict):
            event_target_device_id = event_target.get("device_id")
            if event_target_device_id is not None:
                value = str(event_target_device_id).strip()
                if value:
                    return value

        event_device_id = event.get("device_id")
        if event_device_id is not None:
            value = str(event_device_id).strip()
            if value:
                return value

        return None

    def _extract_selector(self, action: dict[str, Any]) -> dict[str, Any] | None:
        """Extrae un diccionario selector desde una acción o su bloque objetivo.

        Args:
            action: Diccionario de acción de regla.

        Returns:
            Una copia superficial de la asignación selectora, o ``None`` cuando está ausente.
        """

        selector = action.get("selector")
        if isinstance(selector, dict) and selector:
            return dict(selector)

        action_target = action.get("target")
        if isinstance(action_target, dict):
            target_selector = action_target.get("selector")
            if isinstance(target_selector, dict) and target_selector:
                return dict(target_selector)

        return None

    def _infer_selector_from_event(
        self,
        device_type: str,
        event: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Deduce un selector desde datos de evento para tipos de dispositivos que lo soportan.

        Args:
            device_type: Tipo de dispositivo objetivo solicitado por la acción.
            event: Carga de evento entrante.

        Returns:
            Un diccionario selector cuando se puede deducir uno, en caso contrario ``None``.
        """

               
        # Creo que esto no es necesario
        #if device_type != "light":
        #    return None

        track_id = event.get("track_id")
        if track_id is None:
            return None

        value = str(track_id).strip()
        if not value:
            return None

        return {"idpista": value}

# endregion