"""登录用到的密码哈希与 session token 处理；加密相关只调用成熟的库。"""

import hashlib
import secrets

from pwdlib import PasswordHash

# argon2id，参数用库的推荐值（这台机器上约 30 ms、占 64 MB 内存）。
_password_hash = PasswordHash.recommended()
# 账号不存在时拿它验证一次，让两种登录失败的耗时接近。
_DUMMY_HASH = _password_hash.hash("dummy_password-for-timing")


def hash_password(password: str) -> str:
    """注册时调用：返回带算法、参数和随机盐的 argon2 哈希字符串。"""
    return _password_hash.hash(password)


def verify_password(password: str, hashed_password: str | None) -> bool:
    """登录时调用；hashed_password 为 None 表示账号不存在，仍验证一次再返回 False。"""
    if hashed_password is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, hashed_password)


def new_session_token() -> str:
    """生成 32 字节随机数的 URL 安全编码，作为写进 Cookie 的 token 原文。"""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """token 本身随机且足够长，用快速的 SHA-256 即可；数据库只存这个值。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
