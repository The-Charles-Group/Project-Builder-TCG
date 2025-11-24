import { Filter, X } from 'lucide-react';
import { useStore } from '../state/store';
import { getFilteredModuleCount } from '../state/selectors';
import { announceToScreenReader } from '../lib/a11y';
import type { EffortSize } from '../domain/models';

export function FilterBar() {
  const scope = useStore((state) => state.scope);
  const filters = useStore((state) => state.filters);
  const setFilters = useStore((state) => state.setFilters);
  const clearFilters = useStore((state) => state.clearFilters);

  if (!scope) return null;

  const filteredCount = getFilteredModuleCount(scope.modules, filters);
  const totalCount = scope.modules.length;
  const hasActiveFilters = Object.keys(filters).some((key) => {
    const value = filters[key as keyof typeof filters];
    return Array.isArray(value) && value.length > 0;
  });

  const handleFilterChange = (filterType: keyof typeof filters, value: string) => {
    const currentValues = filters[filterType] as string[] | undefined || [];
    const newValues = currentValues.includes(value)
      ? currentValues.filter((v) => v !== value)
      : [...currentValues, value];

    const newFilters = { ...filters, [filterType]: newValues };
    setFilters(newFilters);
    
    announceToScreenReader(`Filter applied. Showing ${filteredCount} of ${totalCount} modules.`);
  };

  const handleClearFilters = () => {
    clearFilters();
    announceToScreenReader(`Filters cleared. Showing all ${totalCount} modules.`);
  };

  return (
    <div className="mb-6 p-4 rounded-lg bg-primary-card border border-primary-border">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-accent-blue" />
          <h2 className="text-lg font-semibold text-primary-text">Filters</h2>
          <span className="text-sm text-muted">
            ({filteredCount} of {totalCount} modules)
          </span>
        </div>
        {hasActiveFilters && (
          <button
            onClick={handleClearFilters}
            className="flex items-center gap-1 text-sm text-accent-blue hover:underline"
          >
            <X className="w-4 h-4" />
            Clear All
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Phase Filter */}
        <div>
          <label className="block text-sm font-medium text-muted mb-2">Phase</label>
          <div className="space-y-2">
            {['Discovery', 'Concept', 'Review', 'Production'].map((phase) => (
              <label key={phase} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.phase?.includes(phase) || false}
                  onChange={() => handleFilterChange('phase', phase)}
                  className="w-4 h-4 rounded border-primary-border bg-input-bg text-accent-blue focus:ring-2 focus:ring-accent-blue"
                />
                <span className="text-sm text-primary-text">{phase}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Effort Filter */}
        <div>
          <label className="block text-sm font-medium text-muted mb-2">Effort Size</label>
          <div className="space-y-2">
            {(['S', 'M', 'L'] as EffortSize[]).map((size) => (
              <label key={size} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={filters.effort?.includes(size) || false}
                  onChange={() => handleFilterChange('effort', size)}
                  className="w-4 h-4 rounded border-primary-border bg-input-bg text-accent-blue focus:ring-2 focus:ring-accent-blue"
                />
                <span className="text-sm text-primary-text">
                  {size === 'S' && 'Small (≤120h)'}
                  {size === 'M' && 'Medium (≤400h)'}
                  {size === 'L' && 'Large (>400h)'}
                </span>
              </label>
            ))}
          </div>
        </div>

        {/* Risk Filter */}
        <div>
          <label className="block text-sm font-medium text-muted mb-2">Risk Status</label>
          <div className="space-y-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.risk?.includes('hasRisk') || false}
                onChange={() => handleFilterChange('risk', 'hasRisk')}
                className="w-4 h-4 rounded border-primary-border bg-input-bg text-accent-blue focus:ring-2 focus:ring-accent-blue"
              />
              <span className="text-sm text-primary-text">Has Risks</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={filters.risk?.includes('noRisk') || false}
                onChange={() => handleFilterChange('risk', 'noRisk')}
                className="w-4 h-4 rounded border-primary-border bg-input-bg text-accent-blue focus:ring-2 focus:ring-accent-blue"
              />
              <span className="text-sm text-primary-text">No Risks</span>
            </label>
          </div>
        </div>

        {/* Placeholder for Department (future) */}
        <div>
          <label className="block text-sm font-medium text-muted mb-2">Department</label>
          <div className="text-sm text-muted">
            (Coming soon)
          </div>
        </div>
      </div>
    </div>
  );
}
