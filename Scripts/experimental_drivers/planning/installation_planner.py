# InstallationPlanner: Stage A dry-run planner producing plans without modifying disks
from typing import Dict, List, Optional, Any
from datetime import datetime
import uuid
from ..models.hardware_profile import HardwareProfile, GPUClassification
from ..models.driver import DriverDefinition, InstallationType, VersionPolicy
from ..models.compatibility_result import CompatibilityReport, CompatibilityReportItem
from ..models.install_manifest import (
    InstallPlan,
    FileOperation,
    FileAction,
    ConfigChange,
    ExternalAction,
)
from ..registry.driver_registry import DriverRegistry
from .dependency_resolver import DependencyResolver

class InstallationPlanner:
    def __init__(self, registry: Optional[DriverRegistry] = None):
        self.registry = registry or DriverRegistry()
        self.resolver = DependencyResolver()

    def create_plan(
        self,
        report: CompatibilityReport,
        profile: HardwareProfile,
        selected_driver_ids: List[str],
        active_kexts: Optional[List[str]] = None,
        efi_base_path: str = "EFI",
        xe_options: Optional[Dict[str, Any]] = None,
    ) -> InstallPlan:
        active_kexts = active_kexts or []
        plan_id = str(uuid.uuid4())[:8]
        timestamp = datetime.utcnow().isoformat() + "Z"

        selected_drivers: List[DriverDefinition] = []
        for did in selected_driver_ids:
            drv = self.registry.get_driver(did)
            if drv:
                selected_drivers.append(drv)

        file_ops: List[FileOperation] = []
        config_changes: List[ConfigChange] = []
        external_actions: List[ExternalAction] = []
        recovery_instructions: List[str] = []
        validation_errors: List[str] = []
        validation_warnings: List[str] = []

        # 1. Resolve conflicts and dependencies
        kexts_to_disable, blocking_errors = self.resolver.resolve_conflicts(selected_drivers, active_kexts)
        if blocking_errors:
            validation_errors.extend(blocking_errors)

        for conflict in kexts_to_disable:
            config_changes.append(ConfigChange(
                key_path=f"Kernel/Add/{conflict}/Enabled",
                old_value=True,
                new_value=False,
                operation="update",
                description=f"Disable conflicting kext {conflict} to prevent graphics stack kernel panic.",
            ))

        proposed_drivers_summary = []

        for driver in selected_drivers:
            rel = driver.pinned_release
            proposed_drivers_summary.append({
                "id": driver.id,
                "name": driver.name,
                "version": rel.tag if rel else "custom",
                "commit": rel.commit if rel else "unpinned",
                "installation_type": driver.installation_type.value,
                "repository": driver.repository,
            })

            # Check driver specific plan requirements
            if driver.id == "whateverxe":
                # Must be an opencore-kext
                file_ops.append(FileOperation(
                    action=FileAction.CREATE,
                    destination_path=f"{efi_base_path}/OC/Kexts/WhateverXe.kext",
                    description="WhateverXe Lilu plugin for Intel Xe-LP graphics.",
                    is_subsystem_owned=True,
                ))
                file_ops.append(FileOperation(
                    action=FileAction.CREATE,
                    destination_path=f"{efi_base_path}/OC/Kexts/AMFIPass.kext",
                    description="AMFIPass v1.4.1 Mod build for modified graphics stack.",
                    is_subsystem_owned=True,
                ))

                # OpenCore kernel entries
                config_changes.append(ConfigChange(
                    key_path="Kernel/Add/WhateverXe.kext",
                    old_value=None,
                    new_value={"BundlePath": "WhateverXe.kext", "Enabled": True, "ExecutablePath": "Contents/MacOS/WhateverXe", "PlistPath": "Contents/Info.plist"},
                    operation="add",
                    description="Load WhateverXe.kext through OpenCore Kernel/Add.",
                ))
                config_changes.append(ConfigChange(
                    key_path="Kernel/Add/AMFIPass.kext",
                    old_value=None,
                    new_value={"BundlePath": "AMFIPass.kext", "Enabled": True, "ExecutablePath": "Contents/MacOS/AMFIPass", "PlistPath": "Contents/Info.plist"},
                    operation="add",
                    description="Load AMFIPass Mod through OpenCore Kernel/Add.",
                ))

                # Boot arguments per WhateverXe README (+ conditional flags).
                # -wex-nopanel: Tiger Lake headless only. -igfxdvmt: DVMT 60MB only.
                xe_options = xe_options or {}
                xe_boot = ["-allow3d", "-disablegfxfirmware"]
                xe_dp_props: Dict[str, Any] = {}
                igpu_path = str(xe_options.get("igpu_pci_path") or "PciRoot(0x0)/Pci(0x2,0x0)")

                try:
                    from Scripts.datasets import whateverxe_data as _xe
                except ImportError:  # pragma: no cover
                    from ...datasets import whateverxe_data as _xe  # type: ignore

                intel_igpus = []
                try:
                    _integrated = profile.get_integrated_gpu() if hasattr(profile, "get_integrated_gpu") else None
                except Exception:
                    _integrated = None
                if _integrated is not None and (str(getattr(_integrated, "vendor_id", "")).upper() == "8086"):
                    intel_igpus = [_integrated]
                if not intel_igpus:
                    intel_igpus = [g for g in (profile.gpus or []) if str(getattr(g, "vendor_id", "")).upper() == "8086"]
                # Fallback: any Intel GPU when classification is unavailable.
                if not intel_igpus:
                    intel_igpus = [g for g in (profile.gpus or []) if (g.vendor_id or "").upper() == "8086"]
                if intel_igpus:
                    _ig = intel_igpus[0]
                    if getattr(_ig, "pci_path", None):
                        igpu_path = _ig.pci_path
                    dev = _xe.normalize_device_id(getattr(_ig, "device_id", ""))
                    if dev in _xe.TIGER_LAKE_IDS:
                        has_internal = any(
                            getattr(d, "connected_gpu", "") == getattr(_ig, "name", "") and getattr(d, "connector_type", "") == "Internal"
                            for d in (profile.displays or []))
                        if not has_internal and "-wex-nopanel" not in xe_boot:
                            xe_boot.append("-wex-nopanel")

                dvmt_opt = xe_options.get("dvmt_megabytes")
                if dvmt_opt is not None:
                    try:
                        if int(dvmt_opt) == 60:
                            xe_dp_props.update(_xe.DVMT_60MB_PROPERTIES)
                            xe_boot.append("-igfxdvmt")
                        elif int(dvmt_opt) != 96:
                            validation_warnings.append(
                                "WhateverXe DVMT option {}MB is neither 60 nor 96; no DVMT properties planned (set 96MB in BIOS where possible).".format(dvmt_opt))
                    except (TypeError, ValueError):
                        validation_errors.append("Invalid xe_options['dvmt_megabytes']: must be 60, 96, or omitted.")

                override_opt = xe_options.get("device_id_override")
                if override_opt is not None:
                    ov = override_opt
                    if isinstance(ov, str):
                        s = "".join(c for c in ov if c in "0123456789abcdefABCDEF")
                        if len(s) == 4:
                            ov = _xe.encode_device_id_override(s)
                    phys_id = intel_igpus[0].device_id if intel_igpus else "0000"
                    ok, _target, err, w = _xe.validate_device_id_override(ov, phys_id, "8086")
                    validation_warnings.extend(w)
                    if not ok:
                        # No silent fallback to physical ID (per docs).
                        validation_errors.append("Invalid WhateverXe device-id override: {}".format(err))
                    else:
                        xe_dp_props["device-id"] = ov

                config_changes.append(ConfigChange(
                    key_path="NVRAM/Add/7C436110-AB2A-4BBB-A880-FE41995C9F82/boot-args",
                    old_value="<current_boot_args>",
                    new_value=" ".join(xe_boot),
                    operation="update",
                    description="Append WhateverXe required boot arguments (-allow3d -disablegfxfirmware plus conditional -wex-nopanel/-igfxdvmt).",
                ))

                if xe_dp_props:
                    config_changes.append(ConfigChange(
                        key_path="DeviceProperties/Add/{}".format(igpu_path),
                        old_value=None,
                        new_value=dict(xe_dp_props),
                        operation="add",
                        description="WhateverXe iGPU DeviceProperties on {} (DVMT 60MB pair and/or device-id override per README).".format(igpu_path),
                    ))
                else:
                    validation_warnings.append(
                        "WhateverXe automatic selection needs no iGPU DeviceProperties on {} (96MB DVMT assumed; VBT routing). "
                        "Set xe_options['dvmt_megabytes']=60 only when firmware is fixed at 60MB.".format(igpu_path))

                recovery_instructions.append(
                    "WhateverXe Recovery: If display fails at boot, boot OpenCore into recovery or single-user mode, "
                    "remove WhateverXe.kext and AMFIPass.kext from EFI/OC/Kexts, re-enable WhateverGreen in config.plist, "
                    "and remove -allow3d -disablegfxfirmware from boot-args."
                )

            elif driver.id == "nvidia-macos-driver":
                # External installer: MUST NOT stage into EFI/OC/Kexts
                file_ops.append(FileOperation(
                    action=FileAction.STAGE_EXTERNAL,
                    destination_path="BuildOutput/staging/nvidia-pkg/install.sh",
                    description="Stage NVIDIA driver installer scripts and kernel modules in staging directory outside EFI.",
                    is_subsystem_owned=True,
                ))

                # EFI Config adjustments required by NVIDIA driver
                config_changes.append(ConfigChange(
                    key_path="NVRAM/Add/7C436110-AB2A-4BBB-A880-FE41995C9F82/csr-active-config",
                    old_value="<current_csr>",
                    new_value="430A0000",
                    operation="update",
                    description="Configure SIP with required allowances for unsigned kexts and root operations.",
                ))
                config_changes.append(ConfigChange(
                    key_path="NVRAM/Add/7C436110-AB2A-4BBB-A880-FE41995C9F82/boot-args",
                    old_value="<current_boot_args>",
                    new_value="nvfb=1 nvaccel=1 nvfbheads=4 -nvkmsnosmooth amfi_get_out_of_my_way=0x1 amfi=0x80 ipc_control_port_options=0",
                    operation="update",
                    description="Add NVIDIA framebuffer and AMFI WindowServer arguments.",
                ))
                config_changes.append(ConfigChange(
                    key_path="UEFI/Quirks/ResizeGpuBars",
                    old_value=0,
                    new_value=13,
                    operation="update",
                    description="Set ResizeGpuBars to 13 (8GB BAR).",
                ))
                config_changes.append(ConfigChange(
                    key_path="Booter/Quirks/ResizeAppleGpuBars",
                    old_value=0,
                    new_value=-1,
                    operation="update",
                    description="Set ResizeAppleGpuBars to -1 for full BAR visibility in macOS.",
                ))
                config_changes.append(ConfigChange(
                    key_path="Kernel/Block/IONDRVSupport",
                    old_value=None,
                    new_value={"Identifier": "com.apple.iokit.IONDRVSupport", "Strategy": "Exclude", "Enabled": True},
                    operation="add",
                    description="Exclude Apple IONDRVSupport to allow NVRMFB to take primary display index.",
                ))
                config_changes.append(ConfigChange(
                    key_path="Misc/Security/SecureBootModel",
                    old_value="Default",
                    new_value="Disabled",
                    operation="update",
                    description="Disable Apple Secure Boot for non-Apple kernel extensions.",
                ))

                external_actions.append(ExternalAction(
                    step_number=1,
                    title="Run Privileged NVIDIA Driver Installer in macOS",
                    command_line="sudo ./install.sh",
                    working_directory="/Library/GPUBundles/nullmoth-nvidia/pkgroot",
                    requires_root=True,
                    description="Copies kernel extensions to /Library/Extensions, bundles to /Library/GPUBundles, and rebuilds Auxiliary Kernel Collection (AKC).",
                    rollback_command="sudo ./uninstall.sh",
                ))
                external_actions.append(ExternalAction(
                    step_number=2,
                    title="Authorize System Extension in System Settings",
                    command_line="open 'x-apple.systempreferences:com.apple.preference.security?Privacy_Security'",
                    working_directory="/",
                    requires_root=False,
                    description="Open macOS Privacy & Security to authorize NullMoth kernel extensions.",
                    rollback_command=None,
                ))

                recovery_instructions.append(
                    "NVIDIA Driver Recovery: If system crashes or freezes at 'PCI configuration end', boot with boot-arg "
                    "'-nvrmnogo' or '-x' (safe mode), then run 'sudo ./uninstall.sh' or remove "
                    "/Library/Extensions/NVRM* /Library/Extensions/NVAccel* and trigger 'sudo kmutil clear-staging'."
                )

        # PRD test case 10: both experimental drivers selected simultaneously
        if "whateverxe" in selected_driver_ids and "nvidia-macos-driver" in selected_driver_ids:
            validation_warnings.append(
                "Notice: Both Intel WhateverXe and NVIDIA driver are planned simultaneously. "
                "Ensure WhateverXe handles iGPU while NVIDIA handles discrete GPU. "
                "Do NOT inject NVIDIA kexts into EFI."
            )

        is_validated = len(validation_errors) == 0

        return InstallPlan(
            plan_id=plan_id,
            created_at=timestamp,
            driver_ids=selected_driver_ids,
            proposed_drivers=proposed_drivers_summary,
            file_operations=file_ops,
            config_changes=config_changes,
            external_actions=external_actions,
            recovery_instructions=recovery_instructions,
            is_validated=is_validated,
            validation_errors=validation_errors,
            validation_warnings=validation_warnings,
        )
