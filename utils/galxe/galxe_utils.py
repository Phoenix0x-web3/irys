import hashlib
import json
import random
import time
from typing import Optional

from eth_hash.auto import keccak  # eth-hash

from modules.encoder.encoder_client import get_encrypted_data

GA_MAX_AGE = 60 * 60 * 24 * 365 * 2


def _rand10() -> int:
    return random.randint(10**9, 10**10 - 1)


def generate_ga_client_id(rand: int | None = None, first_ts: int | None = None) -> str:
    r = int(rand) if rand is not None else _rand10()
    ts = int(first_ts) if first_ts is not None else int(time.time())
    return f"{r}.{ts}"


def generate_ga_cookie_value(
    rand: int | None = None,
    first_ts: int | None = None,
) -> str:
    cid = generate_ga_client_id(rand=rand, first_ts=first_ts)
    return cid


def _keccak256_hex(data: bytes) -> str:
    return keccak(data).hex()


def make_x_unique_link_id(galxe_id: Optional[str], suffix: str = "") -> str:
    base = "null" if galxe_id is None else str(galxe_id)
    raw = (base + (suffix)).encode("utf-8")
    return _keccak256_hex(raw)


async def get_captcha(action: str, proxy: str, use_encrypted_data: bool = False):
    def sha256_hex(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    gen_time = str(int(time.time()))

    encrypted_data = json.loads(await get_encrypted_data(action, gen_time, proxy))
    if encrypted_data is None:
        raise Exception("Failed to get encrypted data")

    captcha = {
        "lotNumber": sha256_hex(action),
        "captchaOutput": encrypted_data["geetest_encrypted"],
        "passToken": sha256_hex(gen_time),
        "genTime": gen_time,
        "encryptedData": "",
    }

    if use_encrypted_data:
        captcha.update({"encryptedData": encrypted_data["encrypted_data"]})

    return captcha
