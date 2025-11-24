import type { Module } from '../../domain/models';

interface MiniTimelineProps {
  module: Module;
}

const phaseColors = {
  Discovery: '#60a5fa',
  Concept: '#a78bfa',
  Review: '#f59e0b',
  Production: '#10b981',
};

export function MiniTimeline({ module }: MiniTimelineProps) {
  const phase = module.phase || 'Discovery';
  const phases = ['Discovery', 'Concept', 'Review', 'Production'];
  
  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        {phases.map((p) => {
          const isActive = p === phase;
          const color = phaseColors[p as keyof typeof phaseColors];
          
          return (
            <div
              key={p}
              className="flex-1 group relative"
              title={p}
            >
              <div
                className={`h-2 rounded transition-all ${
                  isActive ? 'opacity-100' : 'opacity-20'
                }`}
                style={{ backgroundColor: color }}
              />
              <div className="absolute -bottom-6 left-0 right-0 text-xs text-center text-exec-muted opacity-0 group-hover:opacity-100 transition-opacity">
                {p}
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="text-sm text-exec-muted text-center pt-4">
        Current phase: <span className="font-semibold text-exec-text">{phase}</span>
      </div>
    </div>
  );
}
