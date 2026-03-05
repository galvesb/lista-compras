class ForbiddenError(Exception):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message)
