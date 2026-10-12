# Compatibility result models representing the 10 PRD dimensions and structured reports
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from .driver import BackendStatus, CompatibilityOutcome
from .hardware_profile import PCIDevice

@dataclass
class DimensionCheck:
    dimension_name: str
    passed: bool
    summary: str
    details: str = ""
    evidence_reference: Optional[str] = None

@dataclass
class CompatibilityReportItem:
    driver_id: str
    driver_name: str
    device: PCIDevice
    matched_family: Optional[str] = None
    backend_status: BackendStatus = BackendStatus.UNKNOWN
    outcome: CompatibilityOutcome = CompatibilityOutcome.UNKNOWN
    dimensions: List[DimensionCheck] = field(default_factory=list)
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    acceleration_verified: bool = False
    requires_privileged_installer: bool = False
    requires_root_patch: bool = False
    conflicting_kexts: List[str] = field(default_factory=list)
    missing_dependencies: List[str] = field(default_factory=list)
    manual_review_required: bool = True
    evidence_urls: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "driver_id": self.driver_id,
            "driver_name": self.driver_name,
            "device": {
                "name": self.device.name,
                "pci_id": self.device.formatted_id,
                "classification": self.device.classification.value,
                "acpi_path": self.device.acpi_path,
            },
            "matched_family": self.matched_family,
            "backend_status": self.backend_status.value,
            "outcome": self.outcome.value,
            "acceleration_verified": self.acceleration_verified,
            "requires_privileged_installer": self.requires_privileged_installer,
            "requires_root_patch": self.requires_root_patch,
            "conflicting_kexts": self.conflicting_kexts,
            "missing_dependencies": self.missing_dependencies,
            "manual_review_required": self.manual_review_required,
            "reasons": self.reasons,
            "warnings": self.warnings,
            "evidence_urls": self.evidence_urls,
            "dimensions": [
                {
                    "name": d.dimension_name,
                    "passed": d.passed,
                    "summary": d.summary,
                    "details": d.details,
                    "evidence": d.evidence_reference,
                }
                for d in self.dimensions
            ],
        }

@dataclass
class CompatibilityReport:
    timestamp: str
    target_macos_version: str
    target_macos_build: Optional[str] = None
    hardware_summary: Dict[str, Any] = field(default_factory=dict)
    items: List[CompatibilityReportItem] = field(default_factory=list)
    overall_outcome: CompatibilityOutcome = CompatibilityOutcome.UNKNOWN
    safe_to_plan: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "target_macos_version": self.target_macos_version,
            "target_macos_build": self.target_macos_build,
            "hardware_summary": self.hardware_summary,
            "overall_outcome": self.overall_outcome.value,
            "safe_to_plan": self.safe_to_plan,
            "items": [item.to_dict() for item in self.items],
        }
