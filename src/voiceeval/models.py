from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class Span(BaseModel):
    """
    Represents a unit of work or time duration in a call (e.g., thinking, speaking).
    """
    span_id: str
    trace_id: str
    name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)

class TranscriptSegment(BaseModel):
    """
    A single segment of a transcript, usually representing a turn or a sentence.
    """
    speaker: str
    text: str
    timestamp: float
    confidence: Optional[float] = None

class Transcript(BaseModel):
    """
    Full transcript of a conversation.
    """
    segments: List[TranscriptSegment] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Call(BaseModel):
    """
    Represents a voice call session.
    """
    call_id: str
    agent_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    transcript: Optional[Transcript] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
