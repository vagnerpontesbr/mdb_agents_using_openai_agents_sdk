"""Trusted loopback configuration; request data never selects a database."""

import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

APPLICATION_HOST = "openai-sdk.qrmdk.mongodb.net"
DATABASE = "telecom_identity"
CONCURRENCY = 8


@dataclass(frozen=True)
class Settings:
    mongodb_uri: str = field(repr=False)
    origin: str = "http://127.0.0.1:8000"
    web_dist: Path | None = None

    def __post_init__(self) -> None:
        try:
            uri = urlsplit(self.mongodb_uri)
            options = parse_qs(uri.query, keep_blank_values=True)
            allowed = {"authsource", "retrywrites", "appname", "w", "tls"}
            valid = (
                uri.scheme == "mongodb+srv"
                and uri.hostname == APPLICATION_HOST
                and uri.port is None
                and bool(uri.username and uri.password)
                and uri.path in ("", "/")
                and not uri.fragment
                and all(key.lower() in allowed and len(values) == 1
                        for key, values in options.items())
                and all(values == ["true"] for key, values in options.items()
                        if key.lower() == "tls")
            )
            origin = urlsplit(self.origin)
            valid_origin = (
                origin.scheme == "http" and origin.hostname == "127.0.0.1"
                and origin.username is None and origin.password is None
                and origin.port is not None and 1024 <= origin.port <= 65535
                and not origin.path and not origin.query and not origin.fragment
                and self.origin == f"http://127.0.0.1:{origin.port}"
            )
        except ValueError:
            raise ValueError("Invalid demo configuration; details suppressed") from None
        if not valid:
            raise ValueError("Inject a TLS SRV URI for the approved application cluster")
        if not valid_origin:
            raise ValueError("APP_ORIGIN must be http://127.0.0.1:<port> (1024-65535)")
        if self.web_dist is not None and not (self.web_dist / "index.html").is_file():
            raise ValueError("APP_WEB_DIST must contain a completed frontend build")

    @classmethod
    def from_env(cls) -> Settings:
        host = os.environ.get("APP_MONGODB_HOST", APPLICATION_HOST)
        if host != APPLICATION_HOST:
            raise ValueError("APP_MONGODB_HOST must select the approved application cluster")
        dist = os.environ.get("APP_WEB_DIST")
        return cls(
            mongodb_uri=os.environ.get("APP_MONGODB_URI", ""),
            origin=os.environ.get("APP_ORIGIN", "http://127.0.0.1:8000"),
            web_dist=Path(dist).resolve() if dist else None,
        )
