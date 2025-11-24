import { Info, Maximize2, Minimize2, Download, Share2 } from 'lucide-react';
import { useStore } from '../../state/store';
import { formatHours } from '../../lib/utils';

export function HeaderSummary() {
  const scope = useStore((state) => state.scope);
  const expandedIds = useStore((state) => state.expandedModuleIds);
  const expandAll = useStore((state) => state.expandAll);
  const collapseAll = useStore((state) => state.collapseAll);
  
  const allExpanded = expandedIds.size === scope.modules.length;
  
  return (
    <header className="bg-exec-card border-b border-exec-border px-6 py-4">
      <div className="max-w-[1920px] mx-auto">
        <div className="flex items-center justify-between gap-6">
          {/* Left: Title + metadata */}
          <div className="flex-1">
            <h1 className="text-2xl font-semibold text-exec-text mb-2">
              {scope.title}
            </h1>
            <div className="flex items-center gap-3 flex-wrap">
              {scope.channels && scope.channels.map((ch) => (
                <span key={ch} className="px-2 py-1 text-xs bg-navy-800 text-navy-200 rounded">
                  {ch}
                </span>
              ))}
              {scope.markets && scope.markets.map((m) => (
                <span key={m} className="px-2 py-1 text-xs bg-navy-800 text-navy-200 rounded">
                  {m}
                </span>
              ))}
              {scope.complexity && (
                <span className="px-2 py-1 text-xs bg-navy-800 text-navy-200 rounded">
                  Complexity: {scope.complexity}
                </span>
              )}
            </div>
          </div>
          
          {/* Middle: Total hours */}
          <div className="flex items-center gap-2 px-4 py-2 bg-exec-bg rounded border border-exec-border">
            <div className="text-right">
              <div className="text-xs text-exec-muted">Total Planned Hours</div>
              <div className="text-lg font-semibold text-exec-accent">
                {formatHours(scope.totalPlannedHours)}
              </div>
            </div>
            <button 
              className="p-1 hover:bg-exec-border rounded"
              title="How this is computed"
            >
              <Info className="w-4 h-4 text-exec-muted" />
            </button>
          </div>
          
          {/* Right: Actions */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => allExpanded ? collapseAll() : expandAll()}
              className="px-3 py-2 text-sm bg-exec-bg hover:bg-exec-border rounded border border-exec-border text-exec-text flex items-center gap-2 transition-colors"
            >
              {allExpanded ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
              {allExpanded ? 'Collapse all' : 'Expand all'}
            </button>
            <button className="px-3 py-2 text-sm bg-exec-bg hover:bg-exec-border rounded border border-exec-border text-exec-text flex items-center gap-2 transition-colors">
              <Download className="w-4 h-4" />
              Export
            </button>
            <button className="px-3 py-2 text-sm bg-exec-bg hover:bg-exec-border rounded border border-exec-border text-exec-text flex items-center gap-2 transition-colors">
              <Share2 className="w-4 h-4" />
              Share
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
