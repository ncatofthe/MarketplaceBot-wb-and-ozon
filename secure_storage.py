"""
Защищенное хранение секретов для локального desktop runtime.
"""
import base64
import os


SECURE_VALUE_PREFIX = "marketplacebot-secure:v1:"
WINDOWS_SCHEME = "dpapi"
FALLBACK_SCHEME = "plain"
CRYPTPROTECT_UI_FORBIDDEN = 0x01


class SecretStorageError(Exception):
    """Ошибка шифрования или расшифровки секрета."""


def is_protected_secret(value):
    """Определяет, завернуто ли значение в supported secure envelope."""
    return isinstance(value, str) and value.startswith(SECURE_VALUE_PREFIX)


def _envelope_value(scheme, payload_bytes):
    """Сборка строкового envelope для секрета."""
    encoded_payload = base64.b64encode(payload_bytes).decode("ascii")
    return f"{SECURE_VALUE_PREFIX}{scheme}:{encoded_payload}"


def _parse_envelope(value):
    """Парсинг envelope-секрета."""
    if not is_protected_secret(value):
        raise SecretStorageError("Value is not protected")

    remainder = value[len(SECURE_VALUE_PREFIX) :]
    scheme, separator, encoded_payload = remainder.partition(":")
    if not separator or not scheme or not encoded_payload:
        raise SecretStorageError("Malformed protected secret envelope")

    try:
        payload = base64.b64decode(encoded_payload.encode("ascii"))
    except Exception as error:
        raise SecretStorageError(f"Invalid protected secret payload: {error}") from error

    return scheme, payload


def get_protected_secret_scheme(value):
    """Возвращает схему защищённого секрета или None."""
    if not is_protected_secret(value):
        return None
    scheme, _ = _parse_envelope(value)
    return scheme


def _dpapi_encrypt_bytes(data):
    """Шифрование байтов через Windows DPAPI."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    input_buffer = ctypes.create_string_buffer(data)
    input_blob = DATA_BLOB(len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_char)))
    output_blob = DATA_BLOB()

    success = crypt32.CryptProtectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    if not success:
        raise SecretStorageError(f"DPAPI encryption failed with code {ctypes.GetLastError()}")

    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def _dpapi_decrypt_bytes(data):
    """Расшифровка байтов через Windows DPAPI."""
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [
            ("cbData", wintypes.DWORD),
            ("pbData", ctypes.POINTER(ctypes.c_char)),
        ]

    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    input_buffer = ctypes.create_string_buffer(data)
    input_blob = DATA_BLOB(len(data), ctypes.cast(input_buffer, ctypes.POINTER(ctypes.c_char)))
    output_blob = DATA_BLOB()

    success = crypt32.CryptUnprotectData(
        ctypes.byref(input_blob),
        None,
        None,
        None,
        None,
        CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(output_blob),
    )
    if not success:
        raise SecretStorageError(f"DPAPI decryption failed with code {ctypes.GetLastError()}")

    try:
        return ctypes.string_at(output_blob.pbData, output_blob.cbData)
    finally:
        kernel32.LocalFree(output_blob.pbData)


def protect_secret(secret, os_name=None):
    """Защищает секрет и возвращает явный строковый envelope."""
    if secret is None:
        return ""

    if is_protected_secret(secret):
        try:
            secret = unprotect_secret(secret, os_name=os_name)
        except SecretStorageError:
            pass

    secret = str(secret or "")
    if not secret:
        return ""

    os_name = os.name if os_name is None else os_name
    secret_bytes = secret.encode("utf-8")

    if os_name == "nt":
        try:
            return _envelope_value(WINDOWS_SCHEME, _dpapi_encrypt_bytes(secret_bytes))
        except SecretStorageError as error:
            raise SecretStorageError(f"DPAPI encryption is required on Windows: {error}") from error

    return _envelope_value(FALLBACK_SCHEME, secret_bytes)


def unprotect_secret(value, os_name=None):
    """Возвращает исходный секрет из envelope или legacy plaintext как есть."""
    if value is None:
        return ""

    if not is_protected_secret(value):
        return str(value)

    os_name = os.name if os_name is None else os_name
    scheme, payload = _parse_envelope(value)

    if scheme == WINDOWS_SCHEME:
        if os_name != "nt":
            raise SecretStorageError("DPAPI protected secret can only be decrypted on Windows")
        try:
            return _dpapi_decrypt_bytes(payload).decode("utf-8")
        except UnicodeDecodeError as error:
            raise SecretStorageError(f"Invalid UTF-8 in DPAPI secret: {error}") from error

    if scheme == FALLBACK_SCHEME:
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as error:
            raise SecretStorageError(f"Invalid UTF-8 in protected secret: {error}") from error

    raise SecretStorageError(f"Unsupported secret scheme: {scheme}")
