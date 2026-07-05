"""Utilidades de carga de configuración para el backend de edge gateway.

Este módulo proporciona la lógica centralizada para cargar, validar y exponer
la configuración en tiempo de ejecución requerida al arrancar la aplicación.
Combina la configuración tipada del entorno con archivos YAML ubicados en el
directorio ``config/`` del proyecto.

Responsabilidades:
    - Resolver las rutas del proyecto y de configuración.
    - Cargar archivos YAML de forma segura y validar su estructura.
    - Exigir las claves requeridas para cada archivo de configuración de arranque.
    - Exponer accesores para la configuración YAML de arranque y las variables de entorno.

Archivos de configuración:
    - ``config/app.yaml``
    - ``config/saas.yaml``
    - ``config/devices.yaml``
    - ``config/rules.yaml``
    - ``config/logging.yaml``

Gestión de errores:
    - Lanza ``RuntimeError`` cuando faltan archivos requeridos.
    - Lanza ``RuntimeError`` cuando la sintaxis YAML es inválida.
    - Lanza ``RuntimeError`` cuando faltan claves requeridas.

Recarga dinámica:
        - ``load_startup_configs`` y ``get_settings`` construyen objetos nuevos en cada
            llamada para que los cambios de configuración se reflejen en tiempo de ejecución.

Autor:
    Jesus Montero

Fecha:
    2026

Ejemplo:
    >>> from app.core.config_loader import load_startup_configs, get_settings
    >>> configs = load_startup_configs()
    >>> settings = get_settings()

"""

# Importaciones de la biblioteca estándar
from pathlib import Path
from typing import Any
import yaml

# Importaciones locales de la aplicación
from app.core.settings import Settings



PROJECT_ROOT = Path(__file__).resolve().parents[3]
CONFIG_DIR = PROJECT_ROOT / "config"

REQUIRED_YAML_FILES = {
    "app.yaml": ["app_name", "environment"],
    "saas.yaml": ["providers"],
    "devices.yaml": ["devices"],
    "rules.yaml": ["rules"],
    "logging.yaml": ["level", "format"],
}


def _require_key(config: dict[str, Any], key: str, filename: str) -> None:
    """Asegura que exista una clave superior requerida en un mapa YAML cargado.

    Args:
        config: Contenido YAML analizado como diccionario.
        key: Nombre de la clave requerida.
        filename: Nombre del archivo YAML origen usado para informar errores.

    Raises:
        RuntimeError: Si falta la clave requerida en ``config``.
    """

    if key not in config:
        raise RuntimeError(
            f"Falta la clave requerida '{key}' en config/{filename}."
        )


def load_yaml_config(filename: str) -> dict[str, Any]:
    """Carga y valida un archivo de configuración YAML desde ``config/``.

    Args:
        filename: Nombre del archivo YAML relativo al directorio ``config/``.

    Returns:
        Contenido YAML analizado como diccionario.

    Raises:
        RuntimeError: Si falta el archivo, tiene sintaxis YAML inválida o no
            contiene un mapa YAML en la raíz.
    """

    file_path = CONFIG_DIR / filename
    if not file_path.exists():
        raise RuntimeError(
            f"Falta el archivo de configuración: config/{filename}."
        )

    try:
        with file_path.open("r", encoding="utf-8") as config_file:
            data = yaml.safe_load(config_file) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Sintaxis YAML inválida en config/{filename}: {exc}") from exc

    if not isinstance(data, dict):
        raise RuntimeError(
            f"La configuración en config/{filename} debe ser un mapa YAML."
        )

    return data


def load_startup_configs() -> dict[str, dict[str, Any]]:
    """Carga y valida todas las configuraciones YAML de arranque requeridas.

    Returns:
        Diccionario indexado por nombres lógicos de sección: ``app``, ``saas``,
        ``devices``, ``rules`` y ``logging``.

    Raises:
        RuntimeError: Si falta algún archivo o clave requerida, o si algún
            archivo contiene contenido YAML inválido.
    """

    loaded: dict[str, dict[str, Any]] = {}

    for filename, required_keys in REQUIRED_YAML_FILES.items():
        config = load_yaml_config(filename)
        for required_key in required_keys:
            _require_key(config, required_key, filename)
        loaded[filename] = config

    return {
        "app": loaded["app.yaml"],
        "saas": loaded["saas.yaml"],
        "devices": loaded["devices.yaml"],
        "rules": loaded["rules.yaml"],
        "logging": loaded["logging.yaml"],
    }


def get_settings() -> Settings:
    """Crea el objeto de configuración de entorno de la aplicación.

    Returns:
        Una instancia de ``Settings`` validada y cargada desde variables de entorno y
        el archivo local ``.env``.
    """

    return Settings()  # pyright: ignore[reportCallIssue]
