"""
Centralized configuration for Hermes Agent.

Reads from environment variables and .env file. Call cfg.validate_llm()
before creating an LLMClient to get a clear error message when credentials
are missing instead of an obscure API error later.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # Load .env once; safe to call at import time


@dataclass(frozen=True)
class Config:
    api_url: str
    api_key: str
    log_level: str
    model: str

    def validate_llm(self) -> None:
        """Raise EnvironmentError if LLM credentials are absent."""
        missing = [
            name
            for name, val in [
                ("HERMES_API_URL", self.api_url),
                ("HERMES_API_KEY", self.api_key),
            ]
            if not val
        ]
        if missing:
            raise EnvironmentError(
                f"Missing required environment variable(s): {', '.join(missing)}\n"
                "Set them in your .env file or shell environment."
            )


cfg: Config = Config(
    api_url=os.getenv("HERMES_API_URL", ""),
    api_key=os.getenv("HERMES_API_KEY", ""),
    log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
    model=os.getenv("HERMES_MODEL", "gpt-5.5"),
)
