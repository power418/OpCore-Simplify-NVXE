import unittest
from Scripts.experimental_drivers.models.hardware_profile import (
    HardwareProfile,
    PCIDevice,
    GPUClassification,
    DisplayInfo,
)
from Scripts.experimental_drivers.compatibility.compatibility_engine import CompatibilityEngine
from Scripts.experimental_drivers.models.driver import (
    BackendStatus,
    CompatibilityOutcome,
)

class TestHPVictusProfile(unittest.TestCase):
    def setUp(self):
        self.engine = CompatibilityEngine()

        # Fixture for HP Victus 15 (i5-12500H, Iris Xe + RTX 3050 Mobile, macOS 15 Sequoia)
        self.iris_xe = PCIDevice(
            vendor_id="8086",
            device_id="46A6",
            name="Intel Iris Xe Graphics (Alder Lake-H)",
            codename="Alder Lake-H",
            classification=GPUClassification.INTEGRATED,
            acpi_path="\\_SB.PC00.GFX0",
            pci_path="PciRoot(0x0)/Pci(0x2,0x0)",
        )
        self.rtx_3050 = PCIDevice(
            vendor_id="10DE",
            device_id="25A0",
            name="NVIDIA GeForce RTX 3050 Mobile",
            codename="GA107M (Ampere)",
            classification=GPUClassification.DISCRETE,
            acpi_path="\\_SB.PC00.PEG0.PEGP",
            pci_path="PciRoot(0x0)/Pci(0x1,0x0)/Pci(0x0,0x0)",
        )
        self.victus_profile = HardwareProfile(
            platform="Laptop",
            motherboard_name="HP Victus 15-fa0xxx",
            chipset="Intel 600 Series Chipset",
            cpu_name="12th Gen Intel(R) Core(TM) i5-12500H",
            cpu_codename="Alder Lake-H",
            gpus=[self.iris_xe, self.rtx_3050],
            displays=[DisplayInfo(name="Internal Screen", connector_type="Internal", connected_gpu=self.iris_xe.name)],
            bios_type="UEFI",
            secure_boot="Disabled",
            target_macos_version="24.1.0",  # macOS 15 Sequoia
        )

    def test_hp_victus_iris_xe_conservative_evaluation(self):
        # Intel Iris Xe Alder Lake-H evaluation
        report = self.engine.evaluate_profile(self.victus_profile, target_macos_version="24.1.0")

        xe_items = [i for i in report.items if i.driver_id == "whateverxe"]
        self.assertEqual(len(xe_items), 1)
        item = xe_items[0]

        # PRD requirement: must NOT label Alder Lake-H acceleration as supported
        self.assertEqual(item.backend_status, BackendStatus.CATALOGUED)
        self.assertFalse(item.acceleration_verified)

        # macOS Sequoia (24.x) is outside WhateverXe's Big Sur target
        self.assertEqual(item.outcome, CompatibilityOutcome.EXPERIMENTAL)
        self.assertTrue(item.manual_review_required)

        # Dimension checks verification
        backend_dim = [d for d in item.dimensions if "Backend Implementation" in d.dimension_name][0]
        self.assertFalse(backend_dim.passed)
        self.assertIn("catalogued", backend_dim.summary.lower())

    def test_hp_victus_rtx_3050_mobile_conservative_evaluation(self):
        # NVIDIA RTX 3050 Mobile evaluation
        report = self.engine.evaluate_profile(self.victus_profile, target_macos_version="24.1.0")

        nv_items = [i for i in report.items if i.driver_id == "nvidia-macos-driver"]
        self.assertEqual(len(nv_items), 1)
        item = nv_items[0]

        # PRD requirement: RTX 3050 Mobile is catalogued, not physical acceleration verified
        self.assertEqual(item.backend_status, BackendStatus.CATALOGUED)
        self.assertFalse(item.acceleration_verified)
        self.assertEqual(item.outcome, CompatibilityOutcome.EXPERIMENTAL)
        self.assertTrue(item.manual_review_required)

        # PRD requirement: Laptop Optimus limitations must be flagged in warnings
        self.assertTrue(any("Optimus" in w for w in item.warnings))

if __name__ == "__main__":
    unittest.main()
