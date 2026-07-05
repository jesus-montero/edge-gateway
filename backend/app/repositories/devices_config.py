"""Ayudantes de repositorio para gestionar la configuración YAML de dispositivos.

Este módulo proporciona utilidades CRUD basadas en archivos sobre
``config/devices.yaml``. Se encarga de localizar el archivo de configuración,
cargar las definiciones de dispositivos, persistir los cambios y exponer
funciones auxiliares usadas por la capa de API/servicios.

Responsabilidades:
    - Resolver la ruta de ``devices.yaml`` a partir de la estructura del proyecto.
    - Crear un archivo de configuración inicial cuando sea necesario.
    - Cargar y guardar listas de dispositivos en almacenamiento YAML.
    - Proporcionar operaciones de inserción, borrado, consulta y comprobación de existencia.
    - Calcular el siguiente ``device_id`` disponible.

Formato de almacenamiento:
    - Mapa raíz con una clave ``devices``.
    - ``devices`` contiene una lista de diccionarios.

Autor:
    Jesus Montero

Fecha:
    2026

Ejemplo:
    >>> devices = load_devices()
    >>> exists = device_exists(1)

"""

# Importaciones de la biblioteca estándar
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

# Importaciones de terceros
import yaml


def get_devices_config_path() -> Path:
    """Devuelve la ruta absoluta de ``config/devices.yaml``.

    Returns:
        Ruta absoluta del archivo de configuración de dispositivos.
    """

    current_dir = Path(__file__).resolve().parent  # directorio repositories
    project_root = current_dir.parent.parent.parent  # raíz edge-gateway
    config_path = project_root / "config" / "devices.yaml"
    return config_path


def create_initial_devices_yaml() -> bool:
    """Crea un archivo inicial ``devices.yaml`` con una lista de dispositivos vacía.

    Returns:
        ``True`` si la creación del archivo fue exitosa, ``False`` si el archivo ya existe
        o si ocurrió un error.
    """

    config_path = get_devices_config_path()
    
    if config_path.exists():
        return False
    
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    initial_config = {
        'devices': []
    }
    
    try:
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(initial_config, file, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"Error al crear el archivo devices.yaml: {e}")
        return False


def load_devices() -> List[Dict[str, Any]]:
    """Carga entradas de dispositivos desde ``devices.yaml``.

    Returns:
        Lista de dispositivos del archivo YAML. Devuelve una lista vacía cuando el archivo
        falta o cuando ocurre un error.
    """

    config_path = get_devices_config_path()
    
    if not config_path.exists():
        print(f"Archivo no encontrado: {config_path}")
        return []
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
            return config.get('devices', []) if config else []
    except yaml.YAMLError as e:
        print(f"Error al analizar el archivo YAML: {e}")
        return []
    except Exception as e:
        print(f"Error al leer el archivo devices.yaml: {e}")
        return []


def _save_devices(devices: List[Dict[str, Any]]) -> bool:
    """Persiste la lista completa de dispositivos en ``devices.yaml``.

    Args:
        devices: Lista completa de diccionarios de dispositivos a guardar.

    Returns:
        ``True`` cuando el guardado es exitoso, en caso contrario ``False``.
    """

    config_path = get_devices_config_path()
    
    try:
        sorted_devices = sorted(devices, key=_device_sort_key)
        config = {'devices': sorted_devices}
        with open(config_path, 'w', encoding='utf-8') as file:
            yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        print(f"Error al guardar el archivo devices.yaml: {e}")
        return False


def _device_sort_key(device: Dict[str, Any]) -> tuple[int, Any]:
    """Construye una clave de ordenamiento estable para dispositivos ordenados por ``device_id``.

    Los IDs numéricos se ordenan primero por su valor entero. Los IDs no numéricos o
    ausentes se colocan después de los IDs numéricos manteniendo un orden determinista.
    """

    device_id = device.get('device_id')
    if device_id is None:
        return (1, "")

    try:
        return (0, int(device_id))
    except (TypeError, ValueError):
        return (1, str(device_id))


def insert_device(device: Dict[str, Any]) -> bool:
    """Inserta una nueva entrada de configuración de dispositivo.

    La inserción se rechaza si falta ``device_id`` o ya existe.

    Args:
        device: Diccionario de configuración del dispositivo.

    Returns:
        ``True`` cuando la inserción es correcta, en caso contrario ``False``.
    """

    if 'device_id' not in device:
        print("Error: el dispositivo debe incluir un 'device_id'")
        return False
    
    devices = load_devices()
    
    # Asegurar que no exista ya un dispositivo con el mismo device_id.
    device_id = device['device_id']
    if any(d['device_id'] == device_id for d in devices):
        print(f"Error: ya existe un dispositivo con device_id = {device_id}")
        return False
    
    # Añadir el nuevo dispositivo.
    devices.append(device)
    
    # Persistir los cambios.
    return _save_devices(devices)


def update_device(device_id: int, updated_data: Dict[str, Any]) -> bool:
    """Actualiza una entrada existente de configuración de dispositivo.

    La actualización se rechaza si el dispositivo no existe. El campo ``device_id``
    no puede ser modificado.

    Args:
        device_id: Identificador del dispositivo a actualizar.
        updated_data: Diccionario con los campos a actualizar.

    Returns:
        ``True`` cuando la actualización es exitosa, en caso contrario ``False``.
    """

    devices = load_devices()
    
    # Buscar el dispositivo a actualizar.
    device_found = False
    for i, device in enumerate(devices):
        if device['device_id'] == device_id:
            device_found = True
            # Evitar la modificación de device_id
            updated_data_copy = updated_data.copy()
            updated_data_copy.pop('device_id', None)
            # Fusionar los datos actualizados en el dispositivo existente
            device.update(updated_data_copy)
            devices[i] = device
            break
    
    if not device_found:
        print(f"Error: no se encontró ningún dispositivo con device_id = {device_id}")
        return False
    
    # Persistir los cambios.
    return _save_devices(devices)


def delete_device(device_id: int) -> bool:
    """Elimina una entrada de dispositivo por ``device_id``.

    Args:
        device_id: Identificador del dispositivo a eliminar.

    Returns:
        ``True`` si un dispositivo fue eliminado y persistido, en caso contrario ``False``.
    """

    devices = load_devices()
    
    # Eliminar el dispositivo objetivo de la lista.
    initial_count = len(devices)
    devices = [d for d in devices if d['device_id'] != device_id]
    
    # Comprobar si se eliminó algún elemento.
    if len(devices) == initial_count:
        print(f"Error: no se encontró ningún dispositivo con device_id = {device_id}")
        return False
    
    # Persistir los cambios.
    return _save_devices(devices)


def get_device(device_id: int) -> Optional[Dict[str, Any]]:
    """Devuelve una configuración de dispositivo por ``device_id``.

    Args:
        device_id: Identificador del dispositivo a buscar.

    Returns:
        Diccionario del dispositivo si se encuentra, en caso contrario ``None``.
    """

    devices = load_devices()
    
    for device in devices:
        if device['device_id'] == device_id:
            return device
    
    return None


def get_all_devices() -> List[Dict[str, Any]]:
    """Devuelve todos los dispositivos configurados.

    Returns:
        Lista de todos los diccionarios de dispositivos.
    """

    return load_devices()


def device_exists(device_id: int) -> bool:
    """Comprueba si existe un dispositivo por ``device_id``.

    Args:
        device_id: Identificador a verificar.

    Returns:
        ``True`` si existe un dispositivo coincidente, en caso contrario ``False``.
    """

    return get_device(device_id) is not None


def get_next_available_device_id() -> int:
    """Calcula el siguiente ``device_id`` numérico disponible.

    Returns:
        ``max(device_id) + 1`` cuando existen dispositivos, en caso contrario ``1``.
    """

    devices = load_devices()
    
    if not devices:
        return 1
    
    # Calcular el máximo device_id actual e incrementarlo en uno.
    max_id = max(d['device_id'] for d in devices)
    return max_id + 1
