class ServiceError(Exception):
    """A client-facing failure raised by the service layer; mapped to an HTTP response in main.py."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
