import { Download, Copy } from 'lucide-react';
import { useStore } from '../state/store';
import { calculateSelectedHours } from '../state/selectors';
import { formatNumber } from '../lib/format';
import { cn } from '../lib/cn';

export function StickySummaryBar() {
  const scope = useStore((state) => state.scope);
  const selectedModuleIds = useStore((state) => state.selectedModuleIds);

  const selectedCount = selectedModuleIds.size;
  const totalHours = calculateSelectedHours(scope, selectedModuleIds);

  if (selectedCount === 0) return null;

  const handleCopySummary = () => {
    if (!scope) return;

    const selectedModules = scope.modules.filter((m) => selectedModuleIds.has(m.id));
    const summary = selectedModules
      .map((m) => {
        const outputs = m.outputs.map((o) => `- ${o.label}`).join('\n  ');
        return `${m.title}\n  ${outputs}`;
      })
      .join('\n\n');

    navigator.clipboard.writeText(summary).then(() => {
      alert('Summary copied to clipboard!');
    });
  };

  const handleExportSelected = () => {
    // TODO: Implement export functionality
    alert('Export selected modules functionality coming soon');
  };

  return (
    <div
      className={cn(
        "fixed bottom-0 left-0 right-0 z-50",
        "bg-primary-card/95 backdrop-blur border-t border-primary-border",
        "shadow-lg"
      )}
    >
      <div className="mx-auto max-w-7xl px-6 py-4">
        <div className="flex items-center justify-between gap-6">
          {/* Left: Selection info */}
          <div className="flex items-center gap-6">
            <div>
              <div className="text-sm text-muted">Modules Selected</div>
              <div className="text-xl font-semibold text-accent-blue">
                {selectedCount}
              </div>
            </div>
            <div className="h-8 w-px bg-primary-border" aria-hidden="true" />
            <div>
              <div className="text-sm text-muted">Estimated Hours</div>
              <div className="text-xl font-semibold text-accent-green">
                {totalHours !== undefined ? formatNumber(totalHours) : 'N/A'}
              </div>
            </div>
          </div>

          {/* Right: Actions */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleCopySummary}
              className="btn-ghost flex items-center gap-2"
            >
              <Copy className="w-4 h-4" />
              Copy Summary
            </button>
            <button
              onClick={handleExportSelected}
              className="btn-primary flex items-center gap-2"
            >
              <Download className="w-4 h-4" />
              Export Selected
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
