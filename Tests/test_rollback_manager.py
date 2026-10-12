import unittest
import os
import shutil
import tempfile
from Scripts.experimental_drivers.rollback.rollback_manager import RollbackManager
from Scripts.experimental_drivers.models.install_manifest import InstallPlan, FileOperation, FileAction

class TestRollbackManager(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.efi_dir = os.path.join(self.test_dir, "EFI")
        self.rollback_dir = os.path.join(self.test_dir, "rollback")
        os.makedirs(os.path.join(self.efi_dir, "OC", "Kexts"), exist_ok=True)

        # Create original user files
        with open(os.path.join(self.efi_dir, "OC", "config.plist"), "w") as f:
            f.write("<plist>ORIGINAL_USER_CONFIG</plist>")
        with open(os.path.join(self.efi_dir, "OC", "Kexts", "VirtualSMC.kext"), "w") as f:
            f.write("user_kext")

        self.manager = RollbackManager(storage_dir=self.rollback_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_backup_and_rollback(self):
        # 1. Create backup
        backup_path = self.manager.create_backup(self.efi_dir)
        self.assertTrue(os.path.exists(backup_path))

        # 2. Simulate partial/complete apply of experimental driver
        plan = InstallPlan(
            plan_id="test_plan",
            created_at="2026-10-12T00:00:00Z",
            driver_ids=["whateverxe"],
            file_operations=[
                FileOperation(action=FileAction.CREATE, destination_path="EFI/OC/Kexts/WhateverXe.kext"),
                FileOperation(action=FileAction.CREATE, destination_path="EFI/OC/Kexts/AMFIPass.kext"),
            ],
        )
        manifest = self.manager.record_manifest(plan, backup_path)

        # Mutate target EFI
        with open(os.path.join(self.efi_dir, "OC", "config.plist"), "w") as f:
            f.write("<plist>MUTATED_EXPERIMENTAL_CONFIG</plist>")
        with open(os.path.join(self.efi_dir, "OC", "Kexts", "WhateverXe.kext"), "w") as f:
            f.write("experimental_kext")

        # 3. Execute rollback (PRD test case 8)
        success, logs = self.manager.execute_rollback(manifest, self.efi_dir)
        self.assertTrue(success)

        # Check: WhateverXe is removed
        self.assertFalse(os.path.exists(os.path.join(self.efi_dir, "OC", "Kexts", "WhateverXe.kext")))

        # Check: Unrelated user kext VirtualSMC is PRESERVED
        self.assertTrue(os.path.exists(os.path.join(self.efi_dir, "OC", "Kexts", "VirtualSMC.kext")))

        # Check: Original config.plist is restored
        with open(os.path.join(self.efi_dir, "OC", "config.plist"), "r") as f:
            content = f.read()
        self.assertIn("ORIGINAL_USER_CONFIG", content)

if __name__ == "__main__":
    unittest.main()
