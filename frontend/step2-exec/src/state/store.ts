import { create } from 'zustand';
import type { ScopeSummary, EffortSize } from '../domain/models';

// ============================================================================
// State Types
// ============================================================================

export interface Filters {
  phase?: string[];
  effort?: EffortSize[];
  risk?: ("hasRisk" | "noRisk")[];
  dept?: string[];
}

export interface UIState {
  drawerModuleId?: string;
  loading: boolean;
}

export interface AppState {
  scope: ScopeSummary | null;
  filters: Filters;
  expandedModuleIds: Set<string>;
  selectedModuleIds: Set<string>;
  ui: UIState;
  
  // Actions
  setScope: (scope: ScopeSummary) => void;
  setFilters: (filters: Filters) => void;
  clearFilters: () => void;
  toggleExpanded: (moduleId: string) => void;
  expandAll: () => void;
  collapseAll: () => void;
  toggleSelected: (moduleId: string) => void;
  clearSelection: () => void;
  openDrawer: (moduleId: string) => void;
  closeDrawer: () => void;
  setLoading: (loading: boolean) => void;
}

// ============================================================================
// Store
// ============================================================================

export const useStore = create<AppState>((set) => ({
  scope: null,
  filters: {},
  expandedModuleIds: new Set(),
  selectedModuleIds: new Set(),
  ui: {
    loading: false,
  },

  setScope: (scope) => set({ scope }),
  
  setFilters: (filters) => set({ filters }),
  
  clearFilters: () => set({ filters: {} }),
  
  toggleExpanded: (moduleId) =>
    set((state) => {
      const expanded = new Set(state.expandedModuleIds);
      if (expanded.has(moduleId)) {
        expanded.delete(moduleId);
      } else {
        expanded.add(moduleId);
      }
      return { expandedModuleIds: expanded };
    }),
  
  expandAll: () =>
    set((state) => {
      const allIds = state.scope?.modules.map((m) => m.id) || [];
      return { expandedModuleIds: new Set(allIds) };
    }),
  
  collapseAll: () => set({ expandedModuleIds: new Set() }),
  
  toggleSelected: (moduleId) =>
    set((state) => {
      const selected = new Set(state.selectedModuleIds);
      if (selected.has(moduleId)) {
        selected.delete(moduleId);
      } else {
        selected.add(moduleId);
      }
      return { selectedModuleIds: selected };
    }),
  
  clearSelection: () => set({ selectedModuleIds: new Set() }),
  
  openDrawer: (moduleId) =>
    set((state) => ({
      ui: { ...state.ui, drawerModuleId: moduleId },
    })),
  
  closeDrawer: () =>
    set((state) => ({
      ui: { ...state.ui, drawerModuleId: undefined },
    })),
  
  setLoading: (loading) =>
    set((state) => ({
      ui: { ...state.ui, loading },
    })),
}));
