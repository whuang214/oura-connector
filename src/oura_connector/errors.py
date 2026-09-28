"""Sanitized errors shared by both interfaces."""


class ConnectorError(Exception):
    """Only safe, non-secret messages may be used here."""


class ConfigurationError(ConnectorError):
    pass


class AuthenticationError(ConnectorError):
    pass


class TokenStoreError(ConnectorError):
    pass


class ApiError(ConnectorError):
    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LimitError(ConnectorError):
    pass
