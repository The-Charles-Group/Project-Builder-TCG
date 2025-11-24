import { X } from 'lucide-react';
import { useStore } from '../../state/store';
import type { EffortSize } from '../../domain/models';

export function FilterBar() {
  const filters = useStore((state) => state.filters);
  const setFilters = useStore((state) => state.setFilters);
  const clearFilters = useStore((state) => state.clearFilters);
  const filteredCount = useStore((state) => state.getFilteredModules().length);
  const totalCount = useStore((state) => state.scope.modules.length);
  
  const hasFilters = filters.phase.length > 0 || filters.effort.length > 0 || filters.risk.length > 0 || filters.dept.length > 0;
  
  const phases = ['Discovery', 'Concept', 'Review', 'Production'];
  const efforts: EffortSize[] = ['S', 'M', 'L'];
  const depts = ['Strategy', 'Creative', 'Production', 'Operations'];
  
  const toggleFilter = <K extends keyof typeof filters>(
    key: K,
    value: typeof filters[K][number]
  ) => {
    const current = filters[key] as string[];
    const newValue = current.includes(value as string)
      ? current.filter((v) => v !== value)
      : [...current, value as string];
    setFilters({ [key]: newValue });
  };
  
  return (
    <div className="bg-exec-card border-b border-exec-border px-6 py-4">
      <div className="max-w-[1920px] mx-auto">
        <div className="flex items-center justify-between gap-4 mb-3">
          <h2 className="text-sm font-semibold text-exec-text uppercase tracking-wide">Filters</h2>
          {hasFilters && (
            <button
              onClick={clearFilters}
              className="text-xs text-exec-accent hover:text-exec-accent/80 transition-colors flex items-center gap-1"
            >
              <X className="w-3 h-3" />
              Clear all
            </button>
          )}
        </div>
        
        <div className="flex flex-wrap gap-6">
          {/* Phase filter */}
          <div>
            <label className="text-xs text-exec-muted block mb-2">Phase</label>
            <div className="flex gap-2">
              {phases.map((phase) => (
                <button
                  key={phase}
                  onClick={() => toggleFilter('phase', phase)}
                  className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                    filters.phase.includes(phase)
                      ? 'bg-exec-accent text-white border-exec-accent'
                      : 'bg-exec-bg text-exec-text border-exec-border hover:border-exec-accent'
                  }`}
                >
                  {phase}
                </button>
              ))}
            </div>
          </div>
          
          {/* Effort filter */}
          <div>
            <label className="text-xs text-exec-muted block mb-2">Effort</label>
            <div className="flex gap-2">
              {efforts.map((effort) => (
                <button
                  key={effort}
                  onClick={() => toggleFilter('effort', effort)}
                  className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                    filters.effort.includes(effort)
                      ? 'bg-exec-accent text-white border-exec-accent'
                      : 'bg-exec-bg text-exec-text border-exec-border hover:border-exec-accent'
                  }`}
                >
                  {effort}
                </button>
              ))}
            </div>
          </div>
          
          {/* Risk filter */}
          <div>
            <label className="text-xs text-exec-muted block mb-2">Risk</label>
            <div className="flex gap-2">
              <button
                onClick={() => toggleFilter('risk', 'hasRisk')}
                className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                  filters.risk.includes('hasRisk')
                    ? 'bg-exec-accent text-white border-exec-accent'
                    : 'bg-exec-bg text-exec-text border-exec-border hover:border-exec-accent'
                }`}
              >
                Has risk
              </button>
              <button
                onClick={() => toggleFilter('risk', 'noRisk')}
                className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                  filters.risk.includes('noRisk')
                    ? 'bg-exec-accent text-white border-exec-accent'
                    : 'bg-exec-bg text-exec-text border-exec-border hover:border-exec-accent'
                }`}
              >
                No risk
              </button>
            </div>
          </div>
          
          {/* Department filter */}
          <div>
            <label className="text-xs text-exec-muted block mb-2">Department</label>
            <div className="flex gap-2">
              {depts.map((dept) => (
                <button
                  key={dept}
                  onClick={() => toggleFilter('dept', dept)}
                  className={`px-3 py-1.5 text-xs rounded border transition-colors ${
                    filters.dept.includes(dept)
                      ? 'bg-exec-accent text-white border-exec-accent'
                      : 'bg-exec-bg text-exec-text border-exec-border hover:border-exec-accent'
                  }`}
                >
                  {dept}
                </button>
              ))}
            </div>
          </div>
        </div>
        
        <div
          className="mt-3 text-xs text-exec-muted"
          role="status"
          aria-live="polite"
        >
          Showing {filteredCount} of {totalCount} modules
        </div>
      </div>
    </div>
  );
}
