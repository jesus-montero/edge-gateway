from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request) -> dict[str, str]:
    app_config = request.app.state.configs["app"]
    return {
        "status": "ok",
        "app_name": str(app_config["app_name"]),
        "environment": str(app_config["environment"]),
    }
