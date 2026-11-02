import asyncio

import bcrypt

# bcrypt only uses the first 72 bytes of a password; bcrypt>=5 raises on longer input.
MAX_PASSWORD_BYTES = 72

# Checked when the username doesn't exist, so a failed login takes the same time
# whether or not the user exists (prevents username enumeration by timing).
_DUMMY_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt())


def _hash(password: bytes) -> str:
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode()


def _check(password: bytes, hashed: bytes) -> bool:
    return bcrypt.checkpw(password, hashed)


# bcrypt is deliberately slow (~150 ms of CPU), so it runs in a worker thread
# instead of blocking the event loop and stalling every other request.


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash, password.encode())


async def verify_password(password: str, hashed_password: str | None) -> bool:
    """Check a password against a stored hash.

    Pass `hashed_password=None` for an unknown user: a dummy hash is checked so the
    response time doesn't reveal whether the username exists. Always returns False then.
    """
    secret = password.encode()
    if len(secret) > MAX_PASSWORD_BYTES:
        # Can never match (registration rejects these), and bcrypt>=5 would raise.
        secret = secret[:MAX_PASSWORD_BYTES]
        hashed_password = None
    if hashed_password is None:
        await asyncio.to_thread(_check, secret, _DUMMY_HASH)
        return False
    return await asyncio.to_thread(_check, secret, hashed_password.encode())
