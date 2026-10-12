# Install manifest and planning models
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

class FileAction(str, Enum):
    CREATE = "create"
    REPLACE = "replace"
    DELETE = "delete"
    STAGE_EXTERNAL = "stage_external"

@dataclass
class FileOperation:
    action: FileAction
    destination_path: str
    source_path: Optional[str] = None
    sha256_before: Optional[str] = None
    sha256_after: Optional[str] = None
    description: str = ""
    is_subsystem_owned: bool = True

@dataclass
class ConfigChange:
    key_path: str  # e.g. "NVRAM/Add/7C436110-AB2A-4BBB-A880-FE41995C9F82/boot-args"
    old_value: Any
    new_value: Any
    operation: str = "update"  # "add", "update", "delete"
    description: str = ""

@dataclass
class ExternalAction:
    step_number: int
    title: str
    command_line: str
    working_directory: str
    requires_root: bool
    description: str
    rollback_command: Optional[str] = None

@dataclass
class InstallPlan:
    plan_id: str
    created_at: str
    driver_ids: List[str]
    proposed_drivers: List[Dict[str, Any]] = field(default_factory=list)
    file_operations: List[FileOperation] = field(default_factory=list)
    config_changes: List[ConfigChange] = field(default_factory=list)
    external_actions: List[ExternalAction] = field(default_factory=list)
    recovery_instructions: List[str] = field(default_factory=list)
    is_validated: bool = False
    validation_errors: List[str] = field(default_factory=list)
    validation_warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "driver_ids": self.driver_ids,
            "proposed_drivers": self.proposed_drivers,
            "is_validated": self.is_validated,
            "validation_errors": self.validation_errors,
            "validation_warnings": self.validation_warnings,
            "file_operations": [
                {
                    "action": op.action.value,
                    "destination_path": op.destination_path,
                    "source_path": op.source_path,
                    "sha256_before": op.sha256_before,
                    "sha256_after": op.sha256_after,
                    "description": op.description,
                    "is_subsystem_owned": op.is_subsystem_owned,
                }
                for op in self.file_operations
            ],
            "config_changes": [
                {
                    "key_path": c.key_path,
                    "operation": c.operation,
                    "old_value": str(c.old_value),
                    "new_value": str(c.new_value),
                    "description": c.description,
                }
                for c in self.config_changes
            ],
            "external_actions": [
                {
                    "step": a.step_number,
                    "title": a.title,
                    "command": a.command_line,
                    "requires_root": a.requires_root,
                    "description": a.description,
                    "rollback_command": a.rollback_command,
                }
                for a in self.external_actions
            ],
            "recovery_instructions": self.recovery_instructions,
        }

@dataclass
class RollbackManifest:
    manifest_id: str
    plan_id: str
    created_at: str
    backup_directory: str
    subsystem_created_files: List[str] = field(default_factory=list)
    replaced_files: List[Dict[str, str]] = field(default_factory=list)  # {"destination": ..., "backup_path": ...}
    modified_configs: List[Dict[str, Any]] = field(default_factory=list)
    external_components_installed: List[str] = field(default_factory=list)
    external_rollback_commands: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_id": self.manifest_id,
            "plan_id": self.plan_id,
            "created_at": self.created_at,
            "backup_directory": self.backup_directory,
            "subsystem_created_files": self.subsystem_created_files,
            "replaced_files": self.replaced_files,
            "modified_configs": self.modified_configs,
            "external_components_installed": self.external_components_installed,
            "external_rollback_commands": self.external_rollback_commands,
        }
