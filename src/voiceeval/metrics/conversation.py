from voiceeval.metrics.base import BaseMetric
from voiceeval.models import Call

class SentimentMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "sentiment"

    def evaluate(self, call: Call) -> float:
        # Placeholder logic
        return 0.0

class TopicAdherenceMetric(BaseMetric):
    @property
    def name(self) -> str:
        return "topic_adherence"

    def evaluate(self, call: Call) -> float:
        return 0.0
