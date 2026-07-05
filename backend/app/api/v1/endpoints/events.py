from typing import Any

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["events"])


@router.post("/events")
def process_event(event: dict[str, Any], request: Request) -> dict[str, Any]:
    rule_engine = request.app.state.rule_engine
    dispatcher = request.app.state.event_dispatcher
    try:
        commands = rule_engine.evaluate(event)
        return dispatcher.dispatch(commands, event)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
