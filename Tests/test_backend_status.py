import unittest
from Scripts.experimental_drivers.models.driver import BackendStatus, HardwareFamilySupport
from Scripts.experimental_drivers.compatibility.backend_status_checker import BackendStatusChecker

class TestBackendStatus(unittest.TestCase):
    def test_catalogued_is_not_implemented(self):
        # Alder Lake-H catalogued entry
        fam = HardwareFamilySupport(
            family="Alder Lake-H",
            supported_device_ids=["46A6"],
            backend_status=BackendStatus.CATALOGUED,
            acceleration_verified=False,
            evidence_url="https://github.com/b00t0x/WhateverXe",
        )
        self.assertFalse(BackendStatusChecker.is_backend_implemented(fam))
        self.assertFalse(BackendStatusChecker.is_acceleration_verified(fam))

    def test_implemented_backend_check(self):
        # Tiger Lake implemented entry
        fam = HardwareFamilySupport(
            family="Tiger Lake",
            supported_device_ids=["9A49"],
            backend_status=BackendStatus.BACKEND_IMPLEMENTED,
            acceleration_verified=True,
            evidence_url="https://github.com/b00t0x/WhateverXe",
        )
        self.assertTrue(BackendStatusChecker.is_backend_implemented(fam))
        self.assertTrue(BackendStatusChecker.is_acceleration_verified(fam))

    def test_status_descriptions(self):
        desc = BackendStatusChecker.get_status_description(BackendStatus.CATALOGUED)
        self.assertIn("NO driver backend is implemented", desc)

if __name__ == "__main__":
    unittest.main()
