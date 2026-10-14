# OpenCoreIntegrator: Deterministic applicator of OpenCore config changes for experimental drivers
from typing import Dict, List, Optional, Any
import copy
import re

class OpenCoreIntegrator:
    @staticmethod
    def append_boot_args(current_boot_args: str, new_args: List[str]) -> str:
        """Appends new boot arguments without duplicating flags."""
        current_tokens = current_boot_args.split() if current_boot_args else []
        for arg in new_args:
            arg = arg.strip()
            if not arg:
                continue
            # For key=value args, check prefix
            if "=" in arg:
                prefix = arg.split("=")[0] + "="
                current_tokens = [tok for tok in current_tokens if not tok.startswith(prefix)]
                current_tokens.append(arg)
            else:
                if arg not in current_tokens:
                    current_tokens.append(arg)
        return " ".join(current_tokens)

    @classmethod
    def apply_config_changes(cls, config_data: Dict[str, Any], changes: List[Any]) -> Dict[str, Any]:
        """Applies a list of ConfigChange objects to OpenCore config dictionary safely."""
        config = copy.deepcopy(config_data)

        for change in changes:
            key_path = change.key_path

            if "boot-args" in key_path:
                nvram_add = config.setdefault("NVRAM", {}).setdefault("Add", {}).setdefault("7C436110-AB2A-4BBB-A880-FE41995C9F82", {})
                curr = nvram_add.get("boot-args", "")
                if isinstance(curr, bytes):
                    curr = curr.decode("utf-8", errors="ignore")
                new_tokens = change.new_value.split() if isinstance(change.new_value, str) else []
                nvram_add["boot-args"] = cls.append_boot_args(curr, new_tokens)

            elif "csr-active-config" in key_path:
                nvram_add = config.setdefault("NVRAM", {}).setdefault("Add", {}).setdefault("7C436110-AB2A-4BBB-A880-FE41995C9F82", {})
                hex_str = str(change.new_value).replace("<", "").replace(">", "").strip()
                try:
                    nvram_add["csr-active-config"] = bytes.fromhex(hex_str)
                except ValueError:
                    nvram_add["csr-active-config"] = hex_str

            elif "ResizeAppleGpuBars" in key_path:
                config.setdefault("Booter", {}).setdefault("Quirks", {})["ResizeAppleGpuBars"] = int(change.new_value)

            elif "ResizeGpuBars" in key_path:
                config.setdefault("UEFI", {}).setdefault("Quirks", {})["ResizeGpuBars"] = int(change.new_value)

            elif "SecureBootModel" in key_path:
                config.setdefault("Misc", {}).setdefault("Security", {})["SecureBootModel"] = str(change.new_value)

            elif "Kernel/Block/IONDRVSupport" in key_path:
                block_list = config.setdefault("Kernel", {}).setdefault("Block", [])
                if not any(entry.get("Identifier") == "com.apple.iokit.IONDRVSupport" for entry in block_list):
                    block_list.append({
                        "Arch": "x86_64",
                        "Comment": "Exclude IONDRVSupport for NVIDIA NVRMFB",
                        "Enabled": True,
                        "Identifier": "com.apple.iokit.IONDRVSupport",
                        "MaxKernel": "",
                        "MinKernel": "24.0.0",
                        "Strategy": "Exclude",
                    })

            elif "Kernel/Add/WhateverGreen/Enabled" in key_path:
                add_list = config.setdefault("Kernel", {}).setdefault("Add", [])
                for entry in add_list:
                    if "WhateverGreen" in entry.get("BundlePath", ""):
                        entry["Enabled"] = False

            elif "Kernel/Add/WhateverXe.kext" in key_path:
                add_list = config.setdefault("Kernel", {}).setdefault("Add", [])
                if not any(entry.get("BundlePath") == "WhateverXe.kext" for entry in add_list):
                    add_list.append({
                        "Arch": "x86_64",
                        "BundlePath": "WhateverXe.kext",
                        "Comment": "Intel Xe-LP graphics driver plugin",
                        "Enabled": True,
                        "ExecutablePath": "Contents/MacOS/WhateverXe",
                        "MaxKernel": "",
                        "MinKernel": "",
                        "PlistPath": "Contents/Info.plist",
                    })

            elif "Kernel/Add/AMFIPass.kext" in key_path:
                add_list = config.setdefault("Kernel", {}).setdefault("Add", [])
                if not any(entry.get("BundlePath") == "AMFIPass.kext" for entry in add_list):
                    add_list.append({
                        "Arch": "x86_64",
                        "BundlePath": "AMFIPass.kext",
                        "Comment": "AMFIPass Mod for Xe graphics",
                        "Enabled": True,
                        "ExecutablePath": "Contents/MacOS/AMFIPass",
                        "MaxKernel": "",
                        "MinKernel": "",
                        "PlistPath": "Contents/Info.plist",
                    })

            elif key_path.startswith("DeviceProperties/Add/"):
                # e.g. "DeviceProperties/Add/PciRoot(0x0)/Pci(0x2,0x0)"
                # new_value is a dict of properties (Data bytes or str).
                pci_path = key_path[len("DeviceProperties/Add/"):]
                if pci_path and isinstance(change.new_value, dict):
                    dp_add = config.setdefault("DeviceProperties", {}).setdefault("Add", {})
                    node = dp_add.setdefault(pci_path, {})
                    for prop_key, prop_val in change.new_value.items():
                        if isinstance(prop_val, str) and prop_key != "model":
                            # Accept 'D2460000' style Data hex strings.
                            s = "".join(c for c in prop_val if c in "0123456789abcdefABCDEF")
                            if len(s) == 8:
                                try:
                                    node[prop_key] = bytes.fromhex(s)
                                    continue
                                except ValueError:
                                    pass
                        node[prop_key] = prop_val

        return config
