import unittest
from Scripts.experimental_drivers.models.hardware_profile import PCIDevice, GPUClassification
from Scripts.experimental_drivers.detection.pci_inventory import PCIInventory
from Scripts.experimental_drivers.detection.hardware_matcher import HardwareMatcher
from Scripts.experimental_drivers.registry.driver_registry import DriverRegistry

class TestPCIMatching(unittest.TestCase):
    def setUp(self):
        self.registry = DriverRegistry()
        self.matcher = HardwareMatcher(self.registry)

    def test_parse_device_id_string(self):
        v1, d1 = PCIInventory.parse_device_id_string("8086-46A6")
        self.assertEqual(v1, "8086")
        self.assertEqual(d1, "46A6")

        v2, d2 = PCIInventory.parse_device_id_string("PCI\\VEN_10DE&DEV_25A0&SUBSYS_1234")
        self.assertEqual(v2, "10DE")
        self.assertEqual(d2, "25A0")

    def test_tiger_lake_match(self):
        # Tiger Lake 9A49 in WhateverXe
        tgl = PCIDevice(vendor_id="8086", device_id="9A49", name="Intel Iris Xe Graphics (TGL)", classification=GPUClassification.INTEGRATED)
        matches = self.matcher.match_device(tgl)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].driver.id, "whateverxe")
        self.assertEqual(matches[0].family.family, "Tiger Lake")
        self.assertTrue(matches[0].is_direct_pci_match)

    def test_alder_lake_n_match(self):
        # Alder Lake-N 46D1 in WhateverXe
        aln = PCIDevice(vendor_id="8086", device_id="46D1", name="Intel UHD Graphics (N100)", classification=GPUClassification.INTEGRATED)
        matches = self.matcher.match_device(aln)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].family.family, "Alder Lake-N / Twin Lake")
        self.assertTrue(matches[0].is_direct_pci_match)

    def test_nvidia_rtx3050_mobile_match(self):
        # RTX 3050 Mobile 25A0
        rtx = PCIDevice(vendor_id="10DE", device_id="25A0", name="GeForce RTX 3050 Mobile", classification=GPUClassification.DISCRETE)
        matches = self.matcher.match_device(rtx)
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].driver.id, "nvidia-macos-driver")
        self.assertEqual(matches[0].family.family, "GeForce RTX 3050 Mobile / Ampere Mobile")
        self.assertTrue(matches[0].is_direct_pci_match)

if __name__ == "__main__":
    unittest.main()
