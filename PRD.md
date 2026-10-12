# PRD — OpCore-Simplify Experimental Driver Integration System

**Project:** OpCore-Simplify Experimental Driver Integration  
**Type:** Open-source tooling enhancement  
**Primary Language:** Python (follow the existing upstream project conventions)  
**Target Platform:** Windows, Linux, macOS where supported by the existing tooling  
**Target Bootloader:** OpenCore  
**Status:** Proposed  
**Priority:** High  
**Primary Objective:** Integrate experimental Intel Xe-LP and NVIDIA macOS driver projects into OpCore-Simplify through a modular, versioned, compatibility-aware driver management system.

---

## 1. Executive Summary

Extend the existing OpCore-Simplify project with an optional `ExperimentalDrivers` subsystem.

The subsystem must allow users to discover, inspect, track, and selectively integrate experimental graphics-driver projects into their Hackintosh configuration workflow.

Initial upstream projects:

1. `https://github.com/b00t0x/WhateverXe`
2. `https://github.com/nullmoth/nvidia-macos-driver`

The system must preserve OpCore-Simplify's existing functionality and architecture. Experimental driver integration must be optional and isolated from the standard EFI generation pipeline.

The system must not assume that the presence of a GPU Device ID in a source-code table means that its driver backend is implemented or that graphics acceleration works.

### Primary goals

- Detect and report relevant PCI hardware identifiers.
- Maintain a registry of experimental driver projects.
- Track upstream releases and commits.
- Analyze compatibility between hardware, macOS versions, and driver capabilities.
- Distinguish catalogued devices from implemented backends and verified acceleration.
- Generate an EFI configuration and installation manifest where applicable.
- Support reproducible installations, validation, logging, rollback, and offline operation.
- Provide a foundation for future experimental drivers without hardcoding every driver into the core application.

### Non-goals

- Developing a new GPU driver.
- Guaranteeing that unsupported hardware will work through Device ID spoofing.
- Automatically patching arbitrary macOS system files without explicit user authorization.
- Treating NVIDIA drivers as OpenCore kexts when they require a separate installation mechanism.
- Claiming QE/CI, Metal, OpenGL, video acceleration, HDMI, or sleep/wake support without evidence.

---

## 2. Target Hardware and Test Scenario

Primary research configuration:

- Laptop: HP Victus 15
- CPU: Intel Core i5-12500H
- Integrated graphics: Intel Iris Xe / Alder Lake-H
- Discrete graphics: NVIDIA GeForce RTX 3050 Mobile
- Target operating system: macOS Sequoia 15.x
- Bootloader: OpenCore

This is an experimental test profile, not a declaration of hardware compatibility.

The implementation must remain hardware-agnostic and support other machines through data-driven profiles.

### Required hardware information

Collect, when available:

- PCI vendor ID and device ID.
- PCI subsystem vendor and subsystem device IDs.
- GPU family and architecture.
- Integrated/discrete GPU classification.
- ACPI device path.
- Display connector routing, when known.
- macOS version and build.
- OpenCore version.
- Boot arguments and loaded kext inventory.
- Driver package version and upstream commit.
- Hardware-specific validation evidence.

Do not infer HDMI routing solely from the laptop model or GPU names.

---

## 3. System Architecture

Create a modular subsystem that integrates with existing OpCore-Simplify components.

Before implementation, inspect the upstream repository's directory structure, entry points, hardware detection pipeline, kext management, configuration generation, download mechanisms, and existing compatibility rules.

Do not rewrite existing modules or introduce a second configuration pipeline unnecessarily.

Suggested logical modules:

```text
ExperimentalDrivers/
├── registry/
│   ├── driver_registry
│   └── source_definitions
├── models/
│   ├── driver
│   ├── hardware_profile
│   ├── compatibility_result
│   └── install_manifest
├── sources/
│   ├── github_source
│   ├── whateverxe_source
│   └── nvidia_driver_source
├── detection/
│   ├── pci_inventory
│   └── hardware_matcher
├── compatibility/
│   ├── macos_version_checker
│   ├── backend_status_checker
│   └── compatibility_engine
├── planning/
│   ├── installation_planner
│   └── dependency_resolver
├── integration/
│   ├── opencore_integrator
│   └── external_installer_adapter
├── validation/
│   ├── package_validator
│   ├── plist_validator
│   └── manifest_validator
├── rollback/
│   └── rollback_manager
├── reporting/
│   └── compatibility_report
└── tests/
```

The directory names are proposals. Adapt them to the repository's actual Python package conventions and existing module organization.

Avoid creating empty abstraction layers that have no immediate use.

### Core components

**Driver Registry**

Stores metadata about supported experimental driver sources.

**Source Adapter**

Retrieves release metadata, commits, documentation, checksums when available, and package assets.

**Hardware Matcher**

Matches detected PCI identifiers against driver-provided hardware tables and compatibility rules.

**Compatibility Engine**

Determines whether the hardware, macOS version, driver version, dependencies, and backend implementation are suitable for a proposed configuration.

**Installation Planner**

Produces a plan without modifying the system or EFI.

**OpenCore Integrator**

Updates the EFI configuration only for components that actually belong in the OpenCore-managed configuration.

**External Installer Adapter**

Describes installation requirements for drivers that require system extensions, privileged installers, root patches, or other post-boot operations.

**Validation and Rollback**

Validates generated artifacts, records changes, and restores the previous state when possible.

---

## 4. Driver Registry

Use a structured, version-controlled registry.

Example schema:

```json
{
  "id": "whateverxe",
  "name": "WhateverXe",
  "repository": "https://github.com/b00t0x/WhateverXe",
  "category": "intel-graphics",
  "installation_type": "opencore-kext",
  "support_status": "experimental",
  "macos_versions": [],
  "hardware_families": [],
  "requires_root_patch": false,
  "requires_privileged_installation": false,
  "conflicts": [
    "WhateverGreen"
  ],
  "version_policy": "pinned",
  "automatic_installation_allowed": false
}
```

The schema above is illustrative, not authoritative metadata for the upstream project. Populate actual fields only after inspecting source code and official documentation.

Support installation types such as:

- `opencore-kext`
- `root-patch`
- `system-extension`
- `external-installer`
- `manual-only`

Do not assume every driver package uses the same installation mechanism.

### Registry requirements

- Unique driver identifiers.
- Source repository URL.
- Installation type.
- Supported macOS versions and builds, when verified.
- Supported hardware families and device IDs.
- Backend implementation status.
- Known conflicts.
- Required dependencies.
- Security and privilege requirements.
- Latest observed upstream release or commit.
- Last verification timestamp.
- Source evidence references.
- Explicit experimental status.

The registry must support additional driver projects without modifying the core compatibility engine.

---

## 5. Upstream Update Management

Implement upstream tracking for both initial repositories.

### Required capabilities

- Retrieve GitHub release metadata where available.
- Track commit hashes when a project has no formal release.
- Compare upstream versions with the locally pinned version.
- Display changelog and changed-file summaries.
- Record source URLs and retrieval timestamps.
- Verify package checksums or signatures when published.
- Cache downloaded artifacts.
- Support offline inspection of previously downloaded metadata.
- Allow the user to pin a release or commit.
- Generate an update report before changing installed artifacts.

Do not use an arbitrary branch's latest commit as an automatically trusted production version.

### Update states

- `up_to_date`
- `update_available`
- `release_not_found`
- `source_unavailable`
- `verification_failed`
- `breaking_change_suspected`
- `manual_review_required`

### Update policy

Default to pinned versions.

Never silently replace an installed driver, change boot arguments, overwrite EFI files, or execute upstream installation scripts.

Treat repository content, release notes, scripts, and metadata as untrusted input.

---

## 6. Compatibility Engine

This is the most important subsystem.

A device match is not equivalent to a working driver.

### Required compatibility dimensions

1. PCI device identification.
2. GPU architecture.
3. Backend implementation status.
4. Supported macOS version and build.
5. Required kernel interfaces and frameworks.
6. Driver dependencies.
7. Conflicting kexts or patches.
8. Installation mechanism.
9. Known hardware-specific limitations.
10. Verification evidence.

### Backend states

Use explicit states:

- `unknown`
- `catalogued`
- `backend_implemented`
- `build_verified`
- `runtime_verified`
- `acceleration_verified`
- `partially_supported`
- `unsupported`

These states must not be automatically promoted merely because a device ID appears in a source-code table.

### Compatibility outcomes

- `verified`: matching hardware, operating system, driver version, and relevant functionality have evidence of successful testing.
- `conditional`: compatibility depends on documented requirements or configuration.
- `experimental`: a plausible implementation exists, but relevant functionality is not adequately verified.
- `unsupported`: known incompatible or explicitly unsupported.
- `unknown`: insufficient evidence.

The engine must include a human-readable explanation and source references for every result.

### Example

For an Alder Lake-H device:

```text
GPU family: Alder Lake-H
PCI match: detected or manually supplied
Device catalog entry: found / not found
Backend implementation: unknown / implemented
macOS build: matched / unmatched / unknown
Hardware acceleration: verified / unverified
HDMI output: verified / unverified
Overall result: experimental / unknown / unsupported
```

Do not claim support based solely on a matching PCI ID.

---

## 7. WhateverXe Integration

Repository:

`https://github.com/b00t0x/WhateverXe`

### Requirements

- Read the upstream project metadata and source files.
- Identify supported device families and PCI IDs.
- Parse backend and GPU-family enumerations where practical.
- Identify whether each device is only catalogued or has an implemented backend.
- Track supported macOS builds.
- Identify kext dependencies and conflicts.
- Determine whether the selected release is compatible with the existing OpenCore environment.
- Include a source-evidence link for every detected hardware match.
- Generate an installation plan before modifying EFI.

### Important conflict rule

If the selected WhateverXe version explicitly conflicts with WhateverGreen, the compatibility engine must flag the conflict and prevent both from being enabled simultaneously.

Do not assume that disabling one kext is sufficient to make WhateverXe compatible with an otherwise unsupported GPU.

### Alder Lake-H acceptance requirement

For the HP Victus i5-12500H profile, the system must not label Intel Iris Xe acceleration as supported until a suitable backend and relevant runtime behavior have been verified.

Device ID spoofing may be represented as an optional experimental test configuration. It must not be treated as a compatibility fix or a production recommendation.

---

## 8. NVIDIA macOS Driver Integration

Repository:

`https://github.com/nullmoth/nvidia-macos-driver`

### Requirements

- Inspect the repository's actual implementation, supported GPUs, operating system versions, and installation mechanism.
- Determine whether the project installs a kext, system extension, framework bundle, root patch, or another component.
- Record the installation destination and privilege requirements.
- Track driver dependencies and conflicts.
- Distinguish source compilation from successful runtime initialization.
- Report the evidence supporting each claimed GPU and macOS combination.
- Generate a separate installation plan when the driver does not belong in EFI.

### Safety requirements

The integration must not assume that an NVIDIA driver is safe merely because its repository builds successfully.

Before installation, require explicit confirmation for:

- Privileged operations.
- System-extension or kernel-extension installation.
- Root patching.
- Changes to protected system locations.
- Changes that may affect boot or display initialization.

Provide a clear rollback plan and preserve the original EFI.

### RTX 3050 Mobile profile

The compatibility engine must not classify the RTX 3050 Mobile as supported unless there is sufficient evidence for that exact GPU family, driver version, and macOS build.

If the driver is experimental, display that status prominently and default to manual review.

Do not automatically inject arbitrary NVIDIA boot arguments or spoof GPU identifiers.

---

## 9. Installation Planning and EFI Generation

Use a two-stage workflow.

### Stage A: Plan

Generate a report describing:

- Detected hardware.
- Proposed drivers.
- Exact versions and commits.
- Compatibility evidence.
- Known conflicts.
- Required changes.
- Installation destinations.
- Required privileges.
- Recovery instructions.

This stage must not modify the EFI or operating system.

### Stage B: Apply

Only proceed after explicit user confirmation.

- Back up the current EFI.
- Record the current OpenCore configuration.
- Apply minimal, deterministic changes.
- Update the correct installation destination.
- Validate the resulting `config.plist`.
- Validate file references and required dependencies.
- Generate a change manifest.
- Verify that rollback information exists.

Never mix system-installed NVIDIA components into the OpenCore EFI unless the upstream driver explicitly requires that arrangement.

### Output artifacts

```text
BuildOutput/
├── EFI/
├── compatibility-report.json
├── compatibility-report.md
├── install-manifest.json
├── changes.diff
├── upstream-lock.json
└── rollback/
```

Adapt the output layout to the existing OpCore-Simplify conventions.

Do not include secrets, private keys, or unrelated system information in reports.

---

## 10. Rollback and Recovery

The system must maintain an explicit record of every file it creates, replaces, or removes.

Rollback requirements:

- Preserve a copy of the original EFI.
- Restore the previous configuration when possible.
- Remove only files owned by the integration subsystem.
- Never delete unrelated kexts or user modifications.
- Detect when the current state differs from the recorded backup.
- Report when manual recovery is necessary.
- Never claim that an EFI backup guarantees recovery from every system-level patch.

For root patches or system-installed drivers, rollback must use a separately defined recovery workflow. EFI rollback alone is insufficient.

---

## 11. User Interface and Reporting

Follow the existing OpCore-Simplify interface conventions.

Add an optional experimental driver section.

Suggested information per driver:

- Driver name and upstream repository.
- Installed and available versions.
- Hardware match.
- Backend implementation status.
- macOS compatibility.
- Installation type.
- Conflicts and dependencies.
- Verification evidence.
- Last checked timestamp.

Available actions:

- `Inspect`
- `Check Updates`
- `View Compatibility`
- `Generate Plan`
- `Apply Changes`
- `Export Report`
- `Rollback`

`Apply Changes` must remain disabled until all mandatory validations pass and the user has reviewed the plan.

Use neutral, precise status labels. Do not use a success indicator merely because a driver downloaded or its kext loaded.

---

## 12. Logging and Diagnostics

Provide structured diagnostic output.

Record:

- Detected hardware IDs.
- Driver source and commit.
- macOS version and build.
- Compatibility checks and evidence.
- Proposed changes.
- Validation results.
- Installation errors.
- Rollback status.

Support redaction of sensitive information before exporting reports.

The system must not collect or upload diagnostics automatically.

---

## 13. Testing Strategy

### Unit tests

- PCI ID matching.
- Driver registry validation.
- Backend status parsing.
- macOS version comparison.
- Dependency resolution.
- Conflict detection.
- Version pinning.
- Manifest validation.
- Rollback manifest generation.

### Integration tests

- GitHub release and commit metadata retrieval.
- Missing release handling.
- Source unavailability.
- Malformed metadata.
- Invalid package checksum.
- OpenCore configuration validation.
- Dry-run installation.
- Interrupted installation recovery.

### Hardware compatibility tests

Do not require unsupported hardware to be present in CI.

Use fixture-based tests for known PCI IDs and backend states.

Actual GPU acceleration must be marked as hardware-tested only after validation on the corresponding hardware.

### Required test cases

1. Device ID exists but backend is unknown.
2. Backend is implemented but macOS build is unsupported.
3. Driver is compatible but a conflicting kext is enabled.
4. GitHub release is missing.
5. Upstream changes after a pinned version.
6. NVIDIA package requires a privileged installer.
7. EFI generation fails validation.
8. Rollback is requested after partial application.
9. Device ID spoofing is proposed for an unsupported GPU.
10. Both experimental drivers are selected simultaneously.

---

## 14. Acceptance Criteria

The project is ready for an initial release when:

- Existing OpCore-Simplify workflows continue to work.
- Both repositories can be registered without hardcoding their logic into unrelated modules.
- Hardware and driver compatibility are reported separately.
- Unknown backend states are handled conservatively.
- Updates are pinned and reproducible.
- Dry-run planning works without modifying the system.
- EFI changes can be reviewed before application.
- Conflicting kexts are detected.
- External installation mechanisms are represented correctly.
- Validation and rollback reports are generated.
- Automated tests pass.
- Documentation clearly distinguishes experimental claims from verified functionality.

No acceptance criterion requires the HP Victus i5-12500H or RTX 3050 Mobile to achieve graphics acceleration. That is a separate hardware research milestone.

---

## 15. Implementation Phases

### Phase 1 — Repository Audit

Inspect the current OpCore-Simplify architecture and document the actual integration points.

Deliverables:
- Existing module map.
- Hardware detection flow.
- Kext and patch management flow.
- EFI generation flow.
- Proposed minimal integration points.

Do not modify code in this phase.

### Phase 2 — Driver Registry

Implement source metadata, version pinning, update discovery, and driver models.

### Phase 3 — Compatibility Engine

Implement hardware matching, backend-state handling, conflict detection, and evidence-based reports.

### Phase 4 — Dry-Run Planner

Generate plans and manifests without making changes to EFI or system files.

### Phase 5 — WhateverXe Adapter

Integrate WhateverXe source metadata, hardware tables, dependencies, and compatibility information.

### Phase 6 — NVIDIA Adapter

Integrate NVIDIA project metadata and its actual installation requirements, preserving the distinction between EFI and system-level installation.

### Phase 7 — Validated Application and Rollback

Add controlled application, configuration validation, backup, rollback, and failure recovery.

### Phase 8 — Hardware Research

Test the HP Victus configuration separately. Document boot success, GPU initialization, acceleration, HDMI output, sleep/wake, and stability independently.

---

## 16. Instructions to the AI Coding Agent

You are working in an existing open-source project. Your responsibility is to extend it safely, not replace it.

Before writing code:

1. Inspect the actual repository and read its contribution instructions.
2. Map existing modules and data flows.
3. Read the current source code and documentation for both driver projects.
4. Verify their current support claims against the code and release history.
5. Identify the smallest maintainable integration design.
6. Write an implementation plan and identify assumptions.

During implementation:

- Follow existing naming, formatting, dependency, and testing conventions.
- Avoid unnecessary dependencies.
- Do not invent upstream APIs or driver capabilities.
- Do not copy entire upstream repositories into the project without a clear licensing and maintenance reason.
- Do not run privileged installation scripts.
- Do not modify the user's actual EFI automatically.
- Keep experimental integrations isolated behind explicit opt-in.
- Add tests alongside each implemented component.
- Make incremental changes and report what has actually been completed.

If upstream code is unavailable, incompatible, or insufficiently documented, report the limitation rather than guessing.

### Required final report from the agent

At completion, report:

1. Files created and modified.
2. Architecture decisions.
3. Implemented features.
4. Tests executed and results.
5. Upstream versions and commits inspected.
6. Known compatibility limitations.
7. Remaining work.
8. Exact instructions for running the tool in dry-run mode.
9. Recovery and rollback procedure.

**First task:** perform Phase 1 only. Produce a repository audit and a concrete implementation plan based on the actual source tree. Do not begin modifying files until the audit identifies the appropriate integration points.
