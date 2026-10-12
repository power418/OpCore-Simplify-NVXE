import unittest
from Scripts.experimental_drivers.models.hardware_profile import HardwareProfile, PCIDevice, GPUClassification
from Scripts.experimental_drivers.planning.installation_planner import InstallationPlanner
from Scripts.experimental_drivers.compatibility.compatibility_engine import CompatibilityEngine
from Scripts.experimental_drivers.models.install_manifest import FileAction

class TestInstallationPlanner(unittest.TestCase):
    def setUp(self):
        self.engine = CompatibilityEngine()
        self.planner = InstallationPlanner()

    def test_dry_run_whateverxe_plan(self):
        tgl_gpu = PCIDevice(vendor_id="8086", device_id="9A49", name="Intel Iris Xe (Tiger Lake)", classification=GPUClassification.INTEGRATED)
        profile = HardwareProfile(platform="Desktop", gpus=[tgl_gpu])

        report = self.engine.evaluate_profile(profile, target_macos_version="20.6.0")
        plan = self.planner.create_plan(
            report=report,
            profile=profile,
            selected_driver_ids=["whateverxe"],
            active_kexts=["WhateverGreen"]
        )

        self.assertTrue(plan.is_validated)
        self.assertIn("whateverxe", plan.driver_ids)

        # Verify WhateverGreen is disabled
        cfg_change_wg = [c for c in plan.config_changes if "WhateverGreen" in c.key_path]
        self.assertEqual(len(cfg_change_wg), 1)
        self.assertFalse(cfg_change_wg[0].new_value)

        # Verify WhateverXe kext file op
        kext_ops = [op for op in plan.file_operations if "WhateverXe.kext" in op.destination_path]
        self.assertEqual(len(kext_ops), 1)
        self.assertEqual(kext_ops[0].action, FileAction.CREATE)

    def test_dry_run_nvidia_external_isolation(self):
        # Test case 6: NVIDIA package requires external installer, must not touch EFI/OC/Kexts
        rtx_gpu = PCIDevice(vendor_id="10DE", device_id="2882", name="GeForce RTX 5060", classification=GPUClassification.DISCRETE)
        profile = HardwareProfile(platform="Desktop", gpus=[rtx_gpu])

        report = self.engine.evaluate_profile(profile, target_macos_version="24.1.0")
        plan = self.planner.create_plan(
            report=report,
            profile=profile,
            selected_driver_ids=["nvidia-macos-driver"],
        )

        self.assertTrue(plan.is_validated)
        # Verify no kext created in EFI/OC/Kexts
        efi_kexts = [op for op in plan.file_operations if "EFI/OC/Kexts" in op.destination_path]
        self.assertEqual(len(efi_kexts), 0)

        # Verify external action is generated
        self.assertTrue(len(plan.external_actions) >= 1)
        self.assertTrue(plan.external_actions[0].requires_root)

if __name__ == "__main__":
    unittest.main()
