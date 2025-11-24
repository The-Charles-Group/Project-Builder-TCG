import { useEffect, useRef, useState } from 'react';
import { X, CheckCircle2, Users, Calendar, Link2, FileText } from 'lucide-react';
import { useStore } from '../state/store';
import { trapFocus } from '../lib/a11y';
import { formatHours } from '../lib/format';
import { cn } from '../lib/cn';

type Tab = 'overview' | 'deliverables' | 'resourcing' | 'timeline' | 'dependencies' | 'notes';

export function DetailsDrawer() {
  const drawerModuleId = useStore((state) => state.ui.drawerModuleId);
  const scope = useStore((state) => state.scope);
  const closeDrawer = useStore((state) => state.closeDrawer);
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const drawerRef = useRef<HTMLDivElement>(null);

  const module = scope?.modules.find((m) => m.id === drawerModuleId);

  // Focus trap and ESC key handler
  useEffect(() => {
    if (!drawerRef.current || !module) return;

    const cleanup = trapFocus(drawerRef.current);
    
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeDrawer();
      }
    };

    document.addEventListener('keydown', handleEscape);

    return () => {
      cleanup();
      document.removeEventListener('keydown', handleEscape);
    };
  }, [module, closeDrawer]);

  if (!module) return null;

  const tabs: Array<{ id: Tab; label: string; icon: React.ReactNode }> = [
    { id: 'overview', label: 'Overview', icon: <FileText className="w-4 h-4" /> },
    { id: 'deliverables', label: 'Deliverables', icon: <CheckCircle2 className="w-4 h-4" /> },
    { id: 'resourcing', label: 'Resourcing', icon: <Users className="w-4 h-4" /> },
    { id: 'timeline', label: 'Timeline', icon: <Calendar className="w-4 h-4" /> },
    { id: 'dependencies', label: 'Dependencies', icon: <Link2 className="w-4 h-4" /> },
    { id: 'notes', label: 'Notes', icon: <FileText className="w-4 h-4" /> },
  ];

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-50"
        onClick={closeDrawer}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-primary-bg border-l border-primary-border shadow-2xl z-50 overflow-hidden flex flex-col"
        role="dialog"
        aria-modal="true"
        aria-labelledby="drawer-title"
      >
        {/* Header */}
        <div className="p-6 border-b border-primary-border">
          <div className="flex items-start justify-between gap-4 mb-2">
            <h2
              id="drawer-title"
              className="text-2xl font-semibold text-primary-text flex-1"
            >
              {module.title}
            </h2>
            <button
              onClick={closeDrawer}
              className="p-2 hover:bg-selection-bg rounded-lg transition-colors"
              aria-label="Close drawer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          <p className="text-sm text-muted">{module.valueStatement}</p>
        </div>

        {/* Tabs */}
        <div className="border-b border-primary-border px-6">
          <div className="flex gap-1 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors whitespace-nowrap",
                  activeTab === tab.id
                    ? "text-accent-blue border-b-2 border-accent-blue"
                    : "text-muted hover:text-primary-text"
                )}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && <OverviewTab module={module} />}
          {activeTab === 'deliverables' && <DeliverablesTab module={module} />}
          {activeTab === 'resourcing' && <ResourcingTab module={module} />}
          {activeTab === 'timeline' && <TimelineTab module={module} />}
          {activeTab === 'dependencies' && <DependenciesTab module={module} scope={scope} />}
          {activeTab === 'notes' && <NotesTab />}
        </div>
      </div>
    </>
  );
}

// Tab Components
function OverviewTab({ module }: { module: any }) {
  return (
    <div className="space-y-6">
      {/* Activities */}
      {module.activities.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-primary-text mb-3">Activities</h3>
          <ul className="space-y-2">
            {module.activities.map((activity: string, idx: number) => (
              <li key={idx} className="flex gap-3">
                <span className="text-accent-blue mt-1">•</span>
                <span className="text-sm text-primary-text flex-1">{activity}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Assumptions */}
      {module.assumptions && module.assumptions.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-primary-text mb-3">Assumptions</h3>
          <ul className="space-y-2">
            {module.assumptions.map((assumption: string, idx: number) => (
              <li key={idx} className="flex gap-3">
                <span className="text-accent-green mt-1">✓</span>
                <span className="text-sm text-muted flex-1">{assumption}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Risks */}
      {module.risks && module.risks.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-yellow-400 mb-3">Risks</h3>
          <ul className="space-y-2">
            {module.risks.map((risk: string, idx: number) => (
              <li key={idx} className="flex gap-3">
                <span className="text-yellow-400 mt-1">!</span>
                <span className="text-sm text-primary-text flex-1">{risk}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function DeliverablesTab({ module }: { module: any }) {
  return (
    <div className="space-y-3">
      {module.outputs.map((output: any) => (
        <div key={output.id} className="p-4 rounded-lg bg-primary-card border border-primary-border">
          <h4 className="font-semibold text-primary-text mb-2">{output.label}</h4>
          {output.acceptanceCriteria && (
            <ul className="list-disc list-inside space-y-1 text-sm text-muted">
              {output.acceptanceCriteria.map((criteria: string, idx: number) => (
                <li key={idx}>{criteria}</li>
              ))}
            </ul>
          )}
        </div>
      ))}
    </div>
  );
}

function ResourcingTab({ module }: { module: any }) {
  if (!module.roles || module.roles.length === 0) {
    return <p className="text-muted">No resourcing information available.</p>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="border-b border-primary-border">
            <th className="text-left py-3 pr-4 text-sm font-semibold text-muted">Role</th>
            <th className="text-left py-3 pr-4 text-sm font-semibold text-muted">Seniority</th>
            <th className="text-right py-3 text-sm font-semibold text-muted">Hours</th>
          </tr>
        </thead>
        <tbody>
          {module.roles.map((role: any, idx: number) => (
            <tr key={idx} className="border-b border-primary-border/50">
              <td className="py-3 pr-4 text-sm text-primary-text">{role.role}</td>
              <td className="py-3 pr-4 text-sm text-muted">{role.seniority || '—'}</td>
              <td className="py-3 text-sm text-right text-accent-blue font-medium">
                {formatHours(role.hours)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TimelineTab({ module }: { module: any }) {
  const phases = ['Discovery', 'Concept', 'Review', 'Production'];
  const currentPhase = module.phase || 'Discovery';

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold text-primary-text mb-4">Phase</h3>
        <div className="flex gap-2">
          {phases.map((phase) => (
            <div
              key={phase}
              className={cn(
                "flex-1 h-2 rounded-full",
                phase === currentPhase ? "bg-accent-blue" : "bg-selection-bg"
              )}
              title={phase}
            />
          ))}
        </div>
        <div className="flex justify-between mt-2 text-xs text-muted">
          {phases.map((phase) => (
            <span key={phase} className={cn(phase === currentPhase && "text-accent-blue font-semibold")}>
              {phase}
            </span>
          ))}
        </div>
      </div>
      <p className="text-sm text-muted">
        Current phase: <span className="text-accent-blue font-semibold">{currentPhase}</span>
      </p>
    </div>
  );
}

function DependenciesTab({ module, scope }: { module: any; scope: any }) {
  if (!module.dependencies || module.dependencies.length === 0) {
    return <p className="text-muted">No dependencies.</p>;
  }

  const needs = module.dependencies.filter((d: any) => d.type === 'needs');
  const feeds = module.dependencies.filter((d: any) => d.type === 'feeds');

  const getModuleTitle = (id: string) => {
    const m = scope?.modules.find((mod: any) => mod.id === id);
    return m?.title || id;
  };

  return (
    <div className="space-y-6">
      {needs.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-primary-text mb-3">Needs (Upstream)</h3>
          <div className="space-y-2">
            {needs.map((dep: any) => (
              <div key={dep.id} className="p-3 rounded-lg bg-primary-card border border-primary-border">
                <p className="text-sm text-primary-text">{getModuleTitle(dep.id)}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {feeds.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-primary-text mb-3">Feeds (Downstream)</h3>
          <div className="space-y-2">
            {feeds.map((dep: any) => (
              <div key={dep.id} className="p-3 rounded-lg bg-primary-card border border-primary-border">
                <p className="text-sm text-primary-text">{getModuleTitle(dep.id)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function NotesTab() {
  return (
    <div>
      <p className="text-muted mb-4">Notes are read-only in this view.</p>
      <div className="p-4 rounded-lg bg-input-bg border border-primary-border">
        <p className="text-sm text-muted italic">No notes available.</p>
      </div>
    </div>
  );
}
