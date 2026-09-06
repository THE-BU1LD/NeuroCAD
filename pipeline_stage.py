# pipeline_stage.py

from abc import ABC, abstractmethod
from typing import Any


class PipelineStage(ABC):
    @abstractmethod
    def run(self, data: Any) -> Any:
        raise TypeError("PipelineStage.run must be implemented by a concrete stage")
