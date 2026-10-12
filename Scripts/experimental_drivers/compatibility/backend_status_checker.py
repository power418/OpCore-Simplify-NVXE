# BackendStatusChecker: Distinguishes catalogued devices from implemented and verified backends
from ..models.driver import BackendStatus, HardwareFamilySupport

class BackendStatusChecker:
    @staticmethod
    def is_backend_implemented(family: HardwareFamilySupport) -> bool:
        """Returns True if the backend code is actually implemented (not merely catalogued)."""
        implemented_states = {
            BackendStatus.BACKEND_IMPLEMENTED,
            BackendStatus.BUILD_VERIFIED,
            BackendStatus.RUNTIME_VERIFIED,
            BackendStatus.ACCELERATION_VERIFIED,
        }
        return family.backend_status in implemented_states

    @staticmethod
    def is_acceleration_verified(family: HardwareFamilySupport) -> bool:
        """Returns True only when QE/CI / Metal acceleration is verified on real physical hardware."""
        return family.backend_status == BackendStatus.ACCELERATION_VERIFIED or family.acceleration_verified

    @staticmethod
    def get_status_description(status: BackendStatus) -> str:
        descriptions = {
            BackendStatus.UNKNOWN: "Unknown backend status; no verification records found.",
            BackendStatus.CATALOGUED: "Device ID is present in driver catalog/source table, but NO driver backend is implemented.",
            BackendStatus.BACKEND_IMPLEMENTED: "Driver backend logic is implemented in source code.",
            BackendStatus.BUILD_VERIFIED: "Driver builds against donor frameworks, but hardware runtime is unverified.",
            BackendStatus.RUNTIME_VERIFIED: "Driver initializes at boot on test hardware.",
            BackendStatus.ACCELERATION_VERIFIED: "Metal / graphics acceleration is physically tested and verified on hardware.",
            BackendStatus.PARTIALLY_SUPPORTED: "Basic display working, but hardware acceleration/features are degraded.",
            BackendStatus.UNSUPPORTED: "Explicitly incompatible or unsupported by the project architecture.",
        }
        return descriptions.get(status, "Status undetermined.")
