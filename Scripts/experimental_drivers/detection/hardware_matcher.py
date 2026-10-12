# HardwareMatcher: Matches detected hardware devices to driver definitions and families
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from ..models.hardware_profile import PCIDevice, HardwareProfile
from ..models.driver import DriverDefinition, HardwareFamilySupport, BackendStatus
from ..registry.driver_registry import DriverRegistry

@dataclass
class DriverMatch:
    device: PCIDevice
    driver: DriverDefinition
    family: HardwareFamilySupport
    is_direct_pci_match: bool
    notes: str = ""

class HardwareMatcher:
    def __init__(self, registry: Optional[DriverRegistry] = None):
        self.registry = registry or DriverRegistry()

    def match_device(self, device: PCIDevice) -> List[DriverMatch]:
        matches: List[DriverMatch] = []
        clean_dev = device.short_device_id
        clean_ven = (device.vendor_id or "").upper().strip()

        for driver in self.registry.list_drivers():
            # Filter by vendor
            if driver.category == "intel-graphics" and clean_ven != "8086":
                continue
            if driver.category == "nvidia-graphics" and clean_ven != "10DE":
                continue

            # First: check direct PCI Device ID match
            for family in driver.hardware_families:
                supported_ids = [d.upper().strip() for d in family.supported_device_ids]
                if clean_dev in supported_ids:
                    matches.append(DriverMatch(
                        device=device,
                        driver=driver,
                        family=family,
                        is_direct_pci_match=True,
                        notes=family.notes,
                    ))
                    break
            else:
                # Second: check codename match if not matched by ID
                if device.codename:
                    for family in driver.hardware_families:
                        if device.codename.lower() in family.family.lower():
                            matches.append(DriverMatch(
                                device=device,
                                driver=driver,
                                family=family,
                                is_direct_pci_match=False,
                                notes=f"Matched by GPU architecture '{device.codename}', but Device ID '{clean_dev}' is not explicitly listed.",
                            ))
                            break

        return matches

    def match_profile(self, profile: HardwareProfile) -> List[DriverMatch]:
        all_matches: List[DriverMatch] = []
        for gpu in profile.gpus:
            all_matches.extend(self.match_device(gpu))
        return all_matches
