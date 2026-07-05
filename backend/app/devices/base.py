from abc import ABC, abstractmethod
from typing import Any


class Device(ABC):
    @property
    @abstractmethod
    def device_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def getStatus(self, event: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def execute(self, command: str, event: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError
