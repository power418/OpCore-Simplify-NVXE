import unittest
from Scripts.experimental_drivers.registry.sources import WHATEVERXE_DEFINITION, NVIDIA_MACOS_DRIVER_DEFINITION
from Scripts.experimental_drivers.planning.dependency_resolver import DependencyResolver

class TestConflictAndDependencies(unittest.TestCase):
    def test_whatevergreen_conflict_detected_and_disabled(self):
        # Test case 3: WhateverXe selected with WhateverGreen active
        selected = [WHATEVERXE_DEFINITION]
        active = ["Lilu", "VirtualSMC", "WhateverGreen"]

        to_disable, blocking = DependencyResolver.resolve_conflicts(selected, active)
        self.assertIn("WhateverGreen", to_disable)
        self.assertEqual(len(blocking), 0)

    def test_both_experimental_drivers_simultaneous(self):
        # Test case 10: Both WhateverXe and NVIDIA driver selected
        selected = [WHATEVERXE_DEFINITION, NVIDIA_MACOS_DRIVER_DEFINITION]
        active = ["Lilu", "VirtualSMC", "WhateverGreen"]

        to_disable, blocking = DependencyResolver.resolve_conflicts(selected, active)
        self.assertIn("WhateverGreen", to_disable)

        deps = DependencyResolver.resolve_dependencies(selected)
        self.assertIn("Lilu", deps)
        self.assertIn("AMFIPass-Mod", deps)
        self.assertIn("NVIDIA-GSP-Firmware", deps)

if __name__ == "__main__":
    unittest.main()
