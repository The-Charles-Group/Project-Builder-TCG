import { X, Package, Users, Calendar, Network, FileText } from 'lucide-react';
import { useStore } from '../../state/store';
import { MiniTimeline } from '../MiniTimeline/MiniTimeline';
import { formatHoursRange } from '../../lib/utils';
import { useEffect, useRef, useState } from 'react';

export function DetailsDrawer() {
  const drawerModuleId = useStore((state) => state.drawerModuleId);
  const closeDrawer = useStore((state) => state.closeDrawer);
  const scope = useStore((state) => state.scope);
  const [activeTab, setActiveTab] = useState('overview');
  
  const drawerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeDrawer();
    };
    
    if (drawerModuleId) {
      document.addEventListener('keydown', handleEsc);
      drawerRef.current?.focus();
    }
    
    return () => document.removeEventListener('keydown', handleEsc);
  }, [drawerModuleId, closeDrawer]);
  
  if (!drawerModuleId) return null;
  
  const module = scope.modules.find((m) => m.id === drawerModuleId);
  if (!module) return null;
  
  const tabs = [
    { id: 'overview', label: 'Overview', icon: FileText },
    { id: 'deliverables', label: 'Deliverables', icon: Package },
    { id: 'resourcing', label: 'Resourcing', icon: Users },
    { id: 'timeline', label: 'Timeline', icon: Calendar },
    { id: 'dependencies', label: 'Dependencies', icon: Network },
  ];
  
  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 z-40"
        onClick={closeDrawer}
      />
      
      {/* Drawer */}
      <div
        ref={drawerRef}
        className="fixed right-0 top-0 bottom-0 w-[480px] bg-exec-card border-l border-exec-border shadow-2xl z-50 flex flex-col"
        tabIndex={-1}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-exec-border">
          <h2 className="text-xl font-semibold text-exec-text">{module.title}</h2>
          <button
            onClick={closeDrawer}
            className="p-2 hover:bg-exec-border rounded transition-colors"
            aria-label="Close drawer"
          >
            <X className="w-5 h-5 text-exec-muted" />
          </button>
        </div>
        
        {/* Tabs */}
        <div className="flex border-b border-exec-border overflow-x-auto">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.id
                    ? 'border-exec-accent text-exec-accent'
                    : 'border-transparent text-exec-muted hover:text-exec-text'
                }`}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </div>
        
        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {activeTab === 'overview' && (
            <div className="space-y-6">
              <div>
                <h3 className="text-sm font-semibold text-exec-muted uppercase tracking-wide mb-2">
                  Value Statement
                </h3>
                <p className="text-sm text-exec-text leading-relaxed">{module.valueStatement}</p>
              </div>
              
              <div>
                <h3 className="text-sm font-semibold text-exec-muted uppercase tracking-wide mb-3">
                  Activities
                </h3>
                <ul className="space-y-2">
                  {module.activities.map((activity, idx) => (
                    <li key={idx} className="text-sm text-exec-text leading-relaxed pl-4 relative before:content-['•'] before:absolute before:left-0 before:text-exec-accent">
                      {activity}
                    </li>
                  ))}
                </ul>
              </div>
              
              {module.assumptions && module.assumptions.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-exec-muted uppercase tracking-wide mb-2">
                    Assumptions
                  </h3>
                  <ul className="space-y-1">
                    {module.assumptions.map((assumption, idx) => (
                      <li key={idx} className="text-sm text-exec-text pl-4 relative before:content-['→'] before:absolute before:left-0 before:text-exec-muted">
                        {assumption}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {module.risks && module.risks.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-exec-muted uppercase tracking-wide mb-2">
                    Risks
                  </h3>
                  <ul className="space-y-1">
                    {module.risks.map((risk, idx) => (
                      <li key={idx} className="text-sm text-red-300 pl-4 relative before:content-['⚠'] before:absolute before:left-0">
                        {risk}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {module.effort && (
                <div>
                  <h3 className="text-sm font-semibold text-exec-muted uppercase tracking-wide mb-2">
                    Effort
                  </h3>
                  <p className="text-sm text-exec-text">
                    {formatHoursRange(module.effort.hoursMin, module.effort.hoursMax)}
                    {module.effort.size && ` (Size: ${module.effort.size})`}
                  </p>
                </div>
              )}
            </div>
          )}
          
          {activeTab === 'deliverables' && (
            <div className="space-y-4">
              {module.outputs.map((output) => (
                <div key={output.id} className="p-4 bg-exec-bg rounded border border-exec-border">
                  <h4 className="text-sm font-semibold text-exec-text mb-2">{output.label}</h4>
                  {output.acceptanceCriteria && output.acceptanceCriteria.length > 0 && (
                    <div>
                      <p className="text-xs text-exec-muted mb-1">Acceptance Criteria:</p>
                      <ul className="space-y-1">
                        {output.acceptanceCriteria.map((criteria, idx) => (
                          <li key={idx} className="text-sm text-exec-text pl-4 relative before:content-['✓'] before:absolute before:left-0 before:text-green-400">
                            {criteria}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          
          {activeTab === 'resourcing' && (
            <div>
              {module.roles && module.roles.length > 0 ? (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-exec-border">
                      <th className="text-left py-2 text-exec-muted font-semibold">Role</th>
                      <th className="text-left py-2 text-exec-muted font-semibold">Seniority</th>
                      <th className="text-right py-2 text-exec-muted font-semibold">Hours</th>
                    </tr>
                  </thead>
                  <tbody>
                    {module.roles.map((role, idx) => (
                      <tr key={idx} className="border-b border-exec-border/50">
                        <td className="py-3 text-exec-text">{role.role}</td>
                        <td className="py-3 text-exec-text">{role.seniority || '—'}</td>
                        <td className="py-3 text-exec-text text-right">{role.hours || '—'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p className="text-sm text-exec-muted">No resourcing information available.</p>
              )}
            </div>
          )}
          
          {activeTab === 'timeline' && (
            <div>
              <MiniTimeline module={module} />
            </div>
          )}
          
          {activeTab === 'dependencies' && (
            <div className="space-y-4">
              {module.dependencies && module.dependencies.length > 0 ? (
                <>
                  <div>
                    <h3 className="text-sm font-semibold text-exec-muted uppercase tracking-wide mb-3">
                      Upstream (Needs)
                    </h3>
                    <div className="space-y-2">
                      {module.dependencies
                        .filter((d) => d.type === 'needs')
                        .map((dep) => {
                          const depModule = scope.modules.find((m) => m.id === dep.id);
                          return depModule ? (
                            <div key={dep.id} className="p-3 bg-exec-bg rounded border border-exec-border">
                              <p className="text-sm font-medium text-exec-text">{depModule.title}</p>
                            </div>
                          ) : null;
                        })}
                    </div>
                  </div>
                  
                  <div>
                    <h3 className="text-sm font-semibold text-exec-muted uppercase tracking-wide mb-3">
                      Downstream (Feeds)
                    </h3>
                    <div className="space-y-2">
                      {module.dependencies
                        .filter((d) => d.type === 'feeds')
                        .map((dep) => {
                          const depModule = scope.modules.find((m) => m.id === dep.id);
                          return depModule ? (
                            <div key={dep.id} className="p-3 bg-exec-bg rounded border border-exec-border">
                              <p className="text-sm font-medium text-exec-text">{depModule.title}</p>
                            </div>
                          ) : null;
                        })}
                    </div>
                  </div>
                </>
              ) : (
                <p className="text-sm text-exec-muted">No dependencies defined.</p>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}
