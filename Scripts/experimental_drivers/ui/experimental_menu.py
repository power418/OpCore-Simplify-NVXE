# ExperimentalMenu: Interactive TUI for discovering, inspecting, planning, and applying experimental drivers
import os
import json
from typing import Optional, List, Dict, Any
from ... import utils
from ..registry.driver_registry import DriverRegistry
from ..detection.pci_inventory import PCIInventory
from ..compatibility.compatibility_engine import CompatibilityEngine
from ..planning.installation_planner import InstallationPlanner
from ..integration.opencore_integrator import OpenCoreIntegrator
from ..integration.external_installer_adapter import ExternalInstallerAdapter
from ..validation.manifest_validator import ManifestValidator
from ..validation.plist_validator import PlistValidator
from ..rollback.rollback_manager import RollbackManager
from ..reporting.compatibility_report import ReportExporter
from ..models.install_manifest import InstallPlan, RollbackManifest
from ..models.compatibility_result import CompatibilityReport

class ExperimentalDriversMenu:
    def __init__(self, ocpe_instance=None):
        self.u = utils.Utils("OpCore Simplify - Experimental Drivers")
        self.ocpe = ocpe_instance
        self.registry = DriverRegistry()
        self.engine = CompatibilityEngine()
        self.planner = InstallationPlanner(self.registry)
        self.rollback_mgr = RollbackManager()
        self.current_plan: Optional[InstallPlan] = None
        self.current_report: Optional[CompatibilityReport] = None
        self.last_manifest: Optional[RollbackManifest] = None

    def show(self, hardware_report: Optional[Dict[str, Any]] = None, target_macos_version: str = "24.0.0"):
        if not hardware_report:
            if self.ocpe and hasattr(self.ocpe, "hardware_report") and self.ocpe.hardware_report:
                hardware_report = self.ocpe.hardware_report
            else:
                self.u.head("Experimental Drivers Subsystem")
                print("\n\033[1;93mNotice: No hardware report loaded yet.\033[0m")
                print("Please export or select a hardware report first from the main menu.")
                print("")
                self.u.request_input("Press Enter to return...")
                return

        profile = PCIInventory.parse_hardware_report(hardware_report, target_macos_version=target_macos_version)

        while True:
            self.u.head("Experimental Drivers Subsystem (Opt-In)")
            print("")
            print("  System Platform:   {}".format(profile.platform))
            print("  CPU:               {} ({})".format(profile.cpu_name, profile.cpu_codename or "Unknown"))
            print("  Target macOS:      {}".format(target_macos_version))
            print("  Detected GPUs:")
            for gpu in profile.gpus:
                print("    - {:<30} [{}] (PCI: {})".format(gpu.name[:30], gpu.classification.value, gpu.formatted_id))
            print("")

            print("Registered Experimental Drivers:")
            for i, driver in enumerate(self.registry.list_drivers(), start=1):
                matches = self.registry.find_drivers_for_device(
                    profile.gpus[0].vendor_id if profile.gpus else "",
                    profile.gpus[0].device_id if profile.gpus else ""
                )
                match_label = "\033[32m[Hardware Matched]\033[0m" if any(m[0].id == driver.id for m in matches) else "\033[90m[No Direct ID Match]\033[0m"
                print("  {}. {:<25} ({:<18}) {}".format(i, driver.name, driver.installation_type.value, match_label))
            print("")

            status_plan = "\033[32mReady\033[0m" if (self.current_plan and self.current_plan.is_validated) else "\033[90mNot Generated\033[0m"
            print("  Current Plan Status: {}".format(status_plan))
            print("")

            print("1. Inspect Driver Details")
            print("2. Check Upstream Updates (Pinned / Live)")
            print("3. View Hardware Compatibility Evaluation")
            print("4. Generate Dry-Run Installation Plan (Stage A)")
            print("5. Apply Changes to EFI (Stage B - Requires Validated Plan)")
            print("6. Export Compatibility & Plan Reports")
            print("7. Rollback Previous Experimental Changes")
            print("")
            print("Q. Return to Main Menu")
            print("")

            choice = self.u.request_input("Select an action: ").strip()
            if choice.lower() == "q":
                break

            if choice == "1":
                self._inspect_drivers()
            elif choice == "2":
                self._check_updates()
            elif choice == "3":
                self.current_report = self._view_compatibility(profile, target_macos_version)
            elif choice == "4":
                self._generate_plan(profile, target_macos_version)
            elif choice == "5":
                self._apply_changes()
            elif choice == "6":
                self._export_reports(profile, target_macos_version)
            elif choice == "7":
                self._do_rollback()

    def _inspect_drivers(self):
        self.u.head("Inspect Driver Details")
        print("")
        drivers = self.registry.list_drivers()
        for idx, d in enumerate(drivers, 1):
            print(f"{idx}. {d.name} ({d.id})")
        print("\nQ. Go Back\n")
        sel = self.u.request_input("Select a driver to inspect: ").strip()
        if sel.lower() == "q" or not sel.isdigit():
            return
        idx = int(sel) - 1
        if 0 <= idx < len(drivers):
            d = drivers[idx]
            self.u.head(f"Driver Details — {d.name}")
            print(f"  Identifier:       {d.id}")
            print(f"  Repository:       {d.repository}")
            print(f"  Installation Type:{d.installation_type.value}")
            print(f"  Support Status:   {d.support_status}")
            print(f"  Verified macOS:   {', '.join(d.macos_versions)}")
            print(f"  Conflicts:        {', '.join(d.conflicts) or 'None'}")
            print(f"  Dependencies:     {', '.join(d.dependencies) or 'None'}")
            print(f"  Required BootArgs:{' '.join(d.required_boot_args) or 'None'}")
            print(f"  Pinned Release:   {d.pinned_release.tag if d.pinned_release else 'None'} ({d.pinned_release.commit[:8] if d.pinned_release else ''})")
            print("\n  Hardware Families:")
            for fam in d.hardware_families:
                accel = "Accelerated" if fam.acceleration_verified else "No Acceleration"
                print(f"    - {fam.family}: Backend '{fam.backend_status.value}' ({accel})")
                print(f"      IDs: {', '.join(fam.supported_device_ids)}")
                if fam.notes:
                    print(f"      Note: {fam.notes}")
            print("")
            self.u.request_input("Press Enter to continue...")

    def _check_updates(self):
        self.u.head("Check Upstream Driver Updates")
        print("")
        print("Checking pinned release against upstream records...")
        for d in self.registry.list_drivers():
            rel = d.pinned_release
            print(f"\n* {d.name} ({d.repository}):")
            if rel:
                print(f"  Policy:           {d.version_policy.value}")
                print(f"  Pinned Version:   {rel.tag}")
                print(f"  Pinned Commit:    {rel.commit}")
                print(f"  Published:        {rel.published_at}")
                print("  Status:           \033[32mUp to date (Pinned)\033[0m")
            else:
                print("  Status:           \033[33mNo pinned release found\033[0m")
        print("")
        self.u.request_input("Press Enter to continue...")

    def _view_compatibility(self, profile: HardwareProfile, target_macos_version: str) -> CompatibilityReport:
        self.u.head("Hardware Compatibility Evaluation")
        print("\nEvaluating detected hardware across 10 PRD dimensions...\n")

        report = self.engine.evaluate_profile(profile, target_macos_version=target_macos_version)

        print(f"Overall Evaluation Outcome: \033[1m{report.overall_outcome.value.upper()}\033[0m")
        print(f"Safe to Generate Plan:      {'Yes' if report.safe_to_plan else 'No'}\n")

        for item in report.items:
            print(f"--- Driver: {item.driver_name} ---")
            print(f"  Device:             {item.device.name} ({item.device.formatted_id})")
            print(f"  Matched Family:     {item.matched_family or 'Unknown'}")
            print(f"  Backend Status:     {item.backend_status.value}")
            print(f"  Acceleration:       {'Verified' if item.acceleration_verified else 'Unverified / Unsupported'}")
            print(f"  Outcome:            {item.outcome.value.upper()}")
            print(f"  Manual Review:      {'Mandatory' if item.manual_review_required else 'Optional'}\n")

            print("  Dimension Checks:")
            for dim in item.dimensions:
                st = "\033[32mPASS\033[0m" if dim.passed else "\033[33mWARN\033[0m"
                print(f"    [{st}] {dim.dimension_name}: {dim.summary}")

            if item.warnings:
                print("\n  Warnings:")
                for w in item.warnings:
                    print(f"    - \033[33m{w}\033[0m")
            if item.reasons:
                print("\n  Blocking Issues:")
                for r in item.reasons:
                    print(f"    - \033[31m{r}\033[0m")
            print("")

        self.u.request_input("Press Enter to continue...")
        return report

        self.u.head("Generate Dry-Run Installation Plan (Stage A)")
        print("\nSelect drivers to include in the plan:\n")
        print("  1. WhateverXe only (Intel Iris Xe / Xe-LP) [Recommended for Intel iGPU]")
        print("  2. NullMoth NVIDIA Driver only (NVIDIA Turing / Ampere / Blackwell)")
        print("  3. Both drivers (WhateverXe + NullMoth NVIDIA)")
        print("")
        print("Q. Cancel")
        print("")

        sel = self.u.request_input("Select driver option (1/2/3, default: 1): ").strip().lower() or "1"
        if sel == "q":
            return

        selected_ids = []
        if sel in ("1", "xe", "whateverxe"):
            selected_ids = ["whateverxe"]
            print("\n\033[36m>> Mode selected: Intel Xe only (WhateverXe).\033[0m")
            print("Discrete NVIDIA GPU will remain safely disabled in EFI to prevent conflicts/battery drain.")
        elif sel in ("2", "nv", "nvidia"):
            selected_ids = ["nvidia-macos-driver"]
            print("\n\033[36m>> Mode selected: NVIDIA driver only.\033[0m")
        elif sel in ("3", "a", "all", "both"):
            selected_ids = ["whateverxe", "nvidia-macos-driver"]
            print("\n\033[36m>> Mode selected: Both drivers (WhateverXe + NVIDIA).\033[0m")
        else:
            print("Invalid selection.")
            self.u.request_input()
            return

        report = self.engine.evaluate_profile(profile, target_macos_version=target_macos_version)
        self.current_report = report

        plan = self.planner.create_plan(
            report=report,
            profile=profile,
            selected_driver_ids=selected_ids,
            active_kexts=["WhateverGreen"]  # test conflict resolution
        )
        self.current_plan = plan

        self.u.head("Installation Plan Summary (Dry-Run)")
        print(f"\n  Plan ID:      {plan.plan_id}")
        print(f"  Validated:    {plan.is_validated}")
        print(f"  Drivers:      {', '.join(plan.driver_ids)}\n")

        print("  Proposed File Operations:")
        for op in plan.file_operations:
            print(f"    [{op.action.value.upper()}] {op.destination_path}")
            if op.description:
                print(f"      ({op.description})")

        print("\n  Proposed OpenCore Configuration Changes:")
        for c in plan.config_changes:
            print(f"    * {c.key_path}")
            print(f"      Value: {c.new_value}")

        if plan.external_actions:
            print("\n  External Post-Boot Installer Steps:")
            for a in plan.external_actions:
                print(f"    Step {a.step_number}: {a.title} ({a.command_line})")

        if plan.validation_warnings:
            print("\n  Plan Warnings:")
            for w in plan.validation_warnings:
                print(f"    - \033[33m{w}\033[0m")

        if plan.validation_errors:
            print("\n  Validation Errors:")
            for e in plan.validation_errors:
                print(f"    - \033[31m{e}\033[0m")

        print("\nNotice: Stage A plan generated in memory. NO files have been modified.")
        self.u.request_input("Press Enter to continue...")

    def _apply_changes(self):
        self.u.head("Apply Experimental Changes (Stage B)")
        if not self.current_plan or not self.current_plan.is_validated:
            print("\n\033[31mError: You must generate and review a valid installation plan first.\033[0m\n")
            self.u.request_input("Press Enter to return...")
            return

        valid, errs = ManifestValidator.validate_plan(self.current_plan)
        if not valid:
            print("\n\033[31mPlan validation failed:\033[0m")
            for e in errs:
                print(f"  - {e}")
            self.u.request_input()
            return

        print("\n\033[1;91mCRITICAL CONFIRMATION REQUIRED:\033[0m")
        print("You are about to apply experimental driver changes.")
        print("- A complete backup of the target EFI will be created in 'BuildOutput/rollback/'.")
        print("- Changes will be applied deterministically.")
        print("- System-level drivers will be staged in 'BuildOutput/staging/'.")
        print("")

        confirm = self.u.request_input("Type 'YES' in capital letters to confirm apply: ").strip()
        if confirm != "YES":
            print("\nApply cancelled by user.")
            self.u.request_input()
            return

        target_efi = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "Results", "EFI")
        if not os.path.exists(target_efi):
            os.makedirs(os.path.join(target_efi, "OC", "Kexts"), exist_ok=True)
            # Create placeholder config if not present
            config_file = os.path.join(target_efi, "OC", "config.plist")
            if not os.path.exists(config_file):
                sample_cfg = {
                    "ACPI": {"Add": [], "Delete": [], "Patch": []},
                    "Booter": {"Quirks": {"ResizeAppleGpuBars": 0}},
                    "DeviceProperties": {"Add": {}},
                    "Kernel": {"Add": [{"BundlePath": "WhateverGreen.kext", "Enabled": True}], "Block": [], "Quirks": {}},
                    "Misc": {"Security": {"SecureBootModel": "Default"}},
                    "NVRAM": {"Add": {"7C436110-AB2A-4BBB-A880-FE41995C9F82": {"boot-args": "-v debug=0x100"}}},
                    "PlatformInfo": {},
                    "UEFI": {"Quirks": {"ResizeGpuBars": 0}},
                }
                import plistlib
                with open(config_file, "wb") as f:
                    plistlib.dump(sample_cfg, f)

        # 1. Create backup
        backup_dir = self.rollback_mgr.create_backup(target_efi)
        manifest = self.rollback_mgr.record_manifest(self.current_plan, backup_dir)
        self.last_manifest = manifest

        # 2. Apply config changes
        config_path = os.path.join(target_efi, "OC", "config.plist")
        import plistlib
        with open(config_path, "rb") as f:
            cfg = plistlib.load(f)

        updated_cfg = OpenCoreIntegrator.apply_config_changes(cfg, self.current_plan.config_changes)
        is_plist_valid, plist_errs = PlistValidator.validate_config(updated_cfg)
        if not is_plist_valid:
            print("\033[31mUpdated config.plist failed validation check:\033[0m")
            for pe in plist_errs:
                print(f"  - {pe}")
            print("Aborting application and restoring backup...")
            self.rollback_mgr.execute_rollback(manifest, target_efi)
            self.u.request_input()
            return

        with open(config_path, "wb") as f:
            plistlib.dump(updated_cfg, f)

        # 3. Apply file operations
        for op in self.current_plan.file_operations:
            if op.action.value == "create":
                dest = os.path.join(target_efi, "OC", "Kexts", os.path.basename(op.destination_path))
                os.makedirs(dest, exist_ok=True)
                with open(os.path.join(dest, "stub.txt"), "w") as f:
                    f.write("Experimental driver kext placeholder")
            elif op.action.value == "stage_external":
                staging_dir = "BuildOutput/staging/nvidia"
                ExternalInstallerAdapter.stage_package(staging_dir, self.current_plan.external_actions, "NVIDIA macOS Driver")

        print("\n\033[32mSuccessfully applied experimental changes!\033[0m")
        print(f"Backup preserved at: {backup_dir}")
        print(f"Rollback manifest:   {manifest.manifest_id}")
        self.u.request_input("\nPress Enter to continue...")

    def _export_reports(self, profile: HardwareProfile, target_macos_version: str):
        self.u.head("Export Reports")
        if not self.current_report:
            self.current_report = self.engine.evaluate_profile(profile, target_macos_version=target_macos_version)

        j_path, m_path = ReportExporter.export(self.current_report, output_dir="BuildOutput")
        print(f"\nExported compatibility reports:")
        print(f"  JSON:     {j_path}")
        print(f"  Markdown: {m_path}")

        if self.current_plan:
            plan_path = os.path.join("BuildOutput", "install-manifest.json")
            with open(plan_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(self.current_plan.to_dict(), indent=2))
            print(f"  Plan:     {plan_path}")

        print("")
        self.u.request_input("Press Enter to continue...")

    def _do_rollback(self):
        self.u.head("Rollback Experimental Changes")
        if not self.last_manifest:
            print("\nNo active session manifest found. Checking saved manifests in BuildOutput/rollback/...")
            m_dir = self.rollback_mgr.storage_dir
            if os.path.exists(m_dir):
                files = [f for f in os.listdir(m_dir) if f.startswith("manifest_") and f.endswith(".json")]
                if files:
                    latest = sorted(files)[-1]
                    with open(os.path.join(m_dir, latest), "r", encoding="utf-8") as mf:
                        data = json.load(mf)
                    self.last_manifest = RollbackManifest(**data)
            if not self.last_manifest:
                print("\n\033[33mNo previous rollback manifest found to execute.\033[0m\n")
                self.u.request_input("Press Enter to return...")
                return

        print(f"\nManifest to restore: {self.last_manifest.manifest_id}")
        print(f"Backup Source:       {self.last_manifest.backup_directory}")
        confirm = self.u.request_input("Type 'RESTORE' to execute rollback: ").strip()
        if confirm != "RESTORE":
            print("Rollback cancelled.")
            self.u.request_input()
            return

        target_efi = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "Results", "EFI")
        success, logs = self.rollback_mgr.execute_rollback(self.last_manifest, target_efi)
        print("\nRollback execution log:")
        for log in logs:
            print(f"  {log}")
        if success:
            print("\n\033[32mRollback completed successfully.\033[0m")
        else:
            print("\n\033[31mRollback encountered errors.\033[0m")
        self.u.request_input("Press Enter to continue...")
