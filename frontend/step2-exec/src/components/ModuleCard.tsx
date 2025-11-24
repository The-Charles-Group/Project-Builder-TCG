import { AlertCircle, Link2, ChevronDown, ChevronUp, Check } from 'lucide-react';
import type { Module } from '../domain/models';
import { formatHoursRange } from '../domain/models';
import { cn } from '../lib/cn';
import { truncate } from '../lib/format';

interface ModuleCardProps {
  module: Module;
  isExpanded: boolean;
  isSelected: boolean;
  onToggleExpand: () => void;
  onToggleSelect: () => void;
  onOpenDetails: () => void;
}

export function ModuleCard({
  module,
  isExpanded,
  isSelected,
  onToggleExpand,
  onToggleSelect,
  onOpenDetails,
}: ModuleCardProps) {
  const hasRisks = (module.risks?.length || 0) > 0;
  const hasDependencies = (module.dependencies?.length || 0) > 0;
  const visibleOutputs = module.outputs.slice(0, 3);
  const remainingOutputs = module.outputs.length - 3;

  const effortDisplay = module.effort?.size
    ? module.effort.size
    : formatHoursRange(module.effort?.hoursMin, module.effort?.hoursMax);

  return (
    <article
      className={cn(
        "card hover:border-accent-blue/50 transition-all",
        isSelected && "border-accent-blue ring-2 ring-accent-blue/20"
      )}
      aria-labelledby={`module-title-${module.id}`}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex-1 min-w-0">
          <h3
            id={`module-title-${module.id}`}
            className="text-xl font-semibold text-primary-text mb-1 cursor-pointer hover:text-accent-blue"
            onClick={onOpenDetails}
          >
            {module.title}
          </h3>
          <p className="text-sm text-muted line-clamp-2">
            {module.valueStatement}
          </p>
        </div>

        {/* Effort badge */}
        <div
          className={cn(
            "flex items-center justify-center px-3 py-1 rounded-full text-xs font-semibold",
            module.effort?.size === "S" && "bg-green-500/20 text-green-400 border border-green-500/30",
            module.effort?.size === "M" && "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
            module.effort?.size === "L" && "bg-red-500/20 text-red-400 border border-red-500/30",
            !module.effort?.size && "bg-selection-bg text-muted border border-selection-border"
          )}
        >
          {effortDisplay}
        </div>
      </div>

      {/* Outputs chips */}
      <div className="flex items-center gap-2 flex-wrap mb-4">
        {visibleOutputs.map((output) => (
          <span
            key={output.id}
            className="chip text-xs"
            title={output.label}
          >
            {truncate(output.label, 25)}
          </span>
        ))}
        {remainingOutputs > 0 && (
          <button
            className="chip text-xs hover:bg-accent-blue/10 hover:border-accent-blue/50"
            onClick={onOpenDetails}
            aria-label={`View ${remainingOutputs} more outputs`}
          >
            +{remainingOutputs}
          </button>
        )}
      </div>

      {/* Indicators */}
      <div className="flex items-center gap-4 mb-4 text-xs">
        {hasDependencies && (
          <div className="flex items-center gap-1 text-accent-blue">
            <Link2 className="w-4 h-4" />
            <span>{module.dependencies?.length} dependencies</span>
          </div>
        )}
        {hasRisks && (
          <div className="flex items-center gap-1 text-yellow-400">
            <AlertCircle className="w-4 h-4" />
            <span>{module.risks?.length} risks</span>
          </div>
        )}
        {module.phase && (
          <div className="text-muted">
            Phase: {module.phase}
          </div>
        )}
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="mt-4 pt-4 border-t border-primary-border space-y-3">
          {/* Activities */}
          {module.activities.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-primary-text mb-2">Activities</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted">
                {module.activities.map((activity, idx) => (
                  <li key={idx}>{activity}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Risks */}
          {module.risks && module.risks.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-yellow-400 mb-2 flex items-center gap-1">
                <AlertCircle className="w-4 h-4" />
                Risks
              </h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted">
                {module.risks.map((risk, idx) => (
                  <li key={idx}>{risk}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Assumptions */}
          {module.assumptions && module.assumptions.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-primary-text mb-2">Assumptions</h4>
              <ul className="list-disc list-inside space-y-1 text-sm text-muted">
                {module.assumptions.map((assumption, idx) => (
                  <li key={idx}>{assumption}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-3 mt-4 pt-4 border-t border-primary-border">
        <button
          onClick={onOpenDetails}
          className="btn-sm flex items-center gap-1 flex-1"
        >
          See Details
        </button>
        <button
          onClick={onToggleExpand}
          className="btn-sm flex items-center gap-1"
          aria-label={isExpanded ? "Collapse" : "Expand"}
          aria-expanded={isExpanded}
        >
          {isExpanded ? (
            <>
              <ChevronUp className="w-4 h-4" />
              Collapse
            </>
          ) : (
            <>
              <ChevronDown className="w-4 h-4" />
              Expand
            </>
          )}
        </button>
        <button
          onClick={onToggleSelect}
          className={cn(
            "btn-sm flex items-center gap-1",
            isSelected && "bg-accent-blue text-primary-bg border-accent-blue"
          )}
          aria-label={isSelected ? "Deselect" : "Select"}
          aria-pressed={isSelected}
        >
          <Check className="w-4 h-4" />
          {isSelected ? "Selected" : "Select"}
        </button>
      </div>
    </article>
  );
}
