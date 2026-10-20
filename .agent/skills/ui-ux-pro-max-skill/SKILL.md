---
name: ui-ux-pro-max
description: AI-powered design intelligence with 67 UI styles, 161 color palettes, 57 font pairings, 99 UX guidelines, and 25 chart types across 15+ tech stacks.
---

# UI/UX Pro Max

AI-powered design intelligence with searchable databases of UI styles, color palettes, font pairings, chart types, and UX guidelines. Works as a skill for AI coding assistants.

## Search Command

```bash
python3 src/ui-ux-pro-max/scripts/search.py "<query>" --domain <domain> [-n <max_results>]
```

**Domain search:**
- `product` - Product type recommendations (SaaS, e-commerce, portfolio)
- `style` - UI styles (glassmorphism, minimalism, brutalism) + AI prompts and CSS keywords
- `typography` - Font pairings with Google Fonts imports
- `color` - Color palettes by product type
- `landing` - Page structure and CTA strategies
- `chart` - Chart types and library recommendations
- `ux` - Best practices and anti-patterns

**Stack search:**
```bash
python3 src/ui-ux-pro-max/scripts/search.py "<query>" --stack <stack>
```
Available stacks: `html-tailwind` (default), `react`, `nextjs`, `astro`, `vue`, `nuxtjs`, `nuxt-ui`, `svelte`, `swiftui`, `react-native`, `flutter`, `shadcn`, `jetpack-compose`

The search engine uses BM25 ranking combined with regex matching. Domain auto-detection is available when `--domain` is omitted.
