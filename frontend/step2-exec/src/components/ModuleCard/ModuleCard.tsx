import { ChevronDown, ChevronRight, Eye, CheckSquare, Square, AlertTriangle, Network } from 'lucide-react';
import type { Module } from '../../domain/models';
import { useStore } from '../../state/store';
import { cn, formatHoursRange } from '../../lib/utils';

interface ModuleCardProps {
  module: Module;
}

export function ModuleCard({ module }: ModuleCardProps) {
  const isExpanded = useStore((state) => state.expandedModuleIds.has(module.id));
  const isSelected = useStore((state) => state.selectedModuleIds.has(module.id));
  const toggleExpanded = useStore((state) => state.toggleExpanded);
  const toggleSelected = useStore((state) => state.toggleSelected);
  const openDrawer = useStore((state) => state.openDrawer);
  
  const effortLabel = module.effort?.size || 'M';
  const hoursRange = module.effort ? formatHoursRange(module.effort.hoursMin, module.effort.hoursMax) : null;
  const visibleOutputs = module.outputs.slice(0, 3);
  const overflowCount = module.outputs.length - 3;
  const riskCount = module.risks?.length || 0;
  const depsCount = module.dependencies?.length || 0;
  
  const handleCardClick = (e: React.MouseEvent) => {
    if ((e.target as HTMLElement).closest('button')) return;
    toggleExpanded(module.id);
  };
  
  const handleShiftClick = (e: React.MouseEvent) => {
    if (e.shiftKey) {
      toggleSelected(module.id);
    }
  };
  
  return (
    <div
      className={cn(
        "bg-exec-card border rounded-lg overflow-hidden transition-all duration-200",
        isSelected ? "border-exec-accent shadow-lg shadow-exec-accent/20" : "border-exec-border hover:border-exec-muted"
      )}
      onClick={handleShiftClick}
    >
      {/* Card header - always visible */}
      <div
        className="p-4 cursor-pointer select-none"
        onClick={handleCardClick}
      >
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-start gap-2 flex-1 min-w-0">
            {isExpanded ? (
              <ChevronDown className="w-5 h-5 text-exec-muted flex-shrink-0 mt-0.5" />
            ) : (
              <ChevronRight className="w-5 h-5 text-exec-muted flex-shrink-0 mt-0.5" />
            )}
            <h3 className="text-lg font-semibold text-exec-text leading-tight">
              {module.title}
            </h3>
          </div>
          
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={cn(
              "px-2 py-1 text-xs font-medium rounded",
              effortLabel === 'S' && "bg-green-900/30 text-green-300",
              effortLabel === 'M' && "bg-yellow-900/30 text-yellow-300",
              effortLabel === 'L' && "bg-red-900/30 text-red-300"
            )}>
              {effortLabel}
            </span>
          </div>
        </div>
        
        <p className="text-sm text-exec-muted mb-3 leading-relaxed">
          {module.valueStatement}
        </p>
        
        {/* Output chips */}
        <div className="flex flex-wrap gap-2 mb-3">
          {visibleOutputs.map((output) => (
            <span
              key={output.id}
              className="px-2 py-1 text-xs bg-exec-bg text-exec-text rounded border border-exec-border hover:border-exec-accent transition-colors cursor-default"
              title={output.label}
            >
              {output.label}
            </span>
          ))}
          {overflowCount > 0 && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                openDrawer(module.id);
              }}
              className="px-2 py-1 text-xs bg-exec-accent/10 text-exec-accent rounded border border-exec-accent/30 hover:bg-exec-accent/20 transition-colors"
            >
              +{overflowCount}
            </button>
          )}
        </div>
        
        {/* Metadata row */}
        <div className="flex items-center justify-between text-xs text-exec-muted">
          <div className="flex items-center gap-3">
            {riskCount > 0 && (
              <span className="flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                {riskCount}
              </span>
            )}
            {depsCount > 0 && (
              <span className="flex items-center gap-1">
                <Network className="w-3 h-3" />
                {depsCount}
              </span>
            )}
            {hoursRange && (
              <span>{hoursRange}</span>
            )}
          </div>
        </div>
      </div>
      
      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-exec-border p-4 bg-exec-bg/30">
          <div className="mb-3">
            <h4 className="text-xs font-semibold text-exec-muted uppercase tracking-wide mb-2">
              Activities
            </h4>
            <ul className="space-y-1">
              {module.activities.map((activity, idx) => (
                <li key={idx} className="text-sm text-exec-text leading-relaxed pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-exec-muted">
                  {activity}
                </li>
              ))}
            </ul>
          </div>
          
          <div className="flex items-center gap-2 pt-3 border-t border-exec-border/50">
            <button
              onClick={(e) => {
                e.stopPropagation();
                openDrawer(module.id);
              }}
              className="px-3 py-1.5 text-sm bg-exec-accent text-white rounded hover:bg-exec-accent/90 transition-colors flex items-center gap-1.5"
            >
              <Eye className="w-4 h-4" />
              See details
            </button>
            <button
              onClick={(e) => {
                e.stopPropagation();
                toggleSelected(module.id);
              }}
              className="px-3 py-1.5 text-sm bg-exec-bg text-exec-text rounded border border-exec-border hover:border-exec-accent transition-colors flex items-center gap-1.5"
            >
              {isSelected ? <CheckSquare className="w-4 h-4" /> : <Square className="w-4 h-4" />}
              {isSelected ? 'Selected' : 'Select'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
