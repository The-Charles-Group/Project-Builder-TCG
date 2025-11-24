import type { Module, ScopeSummary } from '../domain/models';
import type { Filters } from './store';

// ============================================================================
// Selectors for derived state
// ============================================================================

export function filterModules(modules: Module[], filters: Filters): Module[] {
  let filtered = modules;

  if (filters.phase && filters.phase.length > 0) {
    filtered = filtered.filter((m) =>
      m.phase && filters.phase?.includes(m.phase)
    );
  }

  if (filters.effort && filters.effort.length > 0) {
    filtered = filtered.filter((m) =>
      m.effort?.size && filters.effort?.includes(m.effort.size)
    );
  }

  if (filters.risk && filters.risk.length > 0) {
    filtered = filtered.filter((m) => {
      const hasRisks = (m.risks?.length || 0) > 0;
      return filters.risk?.includes(hasRisks ? "hasRisk" : "noRisk");
    });
  }

  return filtered;
}

export function calculateSelectedHours(
  scope: ScopeSummary | null,
  selectedIds: Set<string>
): number | undefined {
  if (!scope) return undefined;
  
  const selectedModules = scope.modules.filter((m) => selectedIds.has(m.id));
  
  const totalHours = selectedModules.reduce((sum, m) => {
    const hours = m.effort?.hoursMax || m.effort?.hoursMin;
    return sum + (hours || 0);
  }, 0);
  
  return totalHours > 0 ? totalHours : undefined;
}

export function getFilteredModuleCount(modules: Module[], filters: Filters): number {
  return filterModules(modules, filters).length;
}
