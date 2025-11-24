import { HeaderSummary } from '../components/HeaderSummary/HeaderSummary';
import { FilterBar } from '../components/FilterBar/FilterBar';
import { ModuleGrid } from '../components/ModuleGrid/ModuleGrid';
import { DetailsDrawer } from '../components/DetailsDrawer/DetailsDrawer';
import { StickySummaryBar } from '../components/StickySummaryBar/StickySummaryBar';

export function Step2() {
  return (
    <div className="min-h-screen bg-exec-bg">
      <HeaderSummary />
      <FilterBar />
      
      <main className="max-w-[1920px] mx-auto px-6 py-8 pb-24">
        <ModuleGrid />
      </main>
      
      <DetailsDrawer />
      <StickySummaryBar />
    </div>
  );
}
