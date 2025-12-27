from typing import List, Tuple

class VAD:
    """
    Voice Activity Detection utilities.
    """
    def detect_speech(self, audio: bytes) -> List[Tuple[float, float]]:
        """
        Returns list of (start_time, end_time) tuples where speech is detected.
        """
        return []
