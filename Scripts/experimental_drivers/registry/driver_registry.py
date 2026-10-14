# DriverRegistry: Central repository for experimental driver packages
from typing import Dict, List, Optional, Tuple, Any
import json
from ..models.driver import (
    DriverDefinition,
    DriverRelease,
    HardwareFamilySupport,
    BackendStatus,
    VersionPolicy,
)
from .sources import CANONICAL_DRIVERS
from .release_fetcher import LiveReleaseFetcher

class DriverRegistry:
    def __init__(self, load_defaults: bool = True):
        self._drivers: Dict[str, DriverDefinition] = {}
        self.fetcher = LiveReleaseFetcher()
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

    def update_to_latest(self, driver_id: str) -> Tuple[bool, Optional[DriverRelease], str]:
        """Queries upstream repository dynamically and updates driver to the latest release."""
        driver = self.get_driver(driver_id)
        if not driver:
            return False, None, f"Driver '{driver_id}' not found."

        latest_rel = self.fetcher.fetch_latest_release(driver.repository)
        if not latest_rel:
            return False, driver.pinned_release, f"Could not fetch latest release for {driver.name} from upstream. Keeping existing release."

        old_tag = driver.pinned_release.tag if driver.pinned_release else "None"
        driver.pinned_release = latest_rel
        msg = f"Updated {driver.name} from {old_tag} to latest release {latest_rel.tag}."
        return True, latest_rel, msg

    def update_all_drivers_to_latest(self) -> Dict[str, Tuple[bool, Optional[DriverRelease], str]]:
        results = {}
        for d in self.list_drivers():
            results[d.id] = self.update_to_latest(d.id)
        return results

    def to_dict(self) -> Dict[str, Any]:
        return {
            driver_id: driver.to_dict()
            for driver_id, driver in self._drivers.items()
        }

    def export_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
