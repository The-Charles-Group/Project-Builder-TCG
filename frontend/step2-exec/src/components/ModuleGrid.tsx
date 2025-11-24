import { useStore } from '../state/store';
import { filterModules } from '../state/selectors';
import { ModuleCard } from './ModuleCard';
import React from 'react';

export function ModuleGrid() {
  const scope = useStore((state) => state.scope);
  const filters = useStore((state) => state.filters);
  const expandedModuleIds = useStore((state) => state.expandedModuleIds);
  const selectedModuleIds = useStore((state) => state.selectedModuleIds);
  const toggleExpanded = useStore((state) => state.toggleExpanded);
  const toggleSelected = useStore((state) => state.toggleSelected);
  const openDrawer = useStore((state) => state.openDrawer);

  if (!scope) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <p className="text-muted">Loading scope data...</p>
      </div>
    );
  }

  const filteredModules = filterModules(scope.modules, filters);

  if (filteredModules.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] gap-3">
        <p className="text-muted text-lg">No modules match your filters</p>
        <button
          onClick={() => useStore.getState().clearFilters()}
          className="btn-ghost"
        >
          Clear Filters
        </button>
      </div>
    );
  }

  return (
    <div
      className="grid gap-6 auto-rows-fr"
      style={{
        gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
      }}
      role="list"
      aria-label="Module cards"
    >
      {filteredModules.map((module) => (
        <ModuleCard
          key={module.id}
          module={module}
          isExpanded={expandedModuleIds.has(module.id)}
          isSelected={selectedModuleIds.has(module.id)}
          onToggleExpand={() => toggleExpanded(module.id)}
          onToggleSelect={() => toggleSelected(module.id)}
          onOpenDetails={() => openDrawer(module.id)}
        />
      ))}
    </div>
  );
}
