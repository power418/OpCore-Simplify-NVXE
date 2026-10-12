# DriverRegistry: Central repository for experimental driver packages
from typing import Dict, List, Optional, Tuple, Any
import json
from ..models.driver import (
    DriverDefinition,
    DriverRelease,
    HardwareFamilySupport,
    BackendStatus,
)
from .sources import CANONICAL_DRIVERS

class DriverRegistry:
    def __init__(self, load_defaults: bool = True):
        self._drivers: Dict[str, DriverDefinition] = {}
        if load_defaults:
            for d in CANONICAL_DRIVERS.values():
                self.register_driver(d)

    def register_driver(self, driver: DriverDefinition) -> None:
        if not driver.id:
            raise ValueError("Driver definition must possess a non-empty unique identifier.")
        self._drivers[driver.id.lower()] = driver

    def get_driver(self, driver_id: str) -> Optional[DriverDefinition]:
        if not driver_id:
            return None
        return self._drivers.get(driver_id.lower())

    def list_drivers(self) -> List[DriverDefinition]:
        return list(self._drivers.values())

    def find_drivers_for_device(self, vendor_id: str, device_id: str) -> List[Tuple[DriverDefinition, HardwareFamilySupport]]:
        """Finds any registered drivers matching the given vendor and device ID."""
        matches: List[Tuple[DriverDefinition, HardwareFamilySupport]] = []
        clean_dev = (device_id or "").upper().strip()
        clean_ven = (vendor_id or "").upper().strip()

        for driver in self._drivers.values():
            # Check vendor compatibility
            if driver.category == "intel-graphics" and clean_ven != "8086":
                continue
            if driver.category == "nvidia-graphics" and clean_ven != "10DE":
                continue

            for family in driver.hardware_families:
                upper_supported = [d.upper().strip() for d in family.supported_device_ids]
                if clean_dev in upper_supported:
                    matches.append((driver, family))

        return matches

    def pin_driver_version(self, driver_id: str, release: DriverRelease) -> bool:
        driver = self.get_driver(driver_id)
        if not driver:
            return False
        driver.pinned_release = release
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            driver_id: driver.to_dict()
            for driver_id, driver in self._drivers.items()
        }

    def export_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
