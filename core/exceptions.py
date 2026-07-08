class IngestionError(Exception):
    """Base error for content ingestion failures (invalid link, empty content, etc.)."""


class InvalidLinkError(IngestionError):
    pass


class TranscriptUnavailableError(IngestionError):
    pass


class ScrapeError(IngestionError):
    pass


class EmptyContentError(IngestionError):
    pass


class VectorStoreError(Exception):
    pass


class LLMError(Exception):
    pass
