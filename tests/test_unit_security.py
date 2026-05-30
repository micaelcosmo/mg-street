from app import hash_password, verify_password


def test_hash_password_is_not_plaintext():
    hashed = hash_password("segredo123")
    assert hashed != "segredo123"
    assert isinstance(hashed, str)


def test_verify_password_roundtrip():
    hashed = hash_password("segredo123")
    assert verify_password("segredo123", hashed)


def test_verify_password_rejects_wrong_password():
    hashed = hash_password("segredo123")
    assert not verify_password("errado", hashed)
