# RollbackManager: Deterministic backup, diff tracking, and isolated file recovery
import os
import shutil
import json
import uuid
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
from ..models.install_manifest import RollbackManifest, InstallPlan, FileAction

class RollbackManager:
    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = storage_dir or "BuildOutput/rollback"

    def create_backup(self, target_efi_dir: str) -> str:
        """Copies existing EFI directory into a timestamped rollback snapshot."""
        if not os.path.exists(target_efi_dir):
            raise FileNotFoundError(f"Target EFI directory '{target_efi_dir}' does not exist.")

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(self.storage_dir, f"efi_backup_{timestamp}")
        os.makedirs(backup_path, exist_ok=True)

        # Copy target EFI tree into backup
        shutil.copytree(target_efi_dir, os.path.join(backup_path, "EFI"), dirs_exist_ok=True)
        return backup_path

    def record_manifest(self, plan: InstallPlan, backup_dir: str) -> RollbackManifest:
        """Generates a RollbackManifest for the given plan."""
        manifest_id = f"rb_{uuid.uuid4().hex[:8]}"
        created_at = datetime.utcnow().isoformat() + "Z"

        created_files = []
        replaced_files = []
        external_items = []
        external_commands = []

        for op in plan.file_operations:
            if op.action == FileAction.CREATE:
                created_files.append(op.destination_path)
            elif op.action == FileAction.REPLACE:
                replaced_files.append({
                    "destination": op.destination_path,
                    "backup_source": os.path.join(backup_dir, op.destination_path),
                })
            elif op.action == FileAction.STAGE_EXTERNAL:
                external_items.append(op.destination_path)

        for act in plan.external_actions:
            if act.rollback_command:
                external_commands.append(act.rollback_command)

        manifest = RollbackManifest(
            manifest_id=manifest_id,
            plan_id=plan.plan_id,
            created_at=created_at,
            backup_directory=backup_dir,
            subsystem_created_files=created_files,
            replaced_files=replaced_files,
            modified_configs=[c.key_path for c in plan.config_changes],
            external_components_installed=external_items,
            external_rollback_commands=external_commands,
        )

        manifest_file = os.path.join(self.storage_dir, f"manifest_{manifest_id}.json")
        os.makedirs(self.storage_dir, exist_ok=True)
        with open(manifest_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(manifest.to_dict(), indent=2))

        return manifest

    def execute_rollback(self, manifest: RollbackManifest, target_efi_dir: str) -> Tuple[bool, List[str]]:
        """Restores EFI state, deleting ONLY subsystem-created files and restoring replaced files."""
        log: List[str] = []

        if not os.path.exists(manifest.backup_directory):
            return False, [f"Backup directory '{manifest.backup_directory}' was not found. Manual recovery required."]

        backup_efi = os.path.join(manifest.backup_directory, "EFI")
        if not os.path.exists(backup_efi):
            return False, ["Backup EFI snapshot is corrupted or missing."]

        # 1. Remove only subsystem-created files
        for created_path in manifest.subsystem_created_files:
            # Map path to target_efi_dir
            norm_rel = created_path.replace("\\", "/").lstrip("/")
            if norm_rel.startswith("EFI/"):
                norm_rel = norm_rel[4:]

            target_file = os.path.join(target_efi_dir, norm_rel)
            if os.path.exists(target_file):
                try:
                    if os.path.isdir(target_file):
                        shutil.rmtree(target_file)
                    else:
                        os.remove(target_file)
                    log.append(f"Removed subsystem file: {target_file}")
                except Exception as e:
                    log.append(f"Failed to remove {target_file}: {e}")

        # 2. Restore config.plist from backup
        backup_config = os.path.join(backup_efi, "OC", "config.plist")
        target_config = os.path.join(target_efi_dir, "OC", "config.plist")
        if os.path.exists(backup_config):
            shutil.copy2(backup_config, target_config)
            log.append("Restored original config.plist from backup snapshot.")

        # 3. Restore any replaced files
        for item in manifest.replaced_files:
            dst = item["destination"]
            src = item.get("backup_source")
            if src and os.path.exists(src):
                shutil.copy2(src, dst)
                log.append(f"Restored file from backup: {dst}")

        if manifest.external_rollback_commands:
            log.append("NOTICE: External driver components require manual command execution in macOS:")
            for cmd in manifest.external_rollback_commands:
                log.append(f"  Command: {cmd}")

        return True, log
