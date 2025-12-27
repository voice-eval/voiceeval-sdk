from voiceeval.metrics.base import BaseMetric
from voiceeval.models import Call

class TimeToFirstByteMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "ttfb"

    def evaluate(self, call: Call) -> float:
        return 0.0

class EndToEndLatencyMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "e2e_latency"

    def evaluate(self, call: Call) -> float:
        return 0.0
