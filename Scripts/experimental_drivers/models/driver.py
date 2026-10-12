# Driver model and metadata schemas
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json

class InstallationType(str, Enum):
    OPENCORE_KEXT = "opencore-kext"
    ROOT_PATCH = "root-patch"
    SYSTEM_EXTENSION = "system-extension"
    EXTERNAL_INSTALLER = "external-installer"
    MANUAL_ONLY = "manual-only"

class BackendStatus(str, Enum):
    UNKNOWN = "unknown"
    CATALOGUED = "catalogued"
    BACKEND_IMPLEMENTED = "backend_implemented"
    BUILD_VERIFIED = "build_verified"
    RUNTIME_VERIFIED = "runtime_verified"
    ACCELERATION_VERIFIED = "acceleration_verified"
    PARTIALLY_SUPPORTED = "partially_supported"
    UNSUPPORTED = "unsupported"

class CompatibilityOutcome(str, Enum):
    VERIFIED = "verified"
    CONDITIONAL = "conditional"
    EXPERIMENTAL = "experimental"
    UNSUPPORTED = "unsupported"
    UNKNOWN = "unknown"

class UpdateState(str, Enum):
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"
    RELEASE_NOT_FOUND = "release_not_found"
    SOURCE_UNAVAILABLE = "source_unavailable"
    VERIFICATION_FAILED = "verification_failed"
    BREAKING_CHANGE_SUSPECTED = "breaking_change_suspected"
    MANUAL_REVIEW_REQUIRED = "manual_review_required"

class VersionPolicy(str, Enum):
    PINNED = "pinned"
    MANUAL = "manual"

@dataclass
class DriverRelease:
    tag: str
    commit: str
    release_name: str
    published_at: str
    assets: List[Dict[str, Any]] = field(default_factory=list)
    download_url: Optional[str] = None
    sha256: Optional[str] = None
    changelog: str = ""

@dataclass
class HardwareFamilySupport:
    family: str
    supported_device_ids: List[str]
    backend_status: BackendStatus
    acceleration_verified: bool
    evidence_url: str
    notes: str = ""

@dataclass
class DriverDefinition:
    id: str
    name: str
    repository: str
    category: str
    installation_type: InstallationType
    support_status: str
    macos_versions: List[str]
    hardware_families: List[HardwareFamilySupport]
    requires_root_patch: bool = False
    requires_privileged_installation: bool = False
    conflicts: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    required_boot_args: List[str] = field(default_factory=list)
    optional_boot_args: List[str] = field(default_factory=list)
    required_opencore_settings: Dict[str, Any] = field(default_factory=dict)
    installation_destinations: List[str] = field(default_factory=list)
    version_policy: VersionPolicy = VersionPolicy.PINNED
    pinned_release: Optional[DriverRelease] = None
    last_verified_timestamp: Optional[str] = None
    source_evidence_references: List[str] = field(default_factory=list)
    automatic_installation_allowed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "repository": self.repository,
            "category": self.category,
            "installation_type": self.installation_type.value,
            "support_status": self.support_status,
            "macos_versions": self.macos_versions,
            "hardware_families": [
                {
                    "family": h.family,
                    "supported_device_ids": h.supported_device_ids,
                    "backend_status": h.backend_status.value,
                    "acceleration_verified": h.acceleration_verified,
                    "evidence_url": h.evidence_url,
                    "notes": h.notes,
                }
                for h in self.hardware_families
            ],
            "requires_root_patch": self.requires_root_patch,
            "requires_privileged_installation": self.requires_privileged_installation,
            "conflicts": self.conflicts,
            "dependencies": self.dependencies,
            "required_boot_args": self.required_boot_args,
            "optional_boot_args": self.optional_boot_args,
            "required_opencore_settings": self.required_opencore_settings,
            "installation_destinations": self.installation_destinations,
            "version_policy": self.version_policy.value,
            "pinned_release": {
                "tag": self.pinned_release.tag,
                "commit": self.pinned_release.commit,
                "release_name": self.pinned_release.release_name,
                "published_at": self.pinned_release.published_at,
                "download_url": self.pinned_release.download_url,
                "sha256": self.pinned_release.sha256,
            } if self.pinned_release else None,
            "last_verified_timestamp": self.last_verified_timestamp,
            "source_evidence_references": self.source_evidence_references,
            "automatic_installation_allowed": self.automatic_installation_allowed,
        }
