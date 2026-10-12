# macOS version and Darwin build comparison utility
from typing import Tuple, Optional
import re

class MacOSVersionChecker:
    @staticmethod
    def parse_darwin_version(version_str: str) -> Tuple[int, int, int]:
        """Parses Darwin string (e.g. '20.6.0' or '24.1.0') into tuple of ints."""
        if not version_str:
            return (0, 0, 0)
        clean = version_str.strip()
        parts = clean.split(".")
        try:
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return (major, minor, patch)
        except ValueError:
            return (0, 0, 0)

    @classmethod
    def darwin_to_macos_marketing_version(cls, darwin_str: str) -> str:
        major = cls.parse_darwin_version(darwin_str)[0]
        mapping = {
            17: "macOS High Sierra (10.13)",
            18: "macOS Mojave (10.14)",
            19: "macOS Catalina (10.15)",
            20: "macOS Big Sur (11.x)",
            21: "macOS Monterey (12.x)",
            22: "macOS Ventura (13.x)",
            23: "macOS Sonoma (14.x)",
            24: "macOS Sequoia (15.x)",
            25: "macOS Tahoe (16.x)",
            26: "macOS Tahoe (16.x)",
        }
        return mapping.get(major, f"Darwin {major}.x")

    @classmethod
    def is_version_supported(cls, target_version: str, min_version: str, max_version: str) -> bool:
        t = cls.parse_darwin_version(target_version)
        mi = cls.parse_darwin_version(min_version)
        ma = cls.parse_darwin_version(max_version)
        return mi <= t <= ma
