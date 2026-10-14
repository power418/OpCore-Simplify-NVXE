# PlistValidator: Validates OpenCore config.plist structures and rules
from typing import Dict, List, Tuple, Any, Optional
import plistlib

try:
    from Scripts.datasets import whateverxe_data
except ImportError:  # pragma: no cover - fallback for direct test invocation
    from ...datasets import whateverxe_data  # type: ignore

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
    def _get_boot_args(config_data: Dict[str, Any]) -> str:
        try:
            raw = config_data.get("NVRAM", {}).get("Add", {}).get(
                "7C436110-AB2A-4BBB-A880-FE41995C9F82", {}).get("boot-args", "")
        except AttributeError:
            return ""
        if isinstance(raw, (bytes, bytearray)):
            try:
                return bytes(raw).decode("utf-8", errors="ignore")
            except Exception:
                return ""
        return str(raw or "")

    @staticmethod
    def _find_xe_igpu_node(config_data: Dict[str, Any]):
        """Returns (pci_path, props_dict) for Pci(0x2,0x0) node, else (None, None)."""
        try:
            add = config_data.get("DeviceProperties", {}).get("Add", {})
        except AttributeError:
            return None, None
        if not isinstance(add, dict):
            return None, None
        for path, props in add.items():
            p = str(path or "")
            if "Pci(0x2,0x0)" in p and "Pci(0x1" not in p:
                return path, props
        return None, None

    @classmethod
    def validate_whateverxe_device_properties(
        cls, config_data: Dict[str, Any], hardware_report: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, List[str], List[str]]:
        """WhateverGreen-style validation, scoped to WhateverXe README rules.

        Checks DeviceProperties on the iGPU node + matching boot-args:
        - only device-id / model / DVMT pair keys are allowed
        - device-id is strict 4-byte LE Data targeting an implemented backend
        - DVMT pair is both-or-neither with exact values + -igfxdvmt flag
        - required boot-args -allow3d -disablegfxfirmware are present
        - no WhateverGreen wiring keys on the Xe node
        Invalid overrides never silently fall back (reported as errors).

        Returns (is_valid, errors, warnings).
        """
        from Scripts.datasets import whateverxe_data as _xe

        errors: List[str] = []
        warnings: List[str] = []

        if not isinstance(config_data, dict):
            return False, ["Configuration data is not a dictionary."], warnings

        kernel_add = config_data.get("Kernel", {}).get("Add", []) or []
        wxe_enabled = any("WhateverXe" in str(k.get("BundlePath", "")) and k.get("Enabled") for k in kernel_add if isinstance(k, dict))
        boot_args = cls._get_boot_args(config_data)
        tokens = boot_args.split()

        if "-xe-force-enable" in tokens:
            errors.append("Invalid boot-arg '-xe-force-enable': not part of WhateverXe README (use '-allow3d -disablegfxfirmware').")

        pci_path, props = cls._find_xe_igpu_node(config_data)

        if "#WhateverXe-error" in (props or {}):
            errors.append("Invalid WhateverXe DeviceProperties on {}: device-id override rejected (see docs/device-selection.md; no silent fallback).".format(pci_path))
            return False, errors, warnings

        if not wxe_enabled:
            # Xe props without the kext are at best stale.
            if props:
                warnings.append("DeviceProperties on {} look like WhateverXe props but WhateverXe.kext is not enabled.".format(pci_path))
            return len(errors) == 0, errors, warnings

        # --- required boot-args ---
        for arg in _xe.REQUIRED_BOOT_ARGS:
            if arg not in tokens:
                errors.append("Missing required WhateverXe boot-arg '{}' (README: -allow3d -disablegfxfirmware).".format(arg))

        if props is None:
            # Automatic selection with 96MB DVMT needs no props: valid.
            props = {}

        if not isinstance(props, dict):
            return False, ["DeviceProperties node {} is not a dictionary.".format(pci_path)], warnings

        # --- key allowlist (WhateverGreen wiring keys are forbidden for Xe) ---
        for key in list(props.keys()):
            if str(key).startswith("#"):
                warnings.append("Disabled/commented DeviceProperty '{}' on {} is ignored.".format(key, pci_path))
                continue
            if key not in _xe.ALLOWED_IGPU_KEYS_FOR_XE:
                if key in _xe.FORBIDDEN_IGPU_KEYS_FOR_XE:
                    errors.append(
                        "Invalid DeviceProperty '{}' on {}: WhateverGreen wiring/platform-id key is not valid for WhateverXe "
                        "(connector routing comes from firmware VBT; see README Configuration).".format(key, pci_path))
                else:
                    errors.append("Unknown DeviceProperty '{}' on {} (allowed for Xe: device-id, model, framebuffer-patch-enable, framebuffer-stolenmem).".format(key, pci_path))

        # --- device-id override ---
        if "device-id" in props and not str("device-id").startswith("#"):
            raw = props.get("device-id")
            raw_bytes = bytes(raw) if isinstance(raw, (bytes, bytearray)) else None
            if raw_bytes is None and isinstance(raw, str):
                s = "".join(c for c in raw if c in "0123456789abcdefABCDEF")
                try:
                    raw_bytes = bytes.fromhex(s) if len(s) == 8 else None
                except ValueError:
                    raw_bytes = None
            target = _xe.decode_device_id_override(raw_bytes) if raw_bytes is not None else None
            if target is None:
                errors.append("Invalid 'device-id' on {}: must be Data with exactly four little-endian bytes (e.g. D2460000 for 0x46D2).".format(pci_path))
            else:
                # Reuse canonical validation (rejects 0000/FFFF, unknown,
                # identification-only targets; no silent fallback).
                phys = ""
                vendor = "8086"
                if hardware_report:
                    for _n, _p in (hardware_report.get("GPU", {}) or {}).items():
                        if _p.get("Device Type") == "Integrated GPU" and "Intel" in str(_p.get("Manufacturer", "")):
                            raw_id = str(_p.get("Device ID", ""))
                            vendor = raw_id.split("-")[0].upper() if "-" in raw_id else "8086"
                            phys = raw_id
                            break
                ok, _t, err, w = _xe.validate_device_id_override(raw_bytes, phys or "8086-0000", vendor)
                warnings.extend(w)
                if not ok:
                    errors.append("Invalid 'device-id' on {}: {}".format(pci_path, err))
                elif _t == _xe.normalize_device_id(phys):
                    warnings.append("device-id override 0x{} equals the physical ID; prefer automatic selection.".format(_t))

        # --- DVMT 60MB pair: both-or-neither, exact values, + -igfxdvmt ---
        has_patch = "framebuffer-patch-enable" in props
        has_stolen = "framebuffer-stolenmem" in props
        if has_patch != has_stolen:
            errors.append("Invalid DVMT properties on {}: 'framebuffer-patch-enable' and 'framebuffer-stolenmem' must be set together (README DVMT 60MB) or both omitted (96MB).".format(pci_path))
        if has_patch and has_stolen:
            def _hex(v):
                if isinstance(v, (bytes, bytearray)):
                    return bytes(v).hex().upper()
                s = "".join(c for c in str(v) if c in "0123456789abcdefABCDEF")
                return s.upper()
            if _hex(props.get("framebuffer-patch-enable")) != "01000000":
                errors.append("Invalid 'framebuffer-patch-enable' on {}: must be Data 01000000 for DVMT 60MB.".format(pci_path))
            if _hex(props.get("framebuffer-stolenmem")) != "0000C003":
                errors.append("Invalid 'framebuffer-stolenmem' on {}: must be Data 0000C003 for DVMT 60MB.".format(pci_path))
            if "-igfxdvmt" not in tokens:
                errors.append("Missing boot-arg '-igfxdvmt': required when the DVMT 60MB DeviceProperties pair is present.")
        else:
            if "-igfxdvmt" in tokens and not (has_patch and has_stolen):
                errors.append("Boot-arg '-igfxdvmt' is present but the DVMT 60MB DeviceProperties pair is missing (both keys required together).")

        # --- model ---
        if "model" in props and not isinstance(props.get("model"), str):
            errors.append("Invalid 'model' on {}: must be a String (descriptive label only).".format(pci_path))

        # --- Tiger Lake headless flag (needs hardware report) ---
        if hardware_report:
            for gpu_name, gpu_info in (hardware_report.get("GPU", {}) or {}).items():
                if gpu_info.get("Device Type") != "Integrated GPU":
                    continue
                dev = _xe.normalize_device_id(str(gpu_info.get("Device ID", "")))
                if dev in _xe.TIGER_LAKE_IDS:
                    internal = any(
                        m.get("Connected GPU") == gpu_name and m.get("Connector Type") == "Internal"
                        for m in (hardware_report.get("Monitor", {}) or {}).values())
                    if not internal and "-wex-nopanel" not in tokens:
                        errors.append("Missing boot-arg '-wex-nopanel': required on Tiger Lake systems without an internal display.")
                    break
            for gpu_name, gpu_info in (hardware_report.get("GPU", {}) or {}).items():
                dev = _xe.normalize_device_id(str(gpu_info.get("Device ID", "")))
                if dev in _xe.ALDER_LAKE_N_IDS and "-wex-nopanel" in tokens:
                    warnings.append("Boot-arg '-wex-nopanel' is Tiger Lake-only; Alder Lake-N builds external-display topology automatically and does not use this flag.")
                    break

        return len(errors) == 0, errors, warnings

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

        # WhateverXe DeviceProperties + boot-args validation (WhateverGreen-style, for Xe).
        # Hardware-agnostic part only here; pass hardware_report to
        # validate_whateverxe_device_properties() for headless/DVMT context checks.
        try:
            xe_valid, xe_errors, _xe_warnings = PlistValidator.validate_whateverxe_device_properties(config_data, None)
            errors.extend(xe_errors)
        except Exception:
            pass

        return len(errors) == 0, errors

    @classmethod
    def validate_plist_bytes(cls, raw_plist: bytes) -> Tuple[bool, List[str]]:
        try:
            data = plistlib.loads(raw_plist)
            return cls.validate_config(data)
        except Exception as e:
            return False, [f"Failed to parse plist format: {str(e)}"]
