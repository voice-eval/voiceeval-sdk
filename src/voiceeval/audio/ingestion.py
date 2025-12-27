class AudioIngestor:
    """
    Handles ingestion of raw audio bytes or streams.
    """
    def __init__(self, source: str):
        self.source = source

    def read(self) -> bytes:
        raise NotImplementedError
