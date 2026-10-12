# Dependency and conflict resolution for experimental drivers
from typing import Dict, List, Set, Tuple, Optional
from ..models.driver import DriverDefinition, InstallationType
from ..models.compatibility_result import CompatibilityReportItem

class DependencyResolver:
    @staticmethod
    def resolve_conflicts(
        selected_drivers: List[DriverDefinition],
        active_kexts: List[str],
    ) -> Tuple[List[str], List[str]]:
        """Identifies conflicting kexts that must be disabled, and any unresolvable conflicts.
        Returns: (kexts_to_disable, blocking_errors)
        """
        kexts_to_disable: Set[str] = set()
        blocking_errors: List[str] = []

        driver_ids = [d.id for d in selected_drivers]

        # WhateverGreen vs WhateverXe mutual exclusion
        if "whateverxe" in driver_ids:
            if "WhateverGreen" in active_kexts:
                kexts_to_disable.add("WhateverGreen")

        for driver in selected_drivers:
            for conflict in driver.conflicts:
                if conflict in active_kexts:
                    kexts_to_disable.add(conflict)

        return list(kexts_to_disable), blocking_errors

    @staticmethod
    def resolve_dependencies(selected_drivers: List[DriverDefinition]) -> List[str]:
        """Returns list of required kexts/components needed by the selected drivers."""
        deps: Set[str] = set()
        for driver in selected_drivers:
            for dep in driver.dependencies:
                deps.add(dep)
        return list(deps)
