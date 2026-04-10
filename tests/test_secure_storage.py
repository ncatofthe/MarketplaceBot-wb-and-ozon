import unittest
from unittest import mock

import secure_storage as secure_storage_module


class SecureStorageTests(unittest.TestCase):
    def test_windows_protect_secret_uses_dpapi_envelope_on_success(self):
        with mock.patch.object(secure_storage_module, "_dpapi_encrypt_bytes", return_value=b"ciphertext"):
            protected = secure_storage_module.protect_secret("wb-secret", os_name="nt")

        self.assertEqual(
            secure_storage_module.get_protected_secret_scheme(protected),
            secure_storage_module.WINDOWS_SCHEME,
        )

    def test_windows_protect_secret_raises_when_dpapi_fails(self):
        with mock.patch.object(
            secure_storage_module,
            "_dpapi_encrypt_bytes",
            side_effect=secure_storage_module.SecretStorageError("dpapi unavailable"),
        ):
            with self.assertRaises(secure_storage_module.SecretStorageError):
                secure_storage_module.protect_secret("wb-secret", os_name="nt")

    def test_plain_fallback_envelope_still_loads_for_backward_compatibility(self):
        protected = secure_storage_module.protect_secret("legacy-secret", os_name="posix")

        self.assertEqual(secure_storage_module.unprotect_secret(protected, os_name="posix"), "legacy-secret")


if __name__ == "__main__":
    unittest.main()
