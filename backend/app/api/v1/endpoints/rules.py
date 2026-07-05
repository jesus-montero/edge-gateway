"""Endpoints para la gestión de la configuración de reglas.

Este módulo proporciona endpoints REST para gestionar las reglas del sistema
interactuando con la capa de repositorio rules_config. Permite al frontend
consultar, crear, actualizar y eliminar definiciones de reglas almacenadas en
config/rules.yaml.

Endpoints:
	GET /rules - Lista todas las reglas
	GET /rules/{rule_name} - Obtiene una regla concreta
	POST /rules - Crea una nueva regla
	PUT /rules/{rule_name} - Actualiza una regla existente
	DELETE /rules/{rule_name} - Elimina una regla

Autor:
	Jesus Montero

Fecha:
	2026
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request

from app.core.config_loader import load_startup_configs
from app.repositories import rules_config
from app.services.rule_engine import RuleEngine


router = APIRouter(tags=["rules"])


def _reload_rules_state(request: Request) -> None:
	"""Recarga la configuración de reglas en memoria y el motor de reglas tras una escritura."""

	request.app.state.configs["rules"] = load_startup_configs()["rules"]
	request.app.state.rule_engine = RuleEngine(request.app.state.configs["rules"])


@router.get("/rules")
def list_rules() -> dict[str, Any]:
	"""Recupera todas las reglas configuradas."""

	try:
		rules = rules_config.get_all_rules()
		return {
			"status": "success",
			"count": len(rules),
			"rules": rules,
		}
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"No se pudieron recuperar las reglas: {str(exc)}") from exc


@router.get("/rules/{rule_name}")
def get_rule(rule_name: str) -> dict[str, Any]:
	"""Recupera una regla concreta por nombre."""

	try:
		rule = rules_config.get_rule(rule_name)
		if rule is None:
			raise HTTPException(status_code=404, detail=f"No se encontró la regla '{rule_name}'")

		return {
			"status": "success",
			"rule": rule,
		}
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"No se pudo recuperar la regla: {str(exc)}") from exc


@router.post("/rules")
def create_rule(rule: dict[str, Any], request: Request) -> dict[str, Any]:
	"""Crea una nueva configuración de regla."""

	try:
		if "name" not in rule:
			raise HTTPException(status_code=400, detail="La regla debe incluir un campo 'name'")

		success = rules_config.insert_rule(rule)
		if not success:
			raise HTTPException(
				status_code=400,
				detail=f"No se pudo crear la regla (posible nombre duplicado: {rule.get('name')})",
			)

		_reload_rules_state(request)
		return {
			"status": "success",
			"message": f"Regla '{rule.get('name')}' creada correctamente",
			"rule": rule,
		}
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"No se pudo crear la regla: {str(exc)}") from exc


@router.put("/rules/{rule_name}")
def update_rule(rule_name: str, updated_data: dict[str, Any], request: Request) -> dict[str, Any]:
	"""Actualiza una configuración de regla existente."""

	try:
		if not rules_config.rule_exists(rule_name):
			raise HTTPException(status_code=404, detail=f"No se encontró la regla '{rule_name}'")

		success = rules_config.update_rule(rule_name, updated_data)
		if not success:
			raise HTTPException(status_code=400, detail=f"No se pudo actualizar la regla '{rule_name}'")

		_reload_rules_state(request)
		return {
			"status": "success",
			"message": f"Regla '{rule_name}' actualizada correctamente",
			"rule": rules_config.get_rule(rule_name),
		}
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"No se pudo actualizar la regla: {str(exc)}") from exc


@router.delete("/rules/{rule_name}")
def delete_rule(rule_name: str, request: Request) -> dict[str, Any]:
	"""Elimina una configuración de regla por nombre."""

	try:
		if not rules_config.rule_exists(rule_name):
			raise HTTPException(status_code=404, detail=f"No se encontró la regla '{rule_name}'")

		success = rules_config.delete_rule(rule_name)
		if not success:
			raise HTTPException(status_code=400, detail=f"No se pudo eliminar la regla '{rule_name}'")

		_reload_rules_state(request)
		return {
			"status": "success",
			"message": f"Regla '{rule_name}' eliminada correctamente",
		}
	except HTTPException:
		raise
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"No se pudo eliminar la regla: {str(exc)}") from exc
