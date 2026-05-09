"""AES CBC helpers matching PyRobovac / lakeside key material."""

from __future__ import annotations

from Crypto.Cipher import AES

# Fixed keying material ported from archived PyRobovac (<https://pypi.org/project/robovac/>),
# traced to Google's Apache-2.0 python-lakeside reference implementation.
_AES_KEY = bytes(
    [
        0x24,
        0x4E,
        0x6D,
        0x8A,
        0x56,
        0xAC,
        0x87,
        0x91,
        0x24,
        0x43,
        0x2D,
        0x8B,
        0x6C,
        0xBC,
        0xA2,
        0xC4,
    ]
)
_AES_IV = bytes(
    [
        0x77,
        0x24,
        0x56,
        0xF2,
        0xA7,
        0x66,
        0x4C,
        0xF3,
        0x39,
        0x2C,
        0x35,
        0x97,
        0xE9,
        0x3E,
        0x57,
        0x47,
    ]
)


def encrypt(data: bytes) -> bytes:
    """AES-CBC PKCS padding via zero bytes (upstream behavior)."""

    padded = data
    remainder = len(padded) % 16
    if remainder != 0:
        padded += bytes(16 - remainder)
    cipher = AES.new(_AES_KEY, AES.MODE_CBC, _AES_IV)
    return cipher.encrypt(padded)


def decrypt(data: bytes) -> bytes:
    """Symmetric decrypt matching RoboVac firmware framing."""

    cipher = AES.new(_AES_KEY, AES.MODE_CBC, _AES_IV)
    return cipher.decrypt(data)
