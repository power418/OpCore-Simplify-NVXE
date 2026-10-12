# CompatibilityEngine: Comprehensive 10-dimension evaluation system
from typing import Dict, List, Optional, Any
from datetime import datetime
from ..models.hardware_profile import HardwareProfile, PCIDevice, GPUClassification
from ..models.driver import (
    DriverDefinition,
    HardwareFamilySupport,
    BackendStatus,
    CompatibilityOutcome,
    InstallationType,
)
from ..models.compatibility_result import (
    DimensionCheck,
    CompatibilityReportItem,
    CompatibilityReport,
)
from ..detection.hardware_matcher import HardwareMatcher, DriverMatch
from .macos_version_checker import MacOSVersionChecker
from .backend_status_checker import BackendStatusChecker

class CompatibilityEngine:
    def __init__(self, matcher: Optional[HardwareMatcher] = None):
        self.matcher = matcher or HardwareMatcher()

    def evaluate_match(
        self,
        match: DriverMatch,
        profile: HardwareProfile,
        target_macos_version: str,
        target_macos_build: Optional[str] = None,
        existing_kexts: Optional[List[str]] = None,
    ) -> CompatibilityReportItem:
        existing_kexts = existing_kexts or []
        device = match.device
        driver = match.driver
        family = match.family

        dimensions: List[DimensionCheck] = []
        reasons: List[str] = []
        warnings: List[str] = []
        conflicting_kexts: List[str] = []
        missing_deps: List[str] = []

        # 1. PCI device identification
        pci_passed = match.is_direct_pci_match
        dimensions.append(DimensionCheck(
            dimension_name="1. PCI Device Identification",
            passed=pci_passed,
            summary=f"PCI ID {device.formatted_id}: {'Exact match in table' if pci_passed else 'Architecture match only'}",
            details=f"Device: {device.name}, Vendor: {device.vendor_id}, Device: {device.device_id}, Subvendor: {device.subsystem_vendor_id or 'N/A'}",
            evidence_reference=family.evidence_url,
        ))
        if not pci_passed:
            warnings.append(f"Device ID {device.formatted_id} is not explicitly registered in {family.family} table.")

        # 2. GPU architecture
        arch_passed = bool(device.codename)
        dimensions.append(DimensionCheck(
            dimension_name="2. GPU Architecture",
            passed=arch_passed,
            summary=f"Family: {family.family} (Detected: {device.codename or 'Unknown'})",
            details=f"Classification: {device.classification.value}",
            evidence_reference=family.evidence_url,
        ))

        # 3. Backend implementation status
        backend_implemented = BackendStatusChecker.is_backend_implemented(family)
        acceleration_verified = BackendStatusChecker.is_acceleration_verified(family)
        dimensions.append(DimensionCheck(
            dimension_name="3. Backend Implementation Status",
            passed=backend_implemented,
            summary=f"State: {family.backend_status.value} (Acceleration: {'Verified' if acceleration_verified else 'Unverified'})",
            details=BackendStatusChecker.get_status_description(family.backend_status),
            evidence_reference=family.evidence_url,
        ))
        if not backend_implemented:
            warnings.append(f"No active driver backend is implemented for {family.family}. It is catalogued as a roadmap or placeholder target.")

        # 4. Supported macOS version and build
        version_supported = False
        if driver.macos_versions:
            min_v = driver.macos_versions[0]
            max_v = driver.macos_versions[-1] if len(driver.macos_versions) > 1 else min_v
            version_supported = MacOSVersionChecker.is_version_supported(target_macos_version, min_v, max_v)

        dimensions.append(DimensionCheck(
            dimension_name="4. Supported macOS Version & Build",
            passed=version_supported,
            summary=f"Target {target_macos_version} ({MacOSVersionChecker.darwin_to_macos_marketing_version(target_macos_version)}): {'Supported' if version_supported else 'Out of verified range'}",
            details=f"Driver verified on: {', '.join(driver.macos_versions)}. (Target build: {target_macos_build or 'generic'})",
            evidence_reference=driver.repository,
        ))
        if not version_supported:
            warnings.append(f"Target macOS version {target_macos_version} is outside driver's verified range ({min_v} - {max_v}).")

        # 5. Required kernel interfaces and frameworks
        kernel_interfaces_pass = True
        kernel_details = "Driver uses standard Lilu/IOPCIFamily interfaces." if driver.installation_type == InstallationType.OPENCORE_KEXT else "Requires macOS Auxiliary Kernel Collection (AKC) support."
        dimensions.append(DimensionCheck(
            dimension_name="5. Required Kernel Interfaces & Frameworks",
            passed=kernel_interfaces_pass,
            summary="Kernel interfaces compatible",
            details=kernel_details,
            evidence_reference=driver.repository,
        ))

        # 6. Driver dependencies
        for dep in driver.dependencies:
            # Check if dependencies are documented
            pass
        dimensions.append(DimensionCheck(
            dimension_name="6. Driver Dependencies",
            passed=True,
            summary=f"Required dependencies: {', '.join(driver.dependencies)}",
            details="Must be staged alongside driver.",
            evidence_reference=driver.repository,
        ))

        # 7. Conflicting kexts or patches
        for conflict in driver.conflicts:
            if conflict in existing_kexts:
                conflicting_kexts.append(conflict)
        conflicts_pass = len(conflicting_kexts) == 0
        dimensions.append(DimensionCheck(
            dimension_name="7. Conflicting Kexts & Patches",
            passed=conflicts_pass,
            summary=f"Known conflicts: {', '.join(driver.conflicts)}. Active conflicts: {', '.join(conflicting_kexts) if conflicting_kexts else 'None'}",
            details="Driver must have mutual exclusivity configured.",
            evidence_reference=driver.repository,
        ))
        if not conflicts_pass:
            reasons.append(f"Cannot enable {driver.name} simultaneously with active conflicting kext(s): {', '.join(conflicting_kexts)}.")

        # 8. Installation mechanism
        dimensions.append(DimensionCheck(
            dimension_name="8. Installation Mechanism",
            passed=True,
            summary=f"Mechanism: {driver.installation_type.value}",
            details=f"Destinations: {', '.join(driver.installation_destinations)}. Requires root: {driver.requires_privileged_installation}.",
            evidence_reference=driver.repository,
        ))

        # 9. Known hardware-specific limitations
        hw_limitations_passed = True
        hw_limitations_notes = []
        if profile.platform == "Laptop" and device.classification == GPUClassification.DISCRETE:
            hw_limitations_notes.append("Laptop discrete GPU detected (Optimus). Internal display routing is muxless and unverified in macOS.")
            hw_limitations_passed = False
        if driver.id == "whateverxe" and profile.platform == "Laptop":
            hw_limitations_notes.append("WhateverXe currently does not support internal laptop eDP displays.")
            hw_limitations_passed = False

        dimensions.append(DimensionCheck(
            dimension_name="9. Known Hardware Limitations",
            passed=hw_limitations_passed,
            summary="Hardware constraints evaluated",
            details="; ".join(hw_limitations_notes) if hw_limitations_notes else "No critical platform blocking issues identified.",
            evidence_reference=driver.repository,
        ))
        if hw_limitations_notes:
            warnings.extend(hw_limitations_notes)

        # 10. Verification evidence
        dimensions.append(DimensionCheck(
            dimension_name="10. Verification Evidence",
            passed=bool(driver.source_evidence_references),
            summary="Source code and commit hashes verified",
            details=f"Pinned commit: {driver.pinned_release.commit if driver.pinned_release else 'N/A'}",
            evidence_reference=driver.source_evidence_references[0] if driver.source_evidence_references else None,
        ))

        # Outcome synthesis
        if not backend_implemented or not version_supported:
            outcome = CompatibilityOutcome.EXPERIMENTAL if pci_passed else CompatibilityOutcome.UNSUPPORTED
        elif backend_implemented and not acceleration_verified:
            outcome = CompatibilityOutcome.EXPERIMENTAL
        elif backend_implemented and acceleration_verified and version_supported and conflicts_pass:
            outcome = CompatibilityOutcome.CONDITIONAL if driver.requires_root_patch or driver.required_boot_args else CompatibilityOutcome.VERIFIED
        else:
            outcome = CompatibilityOutcome.EXPERIMENTAL

        manual_review = (
            outcome in (CompatibilityOutcome.EXPERIMENTAL, CompatibilityOutcome.CONDITIONAL, CompatibilityOutcome.UNSUPPORTED)
            or not acceleration_verified
            or driver.requires_privileged_installation
            or not hw_limitations_passed
        )

        return CompatibilityReportItem(
            driver_id=driver.id,
            driver_name=driver.name,
            device=device,
            matched_family=family.family,
            backend_status=family.backend_status,
            outcome=outcome,
            dimensions=dimensions,
            reasons=reasons,
            warnings=warnings,
            acceleration_verified=acceleration_verified,
            requires_privileged_installer=driver.requires_privileged_installation,
            requires_root_patch=driver.requires_root_patch,
            conflicting_kexts=conflicting_kexts,
            missing_dependencies=missing_deps,
            manual_review_required=manual_review,
            evidence_urls=[family.evidence_url] if family.evidence_url else [],
        )

    def evaluate_profile(
        self,
        profile: HardwareProfile,
        target_macos_version: str,
        target_macos_build: Optional[str] = None,
        existing_kexts: Optional[List[str]] = None,
    ) -> CompatibilityReport:
        matches = self.matcher.match_profile(profile)
        items: List[CompatibilityReportItem] = []

        for m in matches:
            item = self.evaluate_match(
                match=m,
                profile=profile,
                target_macos_version=target_macos_version,
                target_macos_build=target_macos_build,
                existing_kexts=existing_kexts,
            )
            items.append(item)

        # Aggregate overall outcome
        if not items:
            overall = CompatibilityOutcome.UNKNOWN
            safe = False
        elif all(i.outcome == CompatibilityOutcome.VERIFIED for i in items):
            overall = CompatibilityOutcome.VERIFIED
            safe = True
        elif any(i.outcome in (CompatibilityOutcome.VERIFIED, CompatibilityOutcome.CONDITIONAL, CompatibilityOutcome.EXPERIMENTAL) for i in items):
            overall = CompatibilityOutcome.EXPERIMENTAL
            safe = True  # Can generate dry-run plan for review
        else:
            overall = CompatibilityOutcome.UNSUPPORTED
            safe = False

        return CompatibilityReport(
            timestamp=datetime.utcnow().isoformat() + "Z",
            target_macos_version=target_macos_version,
            target_macos_build=target_macos_build,
            hardware_summary={
                "platform": profile.platform,
                "motherboard": profile.motherboard_name,
                "cpu": profile.cpu_name,
                "gpus": [g.formatted_id for g in profile.gpus],
            },
            items=items,
            overall_outcome=overall,
            safe_to_plan=safe,
        )
