"""Definición de la configuración de ejecución para el backend de edge gateway.

Este módulo centraliza la configuración basada en el entorno mediante un modelo
tipado de ajustes de Pydantic. Define los valores mínimos de secreto y credenciales
requeridos por el backend y configura cómo se cargan desde las variables de entorno
y el archivo local ``.env``.

Responsabilidades:
    - Definir ajustes de ejecución fuertemente tipados usados en toda la aplicación.
    - Cargar la configuración desde variables de entorno y ``.env``.
    - Ignorar variables de entorno desconocidas para mantener un arranque tolerante.

Fuente de configuración:
    - Variables de entorno disponibles en el proceso.
    - Un archivo ``.env`` ubicado en la raíz del proyecto.

Autor:
    Jesus Montero

Fecha:
    2026

Ejemplo:
    >>> from app.core.settings import Settings
    >>> settings = Settings()
    >>> settings.admin_username

"""

# Importaciones de la biblioteca estándar
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Ajustes de ejecución de la aplicación cargados desde variables de entorno.

    Attributes:
        secret_key: Secreto criptográfico usado por funciones relacionadas con seguridad.
        sportgo_api_token: Token opcional de arranque para peticiones de integración con SportGo.
        admin_username: Nombre de usuario administrador por defecto.
        admin_password: Contraseña de administrador por defecto.
    """

    secret_key: str
    sportgo_api_token: str | None = None
    admin_username: str
    admin_password: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
