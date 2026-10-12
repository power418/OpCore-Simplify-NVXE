# PlistValidator: Validates OpenCore config.plist structures and rules
from typing import Dict, List, Tuple, Any
import plistlib

REQUIRED_OC_SECTIONS = [
    "ACPI",
    "Booter",
    "DeviceProperties",
    "Kernel",
    "Misc",
    "NVRAM",
    "PlatformInfo",
    "UEFI",
]

class PlistValidator:
    @staticmethod
    def validate_config(config_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        if not isinstance(config_data, dict):
            return False, ["Configuration data is not a dictionary."]

        # Check required sections
        for sec in REQUIRED_OC_SECTIONS:
            if sec not in config_data:
                errors.append(f"Missing required OpenCore section '{sec}'.")

        # Check for WhateverGreen and WhateverXe simultaneous activation
        kernel_add = config_data.get("Kernel", {}).get("Add", [])
        wg_enabled = False
        wxe_enabled = False
        nvidia_in_efi = False

        for kext in kernel_add:
            bpath = kext.get("BundlePath", "")
            enabled = kext.get("Enabled", False)
            if "WhateverGreen" in bpath and enabled:
                wg_enabled = True
            if "WhateverXe" in bpath and enabled:
                wxe_enabled = True
            if ("NVRM" in bpath or "NVAccel" in bpath) and enabled:
                nvidia_in_efi = True

        if wg_enabled and wxe_enabled:
            errors.append("Invalid configuration: WhateverGreen and WhateverXe are both enabled simultaneously!")

        if nvidia_in_efi:
            errors.append("Invalid configuration: NVIDIA r610 kernel extensions found in EFI/OC/Kexts Kernel/Add. They must be installed into /Library/Extensions only!")

        return len(errors) == 0, errors

    @classmethod
    def validate_plist_bytes(cls, raw_plist: bytes) -> Tuple[bool, List[str]]:
        try:
            data = plistlib.loads(raw_plist)
            return cls.validate_config(data)
        except Exception as e:
            return False, [f"Failed to parse plist format: {str(e)}"]
