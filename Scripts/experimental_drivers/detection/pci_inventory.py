# PCI Inventory parser converting Report.json into HardwareProfile models
from typing import Dict, List, Optional, Any
import re
from ..models.hardware_profile import (
    PCIDevice,
    GPUClassification,
    DisplayInfo,
    HardwareProfile,
)

class PCIInventory:
    @staticmethod
    def parse_device_id_string(raw_id: str) -> tuple[str, str]:
        """Parses vendor and device id from various report formats.
        Examples:
          '8086-46A6' -> ('8086', '46A6')
          'PCI\\VEN_10DE&DEV_25A0&...' -> ('10DE', '25A0')
          '10DE-25A0' -> ('10DE', '25A0')
        """
        if not raw_id:
            return ("", "")

        raw = raw_id.upper()

        # Handle PCI\\VEN_xxxx&DEV_yyyy format
        ven_match = re.search(r"VEN_([0-9A-F]{4})", raw)
        dev_match = re.search(r"DEV_([0-9A-F]{4})", raw)
        if ven_match and dev_match:
            return (ven_match.group(1), dev_match.group(1))

        # Handle 'XXXX-YYYY' format
        if "-" in raw:
            parts = raw.split("-")
            if len(parts) >= 2:
                return (parts[0][-4:], parts[1][:4])

        return ("", "")

    @classmethod
    def parse_hardware_report(cls, report_data: Dict[str, Any], target_macos_version: Optional[str] = None, target_macos_build: Optional[str] = None) -> HardwareProfile:
        if not isinstance(report_data, dict):
            return HardwareProfile()

        motherboard = report_data.get("Motherboard", {})
        cpu = report_data.get("CPU", {})
        bios = report_data.get("BIOS", {})

        profile = HardwareProfile(
            platform=motherboard.get("Platform", "Desktop"),
            motherboard_name=motherboard.get("Name", "Generic System"),
            chipset=motherboard.get("Chipset", ""),
            cpu_name=cpu.get("Processor Name", "Generic CPU"),
            cpu_codename=cpu.get("Codename", ""),
            cpu_simd=cpu.get("SIMD Features", []),
            bios_type=bios.get("Firmware Type", "UEFI"),
            secure_boot=bios.get("Secure Boot", "Disabled"),
            target_macos_version=target_macos_version,
            target_macos_build=target_macos_build,
        )

        # Parse GPUs
        raw_gpus = report_data.get("GPU", {})
        for gpu_name, gpu_props in raw_gpus.items():
            raw_id = gpu_props.get("Device ID", "")
            ven, dev = cls.parse_device_id_string(raw_id)
            if not ven or not dev:
                continue

            sub_ven = None
            sub_dev = None
            sub_id = gpu_props.get("Subsystem ID")
            if sub_id:
                sub_ven, sub_dev = cls.parse_device_id_string(sub_id)

            dev_type = gpu_props.get("Device Type", "")
            if "Integrated" in dev_type:
                classification = GPUClassification.INTEGRATED
            elif "Discrete" in dev_type:
                classification = GPUClassification.DISCRETE
            else:
                classification = GPUClassification.UNKNOWN

            pci_dev = PCIDevice(
                vendor_id=ven,
                device_id=dev,
                name=gpu_name,
                subsystem_vendor_id=sub_ven,
                subsystem_device_id=sub_dev,
                acpi_path=gpu_props.get("ACPI Path"),
                pci_path=gpu_props.get("PCI Path"),
                codename=gpu_props.get("Codename"),
                manufacturer=gpu_props.get("Manufacturer"),
                classification=classification,
                raw_properties=gpu_props,
            )
            profile.gpus.append(pci_dev)

        # Parse Displays
        raw_monitors = report_data.get("Monitor", {})
        for mon_name, mon_props in raw_monitors.items():
            disp = DisplayInfo(
                name=mon_name,
                connector_type=mon_props.get("Connector Type", "Unknown"),
                connected_gpu=mon_props.get("Connected GPU"),
                resolution=mon_props.get("Resolution"),
            )
            profile.displays.append(disp)

        return profile
