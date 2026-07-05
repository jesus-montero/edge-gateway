"""Contratos abstractos para integraciones SaaS en el backend edge gateway.

Este módulo define la interfaz base que deben implementar los adaptadores de
integración SaaS externos. Estandariza la gestión del ciclo de vida de los
tokens y el envío de eventos para que el resto de la aplicación pueda trabajar
con un contrato coherente.

Responsabilidades:
    - Definir una API abstracta común para los adaptadores de integración SaaS.
    - Imponer métodos para asignación y validación de tokens.
    - Imponer una firma uniforme para el método de envío de eventos.

Notas de diseño:
    - Las integraciones concretas deben heredar de ``SaaSIntegration``.
    - ``ensure_token`` debería renovar los tokens cuando sea necesario.
    - ``send_event`` debería devolver el payload de respuesta del proveedor.

Autor:
    Jesus Montero

Fecha:
    2026

Ejemplo:
    >>> class MyIntegration(SaaSIntegration):
    ...     @property
    ...     def name(self) -> str:
    ...         return "my-provider"
    ...     def set_token(self, token: str) -> None:
    ...         self._token = token
    ...     def ensure_token(self) -> bool:
    ...         return True
    ...     def send_event(self, event: dict[str, Any]) -> dict[str, Any]:
    ...         return {"ok": True}

"""

# Importaciones de la biblioteca estándar
from abc import ABC, abstractmethod
from typing import Any


class SaaSIntegration(ABC):
    """Clase base abstracta para integraciones de proveedores SaaS.

    Las implementaciones deben proporcionar identificación del proveedor,
    gestión del ciclo de vida del token y comportamiento de envío de eventos.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Devuelve un identificador estable del proveedor usado para enrutado y registro."""
        raise NotImplementedError

    @abstractmethod
    def set_token(self, token: str) -> None:
        """Establece el token de acceso del proveedor usado para peticiones autenticadas.

        Args:
            token: Token de acceso obtenido del flujo de autenticación del proveedor.
        """
        raise NotImplementedError

    @abstractmethod
    def ensure_token(self) -> bool:
        """Valida el estado del token. Lo renueva en el proveedor SaaS si ha caducado o falta.

        Returns:
            ``True`` si se produjo una renovación del token; en caso contrario, ``False``.
        """
        raise NotImplementedError

    @abstractmethod
    def send_event(self, event: dict[str, Any]) -> dict[str, Any]:
        """Envía un payload de evento al proveedor SaaS externo.

        Args:
            event: Payload del evento que se entregará al proveedor.

        Returns:
            Payload de respuesta del proveedor como diccionario.
        """
        raise NotImplementedError
