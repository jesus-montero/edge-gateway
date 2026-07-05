"""Ayudantes de repositorio para gestionar la configuración YAML de reglas.

Este módulo proporciona utilidades CRUD basadas en archivos sobre ``config/rules.yaml``.
Almacena definiciones de reglas como una lista ordenada para que se preserve
la precedencia de evaluación definida por el archivo YAML.

Responsabilidades:
    - Resolver la ruta de ``rules.yaml`` a partir de la estructura del proyecto.
    - Cargar y guardar definiciones de reglas en almacenamiento YAML.
    - Proporcionar operaciones de inserción, actualización, eliminación, consulta y verificación de existencia.

Formato de almacenamiento:
    - Mapa raíz con una clave ``rules``.
    - ``rules`` contiene una lista de diccionarios de reglas.

Autor:
    Jesus Montero

Fecha:
    2026
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def get_rules_config_path() -> Path:
    """Devuelve la ruta absoluta de ``config/rules.yaml``."""

    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent
    return project_root / "config" / "rules.yaml"


def load_rules_config() -> dict[str, Any]:
    """Carga el archivo de configuración YAML de reglas."""

    config_path = get_rules_config_path()
    if not config_path.exists():
        return {"rules": []}

    try:
        with config_path.open("r", encoding="utf-8") as file:
            config = yaml.safe_load(file) or {}
    except yaml.YAMLError as exc:
        raise RuntimeError(f"Error al analizar el archivo rules.yaml: {exc}") from exc
    except Exception as exc:
        raise RuntimeError(f"Error al leer el archivo rules.yaml: {exc}") from exc

    if not isinstance(config, dict):
        raise RuntimeError("config/rules.yaml debe contener un mapa YAML en la raíz.")

    rules = config.get("rules", [])
    if rules is None:
        rules = []
    if not isinstance(rules, list):
        raise RuntimeError("La clave 'rules' de config/rules.yaml debe ser una lista.")

    return {"rules": rules}


def _save_rules_config(config: dict[str, Any]) -> bool:
    """Persiste la configuración completa de reglas en ``rules.yaml"."""

    config_path = get_rules_config_path()

    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with config_path.open("w", encoding="utf-8") as file:
            yaml.dump(config, file, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return True
    except Exception as exc:
        print(f"Error al guardar el archivo rules.yaml: {exc}")
        return False


def _normalize_rule_name(rule_name: str) -> str:
    """Normaliza un nombre de regla para comparaciones."""

    return str(rule_name).strip()


def _validate_rule(rule: dict[str, Any]) -> str | None:
    """Valida la estructura de regla utilizada por la API y el motor."""

    if not isinstance(rule, dict):
        return "La regla debe ser un objeto"

    name = _normalize_rule_name(rule.get("name", ""))
    if not name:
        return "La regla debe incluir un campo 'name' no vacío"

    when = rule.get("when")
    if not isinstance(when, dict):
        return f"La regla '{name}' debe incluir un objeto 'when'"

    source = when.get("source")
    event_type = when.get("type")
    if not source or not event_type:
        return f"La regla '{name}' debe incluir when.source y when.type"

    actions = rule.get("actions")
    if not isinstance(actions, list) or not actions:
        return f"La regla '{name}' debe incluir una lista de acciones no vacía"

    for index, action in enumerate(actions):
        if not isinstance(action, dict):
            return f"La regla '{name}' tiene una acción inválida en el índice {index}"

        device = action.get("device")
        command = action.get("command")
        if not device or not command:
            return f"La regla '{name}' tiene una acción inválida en el índice {index}"

    return None


def get_all_rules() -> list[dict[str, Any]]:
    """Devuelve todas las reglas configuradas."""

    return load_rules_config().get("rules", [])


def get_rule(rule_name: str) -> dict[str, Any] | None:
    """Devuelve una configuración de regla por nombre."""

    rule_key = _normalize_rule_name(rule_name)
    if not rule_key:
        return None

    for rule in get_all_rules():
        if isinstance(rule, dict) and _normalize_rule_name(rule.get("name", "")) == rule_key:
            return rule

    return None


def rule_exists(rule_name: str) -> bool:
    """Comprueba si existe una regla por nombre."""

    return get_rule(rule_name) is not None


def insert_rule(rule: dict[str, Any]) -> bool:
    """Inserta una nueva entrada de configuración de regla."""

    validation_error = _validate_rule(rule)
    if validation_error:
        print(f"Error: {validation_error}")
        return False

    rule_key = _normalize_rule_name(rule["name"])
    config = load_rules_config()
    rules = config.get("rules", [])

    if any(isinstance(existing_rule, dict) and _normalize_rule_name(existing_rule.get("name", "")) == rule_key for existing_rule in rules):
        print(f"Error: Ya existe una regla con nombre '{rule_key}'")
        return False

    rules.append(rule)
    config["rules"] = rules
    return _save_rules_config(config)


def update_rule(rule_name: str, updated_rule: dict[str, Any]) -> bool:
    """Actualiza una entrada existente de configuración de regla."""

    rule_key = _normalize_rule_name(rule_name)
    if not rule_key:
        print("Error: El nombre de la regla no puede estar vacío")
        return False

    validation_error = _validate_rule({**updated_rule, "name": rule_key})
    if validation_error:
        print(f"Error: {validation_error}")
        return False

    config = load_rules_config()
    rules = config.get("rules", [])

    for index, existing_rule in enumerate(rules):
        if isinstance(existing_rule, dict) and _normalize_rule_name(existing_rule.get("name", "")) == rule_key:
            rule_to_save = dict(updated_rule)
            rule_to_save["name"] = rule_key
            rules[index] = rule_to_save
            config["rules"] = rules
            return _save_rules_config(config)

    print(f"Error: No rule found with name '{rule_key}'")
    return False


def delete_rule(rule_name: str) -> bool:
    """Elimina una entrada de regla por nombre."""

    rule_key = _normalize_rule_name(rule_name)
    if not rule_key:
        print("Error: El nombre de la regla no puede estar vacío")
        return False

    config = load_rules_config()
    rules = config.get("rules", [])

    filtered_rules = [
        rule for rule in rules
        if not (isinstance(rule, dict) and _normalize_rule_name(rule.get("name", "")) == rule_key)
    ]

    if len(filtered_rules) == len(rules):
        print(f"Error: No se encontró ninguna regla con nombre '{rule_key}'")
        return False

    config["rules"] = filtered_rules
    return _save_rules_config(config)