from abc import ABC, abstractmethod
from typing import Any, Dict
from voiceeval.models import Call

class BaseMetric(ABC):
    """
    Abstract base class for all metrics.
    """
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def evaluate(self, call: Call) -> float:
        """
        Evaluate the metric for a given call.
        Should return a numerical score or value.
        """
        pass
