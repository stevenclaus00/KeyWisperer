"""Pairing token and the kw:// URI shown as a QR code for the phone."""

from __future__ import annotations

import os
import secrets
import socket
from urllib.parse import quote

from .config import config_dir


def token_path():
    return config_dir() / "token"


def load_or_create_token() -> str:
    """Return the persisted token, creating it (chmod 600) on first run."""
    path = token_path()
    if path.exists():
        token = path.read_text().strip()
        if token:
            return token
    path.parent.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(24)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token + "\n")
    os.chmod(path, 0o600)
    return token


def lan_ip() -> str:
    """Best-guess LAN IP via a (never-sent) UDP connect; falls back to localhost."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def pairing_uri(port: int, token: str, host: str | None = None) -> str:
    return f"kw://{host or lan_ip()}:{port}?token={quote(token)}"


def print_pairing(port: int) -> str:
    """Print the URI and an ASCII QR code; returns the URI."""
    import qrcode

    uri = pairing_uri(port, load_or_create_token())
    print(f"\nPairing URI: {uri}\n")
    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.make(fit=True)
    qr.print_ascii(invert=True)
    return uri
