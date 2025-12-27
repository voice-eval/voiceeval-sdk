from typing import List
from voiceeval.models import TranscriptSegment

class Transcriber:
    """
    Base class for transcription services.
    """
    def transcribe(self, audio: bytes) -> List[TranscriptSegment]:
        raise NotImplementedError
