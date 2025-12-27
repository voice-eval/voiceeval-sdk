from typing import List
from voiceeval.models import Call
from voiceeval.metrics import BaseMetric

class OfflineRunner:
    """
    Runs metrics on past call logs.
    """
    def __init__(self, metrics: List[BaseMetric]):
        self.metrics = metrics

    def run(self, call: Call) -> dict:
        results = {}
        for metric in self.metrics:
            results[metric.name] = metric.evaluate(call)
        return results
