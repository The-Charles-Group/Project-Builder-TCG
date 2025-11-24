import { useEffect } from 'react';
import { useStore } from './state/store';
import { seedData } from './domain/seedData';
import { HeaderSummary } from './components/HeaderSummary';
import { FilterBar } from './components/FilterBar';
import { ModuleGrid } from './components/ModuleGrid';
import { StickySummaryBar } from './components/StickySummaryBar';
import { DetailsDrawer } from './components/DetailsDrawer';

function App() {
  const setScope = useStore((state) => state.setScope);
  const setLoading = useStore((state) => state.setLoading);
  const drawerModuleId = useStore((state) => state.ui.drawerModuleId);

  // Load seed data on mount
  useEffect(() => {
    setLoading(true);
    // Simulate async data loading
    setTimeout(() => {
      setScope(seedData);
      setLoading(false);
    }, 500);
  }, [setScope, setLoading]);

  return (
    <div className="min-h-screen bg-primary-bg">
      <HeaderSummary />
      
      <main className="mx-auto max-w-7xl px-6 py-8">
        <FilterBar />
        <ModuleGrid />
      </main>

      <StickySummaryBar />
      
      {drawerModuleId && <DetailsDrawer />}
    </div>
  );
}

export default App;
