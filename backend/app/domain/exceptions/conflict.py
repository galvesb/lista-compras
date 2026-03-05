class ConflictError(Exception):
    """Raised when an optimistic lock version conflict occurs."""

    def __init__(self, resource: str, current_version: int) -> None:
        self.resource = resource
        self.current_version = current_version
        super().__init__(
            f"Conflict on {resource}: resource was modified. Current version: {current_version}"
        )


class DuplicateError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
