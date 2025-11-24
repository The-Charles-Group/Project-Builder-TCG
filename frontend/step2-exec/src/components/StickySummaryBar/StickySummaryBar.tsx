import { Copy, Download } from 'lucide-react';
import { useStore } from '../../state/store';
import { formatHours } from '../../lib/utils';

export function StickySummaryBar() {
  const selectedIds = useStore((state) => state.selectedModuleIds);
  const selectedHours = useStore((state) => state.getSelectedHours());
  const scope = useStore((state) => state.scope);
  
  if (selectedIds.size === 0) return null;
  
  const selectedModules = scope.modules.filter((m) => selectedIds.has(m.id));
  
  const copySummary = () => {
    const text = selectedModules.map((m) => {
      const outputs = m.outputs.map((o) => o.label).join(', ');
      return `${m.title}\n  Outputs: ${outputs}`;
    }).join('\n\n');
    
    navigator.clipboard.writeText(text);
  };
  
  return (
    <div className="fixed bottom-0 left-0 right-0 bg-exec-card border-t border-exec-border shadow-2xl">
      <div className="max-w-[1920px] mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="text-sm text-exec-text">
            <span className="font-semibold">{selectedIds.size}</span> modules selected
          </div>
          <div className="h-4 w-px bg-exec-border" />
          <div className="text-sm text-exec-muted">
            Total est. hours: <span className="font-semibold text-exec-accent">{formatHours(selectedHours)}</span>
          </div>
        </div>
        
        <div className="flex items-center gap-2">
          <button
            onClick={copySummary}
            className="px-3 py-2 text-sm bg-exec-bg hover:bg-exec-border rounded border border-exec-border text-exec-text flex items-center gap-2 transition-colors"
          >
            <Copy className="w-4 h-4" />
            Copy summary
          </button>
          <button className="px-3 py-2 text-sm bg-exec-accent hover:bg-exec-accent/90 text-white rounded flex items-center gap-2 transition-colors">
            <Download className="w-4 h-4" />
            Export selected
          </button>
        </div>
      </div>
    </div>
  );
}
