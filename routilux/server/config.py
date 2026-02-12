"""
API configuration management.

Handles loading and validation of API configuration from environment variables.
"""

import logging
import os
import threading
import warnings
from typing import List, Optional

logger = logging.getLogger(__name__)


class APIConfig:
    """API configuration.

    Loads configuration from environment variables with secure-by-default settings.

    Auth control (all-or-nothing, 要么都保护要么都放开):
        ROUTILUX_API_KEY_ENABLED controls whether all APIs require X-API-Key:
        - true:  All REST endpoints and WebSockets require a valid X-API-Key
                 (header for REST; api_key query for WebSocket). 401/403 or
                 close(1008) when missing/invalid.
        - false: All endpoints are public; X-API-Key is ignored if sent.
        No mixed mode: the server either protects everything or nothing.

    Security defaults (P0-1 fix):
        - api_key_enabled defaults to True (secure by default)
        - rate_limit_enabled defaults to True (secure by default)
        - ROUTILUX_DEV_DISABLE_SECURITY can be set to "true" to disable both
          for development purposes (should be used with caution)
        - ROUTILUX_ENV can be set to "production" to enforce security
    """

    def __init__(self):
        """Load configuration from environment with secure defaults."""
        # Determine environment (production vs development)
        # Check both ROUTILUX_ENV and ENVIRONMENT for flexibility
        self.is_production = (
            os.getenv("ROUTILUX_ENV", "").lower() == "production"
            or os.getenv("ENVIRONMENT", "").lower() == "production"
        )

        # Check for development mode flag (explicit opt-out for development)
        # In production, DEV_DISABLE_SECURITY is ignored for safety
        dev_disable_security = (
            not self.is_production
            and os.getenv("ROUTILUX_DEV_DISABLE_SECURITY", "false").lower() == "true"
        )

        # API Key authentication: defaults to True (secure by default)
        # Can be explicitly disabled with ROUTILUX_DEV_DISABLE_SECURITY for development
        if dev_disable_security:
            self.api_key_enabled: bool = False
            logger.warning(
                "SECURITY WARNING: ROUTILUX_DEV_DISABLE_SECURITY is enabled. "
                "API key authentication is DISABLED. This should ONLY be used for "
                "local development and NEVER in production."
            )
            warnings.warn(
                "API key authentication is disabled via ROUTILUX_DEV_DISABLE_SECURITY. "
                "This should only be used for local development.",
                stacklevel=2,
            )
        elif self.is_production:
            # Production enforces security - ignore explicit disable attempts
            self.api_key_enabled: bool = True
            logger.info("Production environment: API key authentication is enforced")
        else:
            # Default to True (secure by default), allow explicit override in non-production
            env_value = os.getenv("ROUTILUX_API_KEY_ENABLED", "true").lower()
            self.api_key_enabled: bool = env_value == "true"

            if not self.api_key_enabled:
                logger.warning(
                    "SECURITY WARNING: API key authentication is DISABLED. "
                    "The API will be open to all requests without authentication."
                )
                warnings.warn(
                    "API key authentication is disabled. The API will be open to all requests.",
                    stacklevel=2,
                )

        self.api_keys: List[str] = self._load_api_keys()

        # CORS (already handled in main.py, but keep for reference)
        self.cors_origins: str = os.getenv("ROUTILUX_CORS_ORIGINS", "")

        # Rate limiting: defaults to True (secure by default)
        if dev_disable_security:
            self.rate_limit_enabled: bool = False
            logger.warning(
                "SECURITY WARNING: Rate limiting is DISABLED via "
                "ROUTILUX_DEV_DISABLE_SECURITY. This should ONLY be used for "
                "local development and NEVER in production."
            )
        elif self.is_production:
            # Production enforces security - ignore explicit disable attempts
            self.rate_limit_enabled: bool = True
            logger.info("Production environment: Rate limiting is enforced")
        else:
            env_value = os.getenv("ROUTILUX_RATE_LIMIT_ENABLED", "true").lower()
            self.rate_limit_enabled: bool = env_value == "true"

            if not self.rate_limit_enabled:
                logger.warning(
                    "SECURITY WARNING: Rate limiting is DISABLED. "
                    "The API will be vulnerable to abuse and DoS attacks."
                )
                warnings.warn(
                    "Rate limiting is disabled. The API will be vulnerable to abuse.", stacklevel=2
                )

        # Validate rate_limit_per_minute with proper error handling
        try:
            self.rate_limit_per_minute: int = int(os.getenv("ROUTILUX_RATE_LIMIT_PER_MINUTE", "60"))
            if self.rate_limit_per_minute <= 0:
                raise ValueError("rate_limit_per_minute must be positive")
        except (ValueError, TypeError) as e:
            logger.warning(f"Invalid ROUTILUX_RATE_LIMIT_PER_MINUTE, using default: {e}")
            self.rate_limit_per_minute = 60

    def _load_api_keys(self) -> List[str]:
        """Load API keys from environment.

        Supports:
        - ROUTILUX_API_KEY: Single API key
        - ROUTILUX_API_KEYS: Comma-separated list of API keys

        Returns:
            List of API keys.
        """
        keys = []

        # Single key
        single_key = os.getenv("ROUTILUX_API_KEY")
        if single_key:
            keys.append(single_key.strip())

        # Multiple keys
        multiple_keys = os.getenv("ROUTILUX_API_KEYS")
        if multiple_keys:
            keys.extend([k.strip() for k in multiple_keys.split(",") if k.strip()])

        return keys

    def is_api_key_valid(self, api_key: Optional[str]) -> bool:
        """Check if API key is valid.

        Args:
            api_key: API key to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not self.api_key_enabled:
            return True  # Authentication disabled

        if not api_key:
            return False

        return api_key in self.api_keys


# Global config instance
_config: Optional[APIConfig] = None
_config_lock = threading.Lock()


def get_config() -> APIConfig:
    """Get global API config instance.

    Critical fix: Thread-safe singleton initialization using double-checked locking.

    Returns:
        APIConfig instance.
    """
    global _config
    if _config is None:
        with _config_lock:
            # Double-check inside lock
            if _config is None:
                _config = APIConfig()
    return _config
