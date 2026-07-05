"""Registro de dispositivos del backend edge gateway.

Este módulo descubre, registra y resuelve implementaciones de dispositivos a
partir de la configuración cargada desde YAML. También mantiene índices por tipo y 
por identificador para facilitar el enrutado de acciones y la resolución de objetivos.
"""

import logging
import importlib
import inspect
import pkgutil
from typing import Any

from app.devices.base import Device
from app.devices.generic import GenericDevice

# Activar el registro de logs
logger = logging.getLogger(__name__)


class DeviceRegistry:
    """Gestiona el registro y la resolución de dispositivos configurados."""

    def __init__(self) -> None:
        self._registry: dict[str, type[Device]] = {}
        self._devices_by_type: dict[str, list[dict[str, Any]]] = {}
        self._devices_by_id: dict[str, dict[str, Any]] = {}
        logger.debug("DeviceRegistry inicializado.")
        self.discover_from_package("app.devices")

    def register(self, device_type: str, device_cls: type[Device]) -> None:
        """Registra una clase concreta para un tipo lógico de dispositivo."""

        if not device_type:
            logger.error("Se intentó registrar un tipo de dispositivo vacío.")
            raise ValueError("El tipo de dispositivo no puede estar vacío.")
        self._registry[device_type] = device_cls
        logger.info(
            "Tipo de dispositivo '%s' registrado con la clase '%s'.",
            device_type,
            device_cls.__name__,
        )

    def discover_from_package(self, package_name: str) -> None:
        """Descubre clases de dispositivos."""

        package = importlib.import_module(package_name)
        package_paths = getattr(package, "__path__", None)
        if package_paths is None:
            logger.warning("El paquete '%s' no tiene __path__; se omite el descubrimiento de dispositivos.", package_name)
            return

        discovered = 0
        for module_info in pkgutil.iter_modules(package_paths):
            module_name = module_info.name
            if module_name in {"base", "generic", "registry"}:
                continue

            module = importlib.import_module(f"{package_name}.{module_name}")
            for _, candidate in inspect.getmembers(module, inspect.isclass):
                if candidate is Device or not issubclass(candidate, Device):
                    continue
                if candidate.__module__ != module.__name__:
                    continue

                device_type = self._infer_device_type(candidate)
                if not device_type:
                    logger.warning(
                        "Se omite la clase de dispositivo '%s' en '%s': no se pudo inferir el tipo de dispositivo.",
                        candidate.__name__,
                        module.__name__,
                    )
                    continue

                self.register(device_type, candidate)
                discovered += 1

        logger.info("Se descubrieron %d implementación(es) de dispositivo en el paquete '%s'.", discovered, package_name)

    def register_from_config(
        self,
        devices_config: dict[str, Any],
    ) -> None:
        """Carga dispositivos definidos en la configuración YAML."""

        devices = devices_config.get("devices", [])
        if not isinstance(devices, list):
            logger.error("Configuración de dispositivos inválida: la clave 'devices' no es una lista.")
            raise RuntimeError("La clave 'devices' de config/devices.yaml debe ser una lista.")

        logger.info("Cargando %d dispositivos desde la configuración.", len(devices))

        for index, device in enumerate(devices):
            if not isinstance(device, dict):
                logger.error("Entrada de dispositivo inválida en el índice %d: se esperaba un objeto.", index)
                raise RuntimeError(f"El dispositivo en el índice {index} de config/devices.yaml debe ser un objeto.")

            device_id = str(device.get("device_id", "")).strip()
            if not device_id:
                logger.error("El dispositivo en el índice %d no incluye device_id.", index)
                raise RuntimeError(f"El dispositivo en el índice {index} de config/devices.yaml debe incluir 'device_id'.")
            
            if device_id in self._devices_by_id:
                logger.error("Se encontró un device_id duplicado '%s' en el índice %d.", device_id, index)
                raise RuntimeError(f"Se encontró un device_id duplicado '{device_id}' en config/devices.yaml.")

            device_type = str(device.get("type", "")).strip()
            if not device_type:
                logger.error("El dispositivo '%s' en el índice %d no incluye type.", device_id, index)
                raise RuntimeError(f"El dispositivo en el índice {index} de config/devices.yaml debe incluir 'type'.")

            # IMPORTANTE: registrar una implementación genérica cuando todavía no
            # exista un driver específico para este tipo lógico.
            if device_type not in self._registry:
                self._registry[device_type] = GenericDevice
                logger.info(
                    "No existe una clase explícita para el tipo '%s'. Se usa GenericDevice.",
                    device_type,
                )

            stored_device = dict(device)
            self._devices_by_type.setdefault(device_type, []).append(stored_device)
            self._devices_by_id[device_id] = stored_device
            logger.debug(
                "Dispositivo configurado registrado id=%s tipo=%s nombre=%s.",
                device_id,
                device_type,
                stored_device.get("name"),
            )

        logger.info(
            "Configuración de dispositivos cargada: %d dispositivo(s), %d tipo(s).",
            len(self._devices_by_id),
            len(self._devices_by_type),
        )

    def resolve_by_device_id(
        self,
        device_id: str,
        expected_device_type: str | None = None,
    ) -> tuple[Device, dict[str, Any]]:
        """Resuelve un dispositivo configurado a partir de su identificador."""

        normalized_device_id = str(device_id).strip()
        if not normalized_device_id:
            logger.error("resolve_by_device_id se llamó con un id vacío.")
            raise RuntimeError("El id del dispositivo no puede estar vacío.")

        configured_device = self._devices_by_id.get(normalized_device_id)
        if configured_device is None:
            logger.error("El id de dispositivo '%s' no está configurado.", normalized_device_id)
            raise RuntimeError(f"El id de dispositivo '{normalized_device_id}' no está configurado.")

        configured_type = str(configured_device.get("type", "")).strip()
        if expected_device_type and configured_type != expected_device_type:
            logger.error(
                "Incompatibilidad de tipo para el id de dispositivo '%s': configurado=%s esperado=%s.",
                normalized_device_id,
                configured_type,
                expected_device_type,
            )
            raise RuntimeError(
                f"El id de dispositivo '{normalized_device_id}' es de tipo '{configured_type}', "
                f"pero se esperaba '{expected_device_type}'."
            )

        device_cls = self._registry.get(configured_type)
        if device_cls is None:
            logger.error("El tipo de dispositivo '%s' no está registrado.", configured_type)
            raise RuntimeError(f"El tipo de dispositivo '{configured_type}' no está registrado.")

        logger.debug(
            "Se resolvió el id de dispositivo '%s' al tipo '%s' y a la clase '%s'.",
            normalized_device_id,
            configured_type,
            device_cls.__name__,
        )

        return (self._instantiate(device_cls), configured_device)

    def iter_by_type(self, device_type: str) -> list[tuple[Device, dict[str, Any]]]:
        """Itera sobre los dispositivos configurados de un tipo concreto."""

        device_cls = self._registry.get(device_type)
        if device_cls is None:
            raise RuntimeError(f"El tipo de dispositivo '{device_type}' no está registrado.")

        configured_devices = self._devices_by_type.get(device_type, [])
        if not configured_devices:
            return [(self._instantiate(device_cls), {})]

        return [
            (self._instantiate(device_cls), cfg)
            for cfg in configured_devices
        ]

    def resolve_target(
        self,
        device_type: str,
        selector: dict[str, Any] | None = None,
    ) -> tuple[Device, dict[str, Any]]:
        """Resuelve un único objetivo para un tipo de dispositivo."""

        device_cls = self._registry.get(device_type)
        if device_cls is None:
            raise RuntimeError(f"El tipo de dispositivo '{device_type}' no está registrado.")

        configured_devices = self._devices_by_type.get(device_type, [])
        if not configured_devices:
            return (self._instantiate(device_cls), {})

        if selector:
            matches = [
                cfg
                for cfg in configured_devices
                if self._matches_selector(cfg, selector)
            ]
            if not matches:
                raise RuntimeError(
                    f"Ningún dispositivo configurado de tipo '{device_type}' coincide con el selector {selector}."
                )
            if len(matches) > 1:
                raise RuntimeError(
                    f"El selector {selector} es ambiguo para el tipo de dispositivo '{device_type}'."
                )
            return (self._instantiate(device_cls), matches[0])

        if len(configured_devices) == 1:
            return (self._instantiate(device_cls), configured_devices[0])

        raise RuntimeError(
            f"La acción para el tipo de dispositivo '{device_type}' es ambigua: "
            "hay varios dispositivos configurados y no se proporcionó un selector."
        )

    def resolve_many(
        self,
        device_type: str,
        selector: dict[str, Any] | None = None,
    ) -> list[tuple[Device, dict[str, Any]]]:
        """Resuelve todos los dispositivos que coinciden con un tipo y selector."""

        device_cls = self._registry.get(device_type)
        if device_cls is None:
            raise RuntimeError(f"El tipo de dispositivo '{device_type}' no está registrado.")

        configured_devices = self._devices_by_type.get(device_type, [])
        if not configured_devices:
            return [(self._instantiate(device_cls), {})]

        if selector:
            matches = [
                cfg
                for cfg in configured_devices
                if self._matches_selector(cfg, selector)
            ]
            if not matches:
                raise RuntimeError(
                    f"Ningún dispositivo configurado de tipo '{device_type}' coincide con el selector {selector}."
                )
            return [
                (self._instantiate(device_cls), cfg)
                for cfg in matches
            ]

        if len(configured_devices) == 1:
            return [(self._instantiate(device_cls), configured_devices[0])]

        raise RuntimeError(
            f"La acción para el tipo de dispositivo '{device_type}' es ambigua: "
            "hay varios dispositivos configurados y no se proporcionó un selector."
        )

    def _matches_selector(self, config: dict[str, Any], selector: dict[str, Any]) -> bool:
        """Comprueba si una configuración cumple un selector parcial."""

        for key, expected_value in selector.items():
            if key not in config:
                return False
            if str(config[key]).strip() != str(expected_value).strip():
                return False
        return True

    def create(self, device_type: str, **kwargs: Any) -> Device:
        """Crea una instancia nueva de una clase de dispositivo registrada."""

        device_cls = self._registry.get(device_type)
        if device_cls is None:
            logger.error("El tipo de dispositivo '%s' no está registrado.", device_type)
            raise RuntimeError(f"El tipo de dispositivo '{device_type}' no está registrado.")
        logger.debug("Creando dispositivo para el tipo '%s'.", device_type)
        return device_cls(**kwargs)

    def _instantiate(self, device_cls: type[Device]) -> Device:
        """Instancia una clase de dispositivo sin argumentos."""

        return device_cls()

    def _infer_device_type(self, device_cls: type[Device]) -> str:
        """Infiere el tipo lógico de un dispositivo a partir de la clase."""

        explicit_type = getattr(device_cls, "DEVICE_TYPE", None)
        if isinstance(explicit_type, str) and explicit_type.strip():
            return explicit_type.strip()

        try:
            instance = device_cls()
        except TypeError:
            return ""

        return str(instance.device_type).strip()
