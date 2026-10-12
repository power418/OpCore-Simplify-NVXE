import unittest
from Scripts.experimental_drivers.integration.opencore_integrator import OpenCoreIntegrator
from Scripts.experimental_drivers.validation.plist_validator import PlistValidator
from Scripts.experimental_drivers.models.install_manifest import ConfigChange

class TestOpenCoreIntegrator(unittest.TestCase):
    def test_boot_args_append_no_duplicates(self):
        initial = "-v debug=0x100 keepsyms=1 nvfb=0"
        new_args = ["-allow3d", "-disablegfxfirmware", "debug=0x100", "nvfb=1"]

        res = OpenCoreIntegrator.append_boot_args(initial, new_args)
        self.assertIn("-allow3d", res)
        self.assertIn("-disablegfxfirmware", res)
        self.assertIn("nvfb=1", res)
        self.assertNotIn("nvfb=0", res)
        # Verify debug=0x100 appears only once
        self.assertEqual(res.count("debug=0x100"), 1)

    def test_apply_config_changes(self):
        sample_config = {
            "ACPI": {"Add": []},
            "Booter": {"Quirks": {"ResizeAppleGpuBars": 0}},
            "DeviceProperties": {"Add": {}},
            "Kernel": {
                "Add": [{"BundlePath": "WhateverGreen.kext", "Enabled": True}],
                "Block": [],
                "Quirks": {}
            },
            "Misc": {"Security": {"SecureBootModel": "Default"}},
            "NVRAM": {
                "Add": {
                    "7C436110-AB2A-4BBB-A880-FE41995C9F82": {
                        "boot-args": "-v",
                        "csr-active-config": b"\x00\x00\x00\x00"
                    }
                }
            },
            "PlatformInfo": {},
            "UEFI": {"Quirks": {"ResizeGpuBars": 0}}
        }

        changes = [
            ConfigChange(key_path="NVRAM/Add/.../boot-args", old_value="", new_value="-allow3d -disablegfxfirmware"),
            ConfigChange(key_path="NVRAM/Add/.../csr-active-config", old_value="", new_value="430A0000"),
            ConfigChange(key_path="Booter/Quirks/ResizeAppleGpuBars", old_value=0, new_value=-1),
            ConfigChange(key_path="UEFI/Quirks/ResizeGpuBars", old_value=0, new_value=13),
            ConfigChange(key_path="Kernel/Block/IONDRVSupport", old_value=None, new_value=""),
            ConfigChange(key_path="Kernel/Add/WhateverGreen/Enabled", old_value=True, new_value=False),
            ConfigChange(key_path="Kernel/Add/WhateverXe.kext", old_value=None, new_value=""),
        ]

        updated = OpenCoreIntegrator.apply_config_changes(sample_config, changes)

        # Assertions
        nvram_sec = updated["NVRAM"]["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]
        self.assertIn("-allow3d", nvram_sec["boot-args"])
        self.assertEqual(updated["Booter"]["Quirks"]["ResizeAppleGpuBars"], -1)
        self.assertEqual(updated["UEFI"]["Quirks"]["ResizeGpuBars"], 13)

        # WhateverGreen is disabled
        wg = [k for k in updated["Kernel"]["Add"] if "WhateverGreen" in k["BundlePath"]][0]
        self.assertFalse(wg["Enabled"])

        # WhateverXe is enabled
        wxe = [k for k in updated["Kernel"]["Add"] if "WhateverXe" in k["BundlePath"]][0]
        self.assertTrue(wxe["Enabled"])

        # Validates without conflict error
        is_valid, errs = PlistValidator.validate_config(updated)
        self.assertTrue(is_valid, f"Validation failed with: {errs}")

    def test_plist_validator_catches_simultaneous_gpu_kext_conflict(self):
        # PRD test case 7: Validation catches illegal config
        bad_config = {
            "ACPI": {}, "Booter": {}, "DeviceProperties": {}, "Misc": {}, "NVRAM": {}, "PlatformInfo": {}, "UEFI": {},
            "Kernel": {
                "Add": [
                    {"BundlePath": "WhateverGreen.kext", "Enabled": True},
                    {"BundlePath": "WhateverXe.kext", "Enabled": True},
                ]
            }
        }
        is_valid, errs = PlistValidator.validate_config(bad_config)
        self.assertFalse(is_valid)
        self.assertTrue(any("both enabled" in e for e in errs))

if __name__ == "__main__":
    unittest.main()
