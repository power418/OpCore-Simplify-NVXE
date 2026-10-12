# ExternalInstallerAdapter: Stages external packages and generates manual execution instructions
import os
from typing import Dict, List, Optional, Any
from ..models.install_manifest import ExternalAction

class ExternalInstallerAdapter:
    @staticmethod
    def generate_instruction_guide(actions: List[ExternalAction], driver_name: str) -> str:
        lines = [
            f"# External Installation Guide — {driver_name}",
            "",
            "> [!WARNING]",
            "> This driver requires privileged system-level modifications (System Extensions and Auxiliary Kernel Collection).",
            "> It CANNOT and MUST NOT be installed as an OpenCore EFI kext.",
            "> Review each step below carefully before running commands with elevated permissions.",
            "",
            "## Required Prerequisites",
            "1. Boot your Mac using the updated OpenCore EFI.",
            "2. Ensure System Integrity Protection (SIP) is configured with `<430A0000>`.",
            "3. Ensure Apple Secure Boot is disabled (`SecureBootModel: Disabled`).",
            "",
            "## Execution Steps",
            "",
        ]

        for act in actions:
            lines.append(f"### Step {act.step_number}: {act.title}")
            lines.append(act.description)
            lines.append("")
            lines.append("```bash")
            lines.append(act.command_line)
            lines.append("```")
            lines.append("")
            if act.rollback_command:
                lines.append(f"*Rollback command for this step:* `{act.rollback_command}`")
                lines.append("")

        lines.extend([
            "## Recovery and Rollback",
            "If your system encounters a bootloop or kernel panic after installation:",
            "1. Restart the machine and hold the OpenCore boot picker.",
            "2. Press Spacebar and boot into Recovery Mode or Safe Mode (boot-arg `-x` or `-nvrmnogo`).",
            "3. Open Terminal in Recovery and run:",
            "```bash",
            "sudo /Library/GPUBundles/nullmoth-nvidia/pkgroot/uninstall.sh",
            "# Or remove manually:",
            "sudo rm -rf /Library/Extensions/NVRM* /Library/Extensions/NVAccel*",
            "sudo kmutil clear-staging",
            "```",
            "4. Reboot normally.",
        ])

        return "\n".join(lines)

    @classmethod
    def stage_package(cls, staging_dir: str, actions: List[ExternalAction], driver_name: str) -> str:
        """Creates staging directory and writes instruction guide."""
        os.makedirs(staging_dir, exist_ok=True)
        guide_content = cls.generate_instruction_guide(actions, driver_name)
        guide_path = os.path.join(staging_dir, "EXTERNAL_INSTALL_GUIDE.md")
        with open(guide_path, "w", encoding="utf-8") as f:
            f.write(guide_content)
        return guide_path
