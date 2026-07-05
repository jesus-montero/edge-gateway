"""Utilidades de configuración del logging para el backend de edge gateway.

Este módulo centraliza la inicialización del logging de la aplicación. Construye
el nivel efectivo de logging y el formato de mensaje a partir de valores de
configuración opcionales y los aplica mediante el sistema estándar de logging de Python.

Responsabilidades:
    - Leer el nivel de logging y el formato desde la configuración de arranque.
    - Proporcionar valores seguros por defecto cuando falten datos.
    - Inicializar la configuración global de logging para el proceso.

Comportamiento por defecto:
    - El nivel por defecto es ``INFO``.
    - El formato por defecto es ``%(asctime)s | %(levelname)s | %(name)s | %(message)s``.

Autor:
    Jesus Montero

Fecha:
    2026

Ejemplo:
    >>> from app.core.logging_config import configure_logging
    >>> configure_logging({"level": "DEBUG"})

"""

# Importaciones de la biblioteca estándar
import logging
from typing import Any


TRACE_LEVEL = 5

ALLOWED_LOG_LEVELS = ("TRACE", "DEBUG", "INFO", "WARNING", "ERROR")

LOG_LEVELS = {
    "TRACE": TRACE_LEVEL,
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
}


def trace(self: logging.Logger, message: str, *args: Any, **kwargs: Any) -> None:
    """Registra un mensaje con severidad ``TRACE``.

    TRACE es más detallado que DEBUG y está pensado para mensajes de diagnóstico
    muy granulares.
    """

    if self.isEnabledFor(TRACE_LEVEL):
        self._log(TRACE_LEVEL, message, args, **kwargs)


# Registrar TRACE en cuanto se importe este módulo.
logging.addLevelName(TRACE_LEVEL, "TRACE")
setattr(logging, "TRACE", TRACE_LEVEL)
setattr(logging.Logger, "trace", trace)

def configure_logging(config: dict[str, Any] | None = None) -> None:
    """Configura el logging de toda la aplicación a partir de un mapa opcional.

    Args:
        config: Diccionario opcional con opciones de logging.
            Las claves soportadas son ``level`` y ``format``.

    Notes:
        - Los niveles de logging desconocidos caen en ``INFO``.
        - Esta función delega la configuración en ``logging.basicConfig``.
    """

    logging.addLevelName(TRACE_LEVEL, "TRACE")
    logging.Logger.trace = trace  # type: ignore[attr-defined]

    config = config or {}

    level = str(config.get("level", "INFO")).upper()
    if level not in ALLOWED_LOG_LEVELS:
        level = "INFO"

    log_format = str(
        config.get(
            "format",
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        )
    )

    logging.basicConfig(
        level=LOG_LEVELS[level],
        format=log_format,
    )