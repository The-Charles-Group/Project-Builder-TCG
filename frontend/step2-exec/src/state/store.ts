import { create } from 'zustand';
import type { ScopeSummary, Module, EffortSize } from '../domain/models';
import { seedData } from '../domain/seedData';

export interface Filters {
  phase: string[];
  effort: EffortSize[];
  risk: ('hasRisk' | 'noRisk')[];
  dept: string[];
}

interface StoreState {
  scope: ScopeSummary;
  filters: Filters;
  expandedModuleIds: Set<string>;
  selectedModuleIds: Set<string>;
  drawerModuleId: string | null;
  loading: boolean;
  
  setScope: (scope: ScopeSummary) => void;
  setFilters: (filters: Partial<Filters>) => void;
  clearFilters: () => void;
  toggleExpanded: (id: string) => void;
  expandAll: () => void;
  collapseAll: () => void;
  toggleSelected: (id: string) => void;
  clearSelected: () => void;
  openDrawer: (id: string) => void;
  closeDrawer: () => void;
  setLoading: (loading: boolean) => void;
  
  getFilteredModules: () => Module[];
  getSelectedHours: () => number;
}

const defaultFilters: Filters = {
  phase: [],
  effort: [],
  risk: [],
  dept: [],
};

export const useStore = create<StoreState>((set, get) => ({
  scope: seedData,
  filters: defaultFilters,
  expandedModuleIds: new Set(),
  selectedModuleIds: new Set(),
  drawerModuleId: null,
  loading: false,
  
  setScope: (scope) => set({ scope }),
  
  setFilters: (newFilters) => set((state) => ({
    filters: { ...state.filters, ...newFilters },
  })),
  
  clearFilters: () => set({ filters: defaultFilters }),
  
  toggleExpanded: (id) => set((state) => {
    const newExpanded = new Set(state.expandedModuleIds);
    if (newExpanded.has(id)) {
      newExpanded.delete(id);
    } else {
      newExpanded.add(id);
    }
    return { expandedModuleIds: newExpanded };
  }),
  
  expandAll: () => set((state) => ({
    expandedModuleIds: new Set(state.scope.modules.map((m) => m.id)),
  })),
  
  collapseAll: () => set({ expandedModuleIds: new Set() }),
  
  toggleSelected: (id) => set((state) => {
    const newSelected = new Set(state.selectedModuleIds);
    if (newSelected.has(id)) {
      newSelected.delete(id);
    } else {
      newSelected.add(id);
    }
    return { selectedModuleIds: newSelected };
  }),
  
  clearSelected: () => set({ selectedModuleIds: new Set() }),
  
  openDrawer: (id) => set({ drawerModuleId: id }),
  
  closeDrawer: () => set({ drawerModuleId: null }),
  
  setLoading: (loading) => set({ loading }),
  
  getFilteredModules: () => {
    const { scope, filters } = get();
    
    return scope.modules.filter((module) => {
      if (filters.phase.length > 0 && (!module.phase || !filters.phase.includes(module.phase))) {
        return false;
      }
      
      if (filters.effort.length > 0 && (!module.effort?.size || !filters.effort.includes(module.effort.size))) {
        return false;
      }
      
      if (filters.risk.length > 0) {
        const hasRisk = (module.risks && module.risks.length > 0);
        if (filters.risk.includes('hasRisk') && !hasRisk) return false;
        if (filters.risk.includes('noRisk') && hasRisk) return false;
      }
      
      if (filters.dept.length > 0 && (!module.department || !filters.dept.includes(module.department))) {
        return false;
      }
      
      return true;
    });
  },
  
  getSelectedHours: () => {
    const { scope, selectedModuleIds } = get();
    let total = 0;
    
    scope.modules.forEach((module) => {
      if (selectedModuleIds.has(module.id)) {
        if (module.effort?.hoursMin && module.effort?.hoursMax) {
          total += (module.effort.hoursMin + module.effort.hoursMax) / 2;
        }
      }
    });
    
    return Math.round(total);
  },
}));
