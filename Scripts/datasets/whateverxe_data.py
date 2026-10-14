# WhateverXe DeviceProperties dataset.
# Source of truth: https://github.com/b00t0x/WhateverXe
#   - README.md (Configuration, DVMT, Required/Optional boot arguments)
#   - docs/device-selection.md (automatic selection + device-id override + display name)
#
# This module mirrors the WhateverGreen-style validation approach used in
# config_prodigy.igpu_properties(), but scoped strictly to WhateverXe rules:
# automatic PCI selection, VBT connector routing (no manual wiring props),
# DVMT 60MB pair, and a strict 4-byte little-endian device-id override.

IMPLEMENTED_BACKEND_IDS = (
    "9A40", "9A49", "9A78",          # Tiger Lake
    "46D0", "46D1", "46D2", "46D3", "46D4",  # Alder Lake-N / Twin Lake
)

TIGER_LAKE_IDS = ("9A40", "9A49", "9A78")

ALDER_LAKE_N_IDS = ("46D0", "46D1", "46D2", "46D3", "46D4")

# Identification-only / roadmap IDs known from the registry. A device-id
# override targeting these must be REJECTED (docs: identification-only
# targets are rejected, listed ID != implemented backend).
IDENTIFICATION_ONLY_IDS = (
    "46A6", "4626", "46A8", "4690", "4680", "4682",  # Alder Lake S/H/P/U (planned)
    "A780", "A781", "A782", "A783", "A7A0", "A7A8",  # Raptor Lake (planned)
)

DEFAULT_IGPU_PCI_PATH = "PciRoot(0x0)/Pci(0x2,0x0)"

# DVMT 60MB pair from README. Both must be present together as Data.
# framebuffer-patch-enable = 01000000, framebuffer-stolenmem = 0000C003
DVMT_60MB_PROPERTIES = {
    "framebuffer-patch-enable": "01000000",
    "framebuffer-stolenmem": "0000C003",
}

REQUIRED_BOOT_ARGS = ("-allow3d", "-disablegfxfirmware")

# -wex-nopanel is additionally required on Tiger Lake headless systems.
# Alder Lake-N builds external-display topology automatically (no flag).
CONDITIONAL_BOOT_ARGS = ("-wex-nopanel", "-igfxdvmt")

OPTIONAL_BOOT_ARGS = ("gfxrst=", "-wexdbg", "-wexoff", "-wexbeta", "-wex-tgl-off")

# WhateverGreen-style wiring / platform-id keys are NOT valid for Xe.
# README: connector routing is read from firmware VBT; fixed HDMI/DP layouts
# normally need no manual wiring properties. No family-selection or
# per-feature enable arguments required for Alder Lake-N.
FORBIDDEN_IGPU_KEYS_FOR_XE = (
    "AAPL,ig-platform-id",
    "AAPL,snb-platform-id",
    "AAPL00,DualLink",
    "framebuffer-con0-enable",
    "framebuffer-con1-enable",
    "framebuffer-con2-enable",
    "framebuffer-con0-alldata",
    "framebuffer-con1-alldata",
    "framebuffer-con2-alldata",
    "framebuffer-con0-type",
    "framebuffer-con1-type",
    "framebuffer-con2-type",
    "framebuffer-portcount",
    "framebuffer-pipecount",
    "framebuffer-memorycount",
    "framebuffer-fbmem",
    "framebuffer-cursormem",
    "framebuffer-unifiedmem",
    "framebuffer-singlelink",
    "enable-dbuf-early-optimizer",
    "enable-dvmt-calc-fix",
    "enable-cdclk-frequency-fix",
    "enable-max-pixel-clock-override",
    "enable-hdmi-dividers-fix",
    "enable-lspcon-support",
    "igfxonln",
    "-igfxblr",
    "-igfxblt",
    "-igfxvesa",
    "-cdfon",
)

# Only these keys may appear on the Xe iGPU node.
ALLOWED_IGPU_KEYS_FOR_XE = frozenset({
    "device-id",
    "model",
    "framebuffer-patch-enable",
    "framebuffer-stolenmem",
})


def encode_device_id_override(device_id_4hex):
    """Encode '46D2' -> 'D2460000' (Data hex string, little-endian + 0000).

    Returns uppercase hex string or None if input is not 4 hex chars.
    """
    if not device_id_4hex:
        return None
    s = str(device_id_4hex).strip().upper().lstrip("0X")
    if len(s) != 4:
        return None
    try:
        int(s, 16)
    except ValueError:
        return None
    return s[2:4] + s[0:2] + "0000"


def decode_device_id_override(data_bytes):
    """Decode 4-byte LE Data -> '46D2'. Returns None if malformed.

    Malformed = not exactly 4 bytes, or trailing bytes are not 00 00.
    """
    if data_bytes is None:
        return None
    if isinstance(data_bytes, str):
        # Hex string form (e.g. 'D2460000')
        s = "".join(c for c in data_bytes if c in "0123456789abcdefABCDEF")
        if len(s) != 8:
            return None
        try:
            raw = bytes.fromhex(s)
        except ValueError:
            return None
        data_bytes = raw
    if not isinstance(data_bytes, (bytes, bytearray)):
        return None
    if len(data_bytes) != 4:
        return None
    if data_bytes[2] != 0x00 or data_bytes[3] != 0x00:
        return None
    return "{:02X}{:02X}".format(data_bytes[1], data_bytes[0])


def normalize_device_id(short_id):
    """Normalize '9a49', '0x9A49', '8086-9A49' -> '9A49' (or '' if invalid)."""
    if not short_id:
        return ""
    s = str(short_id).strip().upper()
    if "-" in s:
        s = s.split("-")[-1]
    s = s.replace("0X", "")
    s = "".join(c for c in s if c in "0123456789ABCDEF")
    if len(s) > 4:
        s = s[-4:]
    return s


def validate_device_id_override(override_value, physical_device_id, physical_vendor_id="8086"):
    """Validate a device-id override per docs/device-selection.md.

    Args:
        override_value: bytes (Data), hex string, or None (automatic selection).
        physical_device_id: e.g. '46A6' or '8086-46A6'.
        physical_vendor_id: e.g. '8086'.

    Returns:
        (is_valid, target_id_or_None, error_or_None, warnings_list)
        - override None -> (True, None, None, []) meaning automatic selection.
        - invalid override NEVER falls back to physical ID (per docs).
    """
    warnings = []
    physical = normalize_device_id(physical_device_id)
    vendor = str(physical_vendor_id or "").strip().upper()

    if override_value is None:
        return True, None, None, warnings

    # Physical device must be Intel.
    if vendor and vendor != "8086":
        return False, None, "device-id override rejected: physical device is not Intel (vendor {}).".format(vendor or "?"), warnings

    if isinstance(override_value, (bytes, bytearray)):
        raw = bytes(override_value)
    elif isinstance(override_value, str):
        s = "".join(c for c in override_value if c in "0123456789abcdefABCDEF")
        if len(s) != 8:
            return False, None, "device-id override malformed: Data must contain exactly four little-endian bytes (e.g. D2460000 for 0x46D2).", warnings
        try:
            raw = bytes.fromhex(s)
        except ValueError:
            return False, None, "device-id override malformed: Data must contain exactly four little-endian bytes (e.g. D2460000 for 0x46D2).", warnings
    else:
        return False, None, "device-id override malformed: Data must contain exactly four little-endian bytes (e.g. D2460000 for 0x46D2).", warnings

    if len(raw) != 4:
        return False, None, "device-id override malformed: Data must contain exactly four little-endian bytes (e.g. D2460000 for 0x46D2).", warnings
    if raw[2] != 0x00 or raw[3] != 0x00:
        return False, None, "device-id override malformed: upper two bytes must be 00 00 (16-bit ID + two zero bytes).", warnings

    target = "{:02X}{:02X}".format(raw[1], raw[0])

    if target in ("0000", "FFFF"):
        return False, None, "device-id override rejected: zero/FFFF target is not allowed.", warnings
    if target in IDENTIFICATION_ONLY_IDS:
        return False, None, "device-id override rejected: target 0x{} is identification-only (no implemented backend).".format(target), warnings
    if target not in IMPLEMENTED_BACKEND_IDS:
        return False, None, "device-id override rejected: unknown target ID 0x{} (implemented backends: {}).".format(target, ", ".join(IMPLEMENTED_BACKEND_IDS)), warnings

    if physical and target == physical:
        warnings.append("device-id override 0x{} equals the physical ID; override is unnecessary (automatic selection already selects this backend).".format(target))

    return True, target, None, warnings
