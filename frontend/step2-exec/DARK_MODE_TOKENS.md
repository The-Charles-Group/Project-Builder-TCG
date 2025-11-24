# Dark Mode Color Tokens (Extracted from main app)

These tokens are extracted from `/static/style.css` and MUST be used exactly as-is in the React app.

## CSS Variables (from :root)
```css
--bg: #0f1117       /* Main background */
--card: #151a22     /* Card backgrounds */
--text: #e6eaf2     /* Primary text */
--muted: #9aa4b2    /* Muted/secondary text */
--accent: #6aa3ff   /* Primary accent (blue) */
--accent2: #3ddc97  /* Secondary accent (green) */
--border: #232a35   /* Borders */
```

## Additional Colors (from main app)
```css
Input/Select backgrounds: #0b0e13
Selection items: #1a2332 (background), #2a3a4a (border)
Button hover/focus: rgba(106, 163, 255, 0.1-0.5)
Error state: rgba(220, 53, 69, 0.1-0.3)
```

## Tailwind Configuration
Map these to Tailwind classes:
- bg-primary → #0f1117
- bg-card → #151a22
- text-primary → #e6eaf2
- text-muted → #9aa4b2
- border-primary → #232a35
- accent-blue → #6aa3ff
- accent-green → #3ddc97

## Typography
- Font family: system-ui, Segoe UI, Roboto, Helvetica, Arial
- Base size: 14px
- Line height: 1.5
- Headings: 18-20px (Module titles), 14-16px (body)

## Spacing
- Card padding: 20px
- Border radius: 12px (cards), 8px (inputs), 6px (small buttons)
- Gap: 12-16px standard

## CRITICAL RULE
**NO CUSTOM INTERPRETATIONS** - Use these exact values. Do not modify colors, spacing, or add your own design choices.
