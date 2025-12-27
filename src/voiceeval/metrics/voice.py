from voiceeval.metrics.base import BaseMetric
from voiceeval.models import Call

class InterruptionRateMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "interruption_rate"

    def evaluate(self, call: Call) -> float:
        return 0.0

class SilenceDurationMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "silence_duration"

    def evaluate(self, call: Call) -> float:
        return 0.0
