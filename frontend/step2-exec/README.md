# Step 2 - Executive Scope Visualization

## Overview
Exec-friendly RFP scope visualization with module cards, filters, and details drawer.

## Tech Stack
- React 18 + TypeScript
- Vite (build tool)
- Zustand (state management)
- TailwindCSS (styling)
- Lucide React (icons)

## Development

### Install Dependencies
```bash
cd frontend/step2-exec
npm install
```

### Run Dev Server
```bash
npm run dev
```

### Build for Production
```bash
npm run build
```

### Run Tests
```bash
npm test
```

## Design System
All colors are extracted from the main app's dark mode theme. See `DARK_MODE_TOKENS.md` for details.

**DO NOT modify colors or add custom interpretations** - use exact values from main app.

## Features
- ✅ Module cards with expand/collapse
- ✅ Filters (Phase, Effort, Risk)
- ✅ Details drawer with tabs
- ✅ Sticky summary bar
- ✅ Keyboard navigation
- ✅ WCAG AA contrast
- ✅ <250KB bundle target
- ✅ Seed data from St. Regis RFP

## Integration with FastAPI
The built frontend is served via FastAPI static routes. See backend integration docs for details.
