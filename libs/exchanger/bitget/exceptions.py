class BitgetClientException(Exception):
    """Base exception for all Bitget client-related errors."""

    pass


class InvalidProxy(BitgetClientException):
    """Raised when the provided proxy configuration is invalid or unreachable."""

    pass


class APIException(BitgetClientException):
    """
    Raised when the Bitget API returns an unsuccessful response.

    Attributes:
        response (Optional[dict]): Parsed JSON response from the Bitget API.
        status_code (Optional[int]): HTTP status code returned by the API.
        code (Optional[str]): Bitget-specific error code, if available.
        msg (Optional[str]): Bitget-specific error message, if available.

    Args:
        response (Optional[dict]): Parsed JSON response (default: None).
        status_code (Optional[int]): HTTP status code (default: None).
    """

    response: dict | None
    status_code: int | None
    code: str | None
    msg: str | None

    def __init__(self, response: dict | None = None, status_code: int | None = None) -> None:
        """Initialize APIException with optional API response and status code."""
        self.response = response
        self.status_code = status_code
        self.code = None
        self.msg = None
        if self.response and "code" in self.response and "msg" in self.response:
            self.code = self.response.get("code")
            self.msg = self.response.get("msg")

    def __str__(self) -> str:
        """Return a formatted string representation of the error, including code and message."""
        if self.code:
            return f"Bitget API Error {self.code}: {self.msg}"
        if self.msg:
            if self.status_code is not None:
                return f"HTTP {self.status_code} Error: {self.msg}"
            return f"HTTP Error: {self.msg}"
        return f"HTTP {self.status_code} Error"
