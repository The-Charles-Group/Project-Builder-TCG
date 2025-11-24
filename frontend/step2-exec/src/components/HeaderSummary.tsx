import { Download, Share2, ChevronDown, ChevronUp, Info } from 'lucide-react';
import { useStore } from '../state/store';
import { formatNumber } from '../lib/format';
import { cn } from '../lib/cn';

export function HeaderSummary() {
  const scope = useStore((state) => state.scope);
  const expandAll = useStore((state) => state.expandAll);
  const collapseAll = useStore((state) => state.collapseAll);

  if (!scope) return null;

  return (
    <header className="sticky top-0 z-40 border-b border-primary-border bg-primary-bg/95 backdrop-blur">
      <div className="mx-auto max-w-7xl px-6 py-4">
        <div className="flex items-center justify-between gap-6">
          {/* Left: Title & Metadata */}
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-semibold text-primary-text mb-2 truncate">
              {scope.title}
            </h1>
            <div className="flex items-center gap-3 flex-wrap">
              {scope.channels && scope.channels.map((channel) => (
                <span key={channel} className="chip text-xs">
                  {channel}
                </span>
              ))}
              {scope.markets && scope.markets.map((market) => (
                <span key={market} className="chip text-xs">
                  {market}
                </span>
              ))}
              {scope.complexity && (
                <span
                  className={cn(
                    "chip text-xs",
                    scope.complexity === "High" && "border-red-500/30 bg-red-500/10",
                    scope.complexity === "Medium" && "border-yellow-500/30 bg-yellow-500/10",
                    scope.complexity === "Low" && "border-green-500/30 bg-green-500/10"
                  )}
                >
                  {scope.complexity} Complexity
                </span>
              )}
            </div>
          </div>

          {/* Middle: Total Hours */}
          <div className="flex items-center gap-2 px-4 py-2 rounded-lg bg-selection-bg border border-selection-border">
            <Info className="w-4 h-4 text-muted" />
            <div className="text-right">
              <div className="text-xs text-muted">Total Planned</div>
              <div className="text-lg font-semibold text-accent-blue">
                {formatNumber(scope.totalPlannedHours)}h
              </div>
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={expandAll}
              className="btn-sm flex items-center gap-2"
              aria-label="Expand all modules"
            >
              <ChevronDown className="w-4 h-4" />
              Expand All
            </button>
            <button
              onClick={collapseAll}
              className="btn-sm flex items-center gap-2"
              aria-label="Collapse all modules"
            >
              <ChevronUp className="w-4 h-4" />
              Collapse All
            </button>
            <button
              onClick={() => window.print()}
              className="btn-ghost flex items-center gap-2"
              aria-label="Export summary"
            >
              <Download className="w-4 h-4" />
              Export
            </button>
            <button
              onClick={() => {
                // TODO: Implement share functionality
                alert('Share functionality coming soon');
              }}
              className="btn-ghost flex items-center gap-2"
              aria-label="Share scope"
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
