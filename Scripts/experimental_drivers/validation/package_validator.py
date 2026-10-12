# PackageValidator: File existence and SHA-256 integrity verification
import os
import hashlib
from typing import Tuple, Optional

class PackageValidator:
    @staticmethod
    def calculate_sha256(file_path: str) -> Optional[str]:
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return None
        hasher = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)
            return hasher.hexdigest().lower()
        except Exception:
            return None

    @classmethod
    def verify_file_checksum(cls, file_path: str, expected_sha256: str) -> Tuple[bool, str]:
        if not os.path.exists(file_path):
            return False, f"File does not exist: {file_path}"
        actual = cls.calculate_sha256(file_path)
        if not actual:
            return False, f"Failed to compute checksum for {file_path}"
        clean_exp = expected_sha256.lower().strip()
        if actual != clean_exp:
            return False, f"Checksum mismatch: expected {clean_exp}, got {actual}"
        return True, "Checksum OK"
