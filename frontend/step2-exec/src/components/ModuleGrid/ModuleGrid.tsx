import { ModuleCard } from '../ModuleCard/ModuleCard';
import { useStore } from '../../state/store';

export function ModuleGrid() {
  const filteredModules = useStore((state) => state.getFilteredModules());
  
  if (filteredModules.length === 0) {
    return (
      <div className="text-center py-16">
        <p className="text-exec-muted text-lg">No modules match the current filters.</p>
        <button
          onClick={() => useStore.getState().clearFilters()}
          className="mt-4 px-4 py-2 bg-exec-accent text-white rounded hover:bg-exec-accent/90 transition-colors"
        >
          Clear filters
        </button>
      </div>
    );
  }
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 2xl:grid-cols-3 gap-4">
      {filteredModules.map((module) => (
        <ModuleCard key={module.id} module={module} />
      ))}
    </div>
  );
}
