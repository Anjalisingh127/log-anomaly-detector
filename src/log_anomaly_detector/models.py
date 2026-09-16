"""Shared data models for synthetic application events."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LogEvent:
    """A single structured application event rendered as a key-value log line."""

    timestamp: str
    level: str
    service: str
    environment: str
    host: str
    request_id: str
    client_id: str
    method: str
    endpoint: str
    status_code: int
    response_time_ms: int
    error_type: str
    message: str

    def to_log_line(self) -> str:
        message = self.message.replace('"', "'")
        return (
            f"{self.timestamp} level={self.level} service={self.service} "
            f"environment={self.environment} host={self.host} "
            f"request_id={self.request_id} client_id={self.client_id} "
            f"method={self.method} endpoint={self.endpoint} "
            f"status_code={self.status_code} response_time_ms={self.response_time_ms} "
            f"error_type={self.error_type} message=\"{message}\""
        )
