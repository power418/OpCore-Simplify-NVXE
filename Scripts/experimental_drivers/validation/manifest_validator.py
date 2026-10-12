# ManifestValidator: Validates plans and manifests before execution
from typing import Tuple, List
from ..models.install_manifest import InstallPlan, RollbackManifest

class ManifestValidator:
    @staticmethod
    def validate_plan(plan: InstallPlan) -> Tuple[bool, List[str]]:
        errors: List[str] = []

        if not plan.plan_id:
            errors.append("Install plan is missing plan_id.")

        if not plan.driver_ids:
            errors.append("Install plan has no proposed drivers.")

        if not plan.is_validated or plan.validation_errors:
            errors.extend(plan.validation_errors or ["Plan failed previous validation check."])

        for op in plan.file_operations:
            dest = op.destination_path.replace("\\", "/")
            # Safety check: Prevent writing to arbitrary root directories on host
            if dest.startswith("/") and not dest.startswith("/Library") and not dest.startswith("/Users/Shared"):
                errors.append(f"Unsafe destination path '{op.destination_path}'. Target paths must be relative or standard staging paths.")

        return len(errors) == 0, errors

    @staticmethod
    def validate_rollback_manifest(manifest: RollbackManifest) -> Tuple[bool, List[str]]:
        errors: List[str] = []
        if not manifest.manifest_id:
            errors.append("Rollback manifest missing manifest_id.")
        if not manifest.backup_directory:
            errors.append("Rollback manifest missing backup_directory.")
        return len(errors) == 0, errors
