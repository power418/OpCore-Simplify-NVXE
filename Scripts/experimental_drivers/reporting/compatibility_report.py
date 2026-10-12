# CompatibilityReport exporter generating compatibility-report.json and .md
import os
import json
from typing import Optional
from ..models.compatibility_result import CompatibilityReport

class ReportExporter:
    @staticmethod
    def to_markdown(report: CompatibilityReport) -> str:
        lines = [
            "# Experimental Driver Compatibility Report",
            "",
            f"**Generated:** {report.timestamp}  ",
            f"**Target macOS:** {report.target_macos_version} {f'({report.target_macos_build})' if report.target_macos_build else ''}  ",
            f"**Overall Outcome:** `{report.overall_outcome.value.upper()}`  ",
            f"**Safe to Plan (Dry-Run):** {'Yes' if report.safe_to_plan else 'No'}  ",
            "",
            "## 1. Hardware Summary",
            "",
            f"- **Platform:** {report.hardware_summary.get('platform', 'N/A')}",
            f"- **Motherboard:** {report.hardware_summary.get('motherboard', 'N/A')}",
            f"- **Processor:** {report.hardware_summary.get('cpu', 'N/A')}",
            f"- **Detected GPUs:** {', '.join(report.hardware_summary.get('gpus', []))}",
            "",
            "---",
            "",
            "## 2. Driver Evaluation Details",
            "",
        ]

        for item in report.items:
            lines.extend([
                f"### Driver: {item.driver_name} (`{item.driver_id}`)",
                "",
                f"- **Matched GPU:** {item.device.name} (`{item.device.formatted_id}`)",
                f"- **Hardware Family:** {item.matched_family or 'Unknown'}",
                f"- **Backend Status:** `{item.backend_status.value}`",
                f"- **Compatibility Outcome:** `{item.outcome.value.upper()}`",
                f"- **Hardware Acceleration:** {'Verified on physical hardware' if item.acceleration_verified else 'Unverified / Unsupported'}",
                f"- **Manual Review Required:** {'Yes' if item.manual_review_required else 'No'}",
                "",
                "#### Dimension Checks (10 PRD Dimensions)",
                "",
                "| Dimension | Status | Summary | Evidence |",
                "|---|---|---|---|",
            ])

            for dim in item.dimensions:
                st = "PASS" if dim.passed else "WARN / FAIL"
                ev = f"[Link]({dim.evidence_reference})" if dim.evidence_reference else "N/A"
                lines.append(f"| {dim.dimension_name} | `{st}` | {dim.summary} | {ev} |")

            lines.append("")

            if item.warnings:
                lines.extend([
                    "> [!WARNING]",
                    "> **Warnings and Hardware Limitations:**",
                ])
                for w in item.warnings:
                    lines.append(f"> - {w}")
                lines.append("")

            if item.reasons:
                lines.extend([
                    "> [!IMPORTANT]",
                    "> **Blocking Issues:**",
                ])
                for r in item.reasons:
                    lines.append(f"> - {r}")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## 3. Next Actions",
            "1. Review the evaluations above before running Stage A planning.",
            "2. Note that experimental status does not guarantee display output or graphics acceleration.",
            "3. Pinned driver versions ensure reproducible, auditable configurations.",
        ])

        return "\n".join(lines)

    @classmethod
    def export(cls, report: CompatibilityReport, output_dir: str = "BuildOutput") -> tuple[str, str]:
        os.makedirs(output_dir, exist_ok=True)
        json_path = os.path.join(output_dir, "compatibility-report.json")
        md_path = os.path.join(output_dir, "compatibility-report.md")

        with open(json_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(report.to_dict(), indent=2))

        with open(md_path, "w", encoding="utf-8") as f:
            f.write(cls.to_markdown(report))

        return json_path, md_path
