"""Re-encrypt every stored secret with the primary `HB_ENCRYPTION_KEY` (key rotation).

Usage (after putting the new key first in the comma-separated list):
    python -m handball_api.rotate_keys
Idempotent; prints how many secrets were rotated. Run before removing the old key.
"""

from __future__ import annotations

import asyncio

from cryptography.fernet import InvalidToken
from sqlalchemy import select

from handball_api.core.config import get_settings
from handball_api.core.db import enable_system_access, init_engine, open_session
from handball_api.core.security import SecretBox
from handball_api.models import User


async def rotate(database_url: str | None = None) -> tuple[int, int]:
    settings = get_settings()
    init_engine(database_url or settings.database_url)
    box = SecretBox(settings.encryption_key.get_secret_value())
    rotated = failed = 0
    async with open_session() as db:
        await enable_system_access(db, reason="encryption key rotation")
        users = (await db.scalars(select(User).where(User.totp_secret_enc.is_not(None)))).all()
        for user in users:
            try:
                user.totp_secret_enc = box.rotate(user.totp_secret_enc or "")
                rotated += 1
            except InvalidToken:
                failed += 1
    return rotated, failed


def main() -> None:
    rotated, failed = asyncio.run(rotate())
    print(f"rotated {rotated} secrets, {failed} could not be decrypted with any configured key")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
