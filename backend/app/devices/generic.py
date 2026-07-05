from typing import Any

from app.devices.base import Device


class GenericDevice(Device):
    DEVICE_TYPE = "Generic"

    def __init__(self, device_type: str | None = None) -> None:
        self._device_type = device_type or self.DEVICE_TYPE

    @property
    def device_type(self) -> str:
        return self._device_type

    def getStatus(self, event: dict[str, Any]) -> dict[str, Any]:
        target_device = event.get("target_device", {})
        return {
            "device": self.device_type,
            "target": target_device,
            "command": "getStatus",
            "status": "ok",
            "online": True,
            "response": {
                "mode": "simulated",
                "event": event,
            },
        }

    def execute(self, command: str, event: dict[str, Any]) -> dict[str, Any]:
        normalized_command = command.strip().lower()
        if normalized_command in {"getstatus"}:
            return self.getStatus(event)

        target_device = event.get("target_device", {})
        return {
            "device": self.device_type,
            "target": target_device,
            "command": command,
            "status": "simulated",
            "event": event,
        }
