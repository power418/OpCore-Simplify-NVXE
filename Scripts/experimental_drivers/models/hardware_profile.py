# Hardware profile models for detected PCI devices and system information
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

class GPUClassification(str, Enum):
    INTEGRATED = "Integrated"
    DISCRETE = "Discrete"
    EXTERNAL = "External"
    UNKNOWN = "Unknown"

@dataclass
class PCIDevice:
    vendor_id: str  # e.g. '8086' or '10DE'
    device_id: str  # e.g. '46A6' or '25A0'
    name: str = ""
    subsystem_vendor_id: Optional[str] = None
    subsystem_device_id: Optional[str] = None
    acpi_path: Optional[str] = None
    pci_path: Optional[str] = None
    codename: Optional[str] = None
    manufacturer: Optional[str] = None
    classification: GPUClassification = GPUClassification.UNKNOWN
    raw_properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def formatted_id(self) -> str:
        """Returns standard VENDOR-DEVICE uppercase identifier, e.g. '8086-46A6'."""
        v = (self.vendor_id or "").upper().strip()
        d = (self.device_id or "").upper().strip()
        return f"{v}-{d}"

    @property
    def short_device_id(self) -> str:
        """Returns 4-char uppercase device id."""
        return (self.device_id or "").upper().strip()

@dataclass
class DisplayInfo:
    name: str
    connector_type: str  # e.g. 'Internal', 'HDMI', 'DisplayPort', 'VGA'
    connected_gpu: Optional[str] = None
    resolution: Optional[str] = None

@dataclass
class HardwareProfile:
    platform: str = "Desktop"  # 'Laptop' or 'Desktop'
    motherboard_name: str = ""
    chipset: str = ""
    cpu_name: str = ""
    cpu_codename: str = ""
    cpu_simd: List[str] = field(default_factory=list)
    gpus: List[PCIDevice] = field(default_factory=list)
    displays: List[DisplayInfo] = field(default_factory=list)
    bios_type: str = "UEFI"
    secure_boot: str = "Disabled"
    target_macos_version: Optional[str] = None
    target_macos_build: Optional[str] = None

    def get_integrated_gpu(self) -> Optional[PCIDevice]:
        for gpu in self.gpus:
            if gpu.classification == GPUClassification.INTEGRATED:
                return gpu
        return None

    def get_discrete_gpu(self) -> Optional[PCIDevice]:
        for gpu in self.gpus:
            if gpu.classification == GPUClassification.DISCRETE:
                return gpu
        return None
