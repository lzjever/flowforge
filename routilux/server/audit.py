"""
Audit logging for HTTP server.

Provides structured logging of security-relevant events.
"""

import hashlib
import json
import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, TextIO


def hash_api_key(api_key: str) -> str:
    """Hash API key for audit logging (non-reversible).

    Uses SHA-256 truncated to 16 hex characters for secure,
    consistent hashing across Python runs.

    Args:
        api_key: The API key to hash.

    Returns:
        First 16 characters of the SHA-256 hash as hex string.
    """
    return hashlib.sha256(api_key.encode()).hexdigest()[:16]


class AuditLogger:
    """Structured audit logger for security events."""

    def __init__(self, output: TextIO | logging.Logger | None = None):
        """Initialize audit logger."""
        if output is None:
            self._logger = logging.getLogger("routilux.audit")
            self._use_logger = True
        elif isinstance(output, logging.Logger):
            self._logger = output
            self._use_logger = True
        else:
            self._output = output
            self._use_logger = False

    def _write(self, data: dict[str, Any]) -> None:
        """Write audit log entry."""
        if "timestamp" not in data:
            data["timestamp"] = datetime.now(timezone.utc).isoformat()

        if self._use_logger:
            self._logger.info(json.dumps(data))
        else:
            self._output.write(json.dumps(data) + "\n")
            self._output.flush()

    def log_api_call(
        self,
        endpoint: str,
        method: str,
        status: int,
        duration_ms: float,
        api_key_hash: str | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Log an API call."""
        self._write(
            {
                "event_type": "api_call",
                "endpoint": endpoint,
                "method": method,
                "status": status,
                "duration_ms": duration_ms,
                "api_key_hash": api_key_hash,
                "ip_address": ip_address,
            }
        )

    def log_auth_failure(
        self,
        reason: str,
        ip_address: str | None = None,
        api_key_provided: bool = False,
    ) -> None:
        """Log an authentication failure."""
        self._write(
            {
                "event_type": "auth_failure",
                "reason": reason,
                "ip_address": ip_address,
                "api_key_provided": api_key_provided,
            }
        )

    def log_rate_limit_exceeded(
        self, api_key_hash: str | None, ip_address: str, limit: int
    ) -> None:
        """Log a rate limit event."""
        self._write(
            {
                "event_type": "rate_limit_exceeded",
                "api_key_hash": api_key_hash,
                "ip_address": ip_address,
                "limit": limit,
            }
        )

    def log_configuration_change(self, setting: str, old_value: Any, new_value: Any) -> None:
        """Log a configuration change."""
        self._write(
            {
                "event_type": "configuration_change",
                "setting": setting,
                "old_value": str(old_value),
                "new_value": str(new_value),
            }
        )


# Global audit logger instance and lock for thread-safe singleton
_audit_logger: AuditLogger | None = None
_audit_logger_lock = threading.Lock()


def get_audit_logger() -> AuditLogger:
    """Get the global audit logger instance (thread-safe singleton)."""
    global _audit_logger
    if _audit_logger is None:
        with _audit_logger_lock:
            # Double-check pattern for thread safety
            if _audit_logger is None:
                if os.getenv("ROUTILUX_AUDIT_LOGGING_ENABLED", "true").lower() == "false":
                    # Create a no-op logger that discards output
                    _audit_logger = AuditLogger(output=None)
                else:
                    _audit_logger = AuditLogger()
    return _audit_logger
