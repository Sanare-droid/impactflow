from app.core.security import (
    create_access_token,
    decode_token,
    encrypt_secret,
    decrypt_secret,
    hash_password,
    verify_password,
    hash_token,
)
from app.services.auth import slugify


def test_password_hash_roundtrip():
    hashed = hash_password("SecurePass123!")
    assert verify_password("SecurePass123!", hashed)
    assert not verify_password("wrong", hashed)


def test_access_token_roundtrip():
    token = create_access_token(
        "user-1",
        organization_id="org-1",
        roles=["org_admin"],
        permissions=["dashboard:read"],
    )
    payload = decode_token(token)
    assert payload["sub"] == "user-1"
    assert payload["org_id"] == "org-1"
    assert payload["type"] == "access"
    assert "dashboard:read" in payload["permissions"]


def test_encrypt_decrypt_secret():
    encrypted = encrypt_secret("mfa-secret-value")
    assert decrypt_secret(encrypted) == "mfa-secret-value"


def test_hash_token_stable():
    assert hash_token("abc") == hash_token("abc")
    assert hash_token("abc") != hash_token("abcd")


def test_slugify():
    assert slugify("Hope Foundation") == "hope-foundation"
    assert slugify("  MEAL!!! Ops  ") == "meal-ops"
