# Frontend Reference

## Stack

| Layer        | Technology                                    |
|--------------|-----------------------------------------------|
| Language     | TypeScript 5.8 + React 19                     |
| Framework    | TanStack Start (TanStack Router + Vite)        |
| Styling      | Tailwind CSS v4 (design tokens in CSS)        |
| UI kit       | shadcn/ui (Radix primitives)                  |
| Charts       | Recharts 2                                    |
| Animation    | Motion (motion/react)                         |
| Forms        | React Hook Form + Zod                         |
| HTTP client  | Fetch API (`src/lib/api.ts`)                  |
| Icons        | Lucide React                                  |
| Build tool   | Vite 8                                        |
| Package mgr  | Bun                                           |

## Design System

The design system lives in `src/styles.css` — a single CSS file with Tailwind v4 `@theme` tokens.

**Color palette — Deep Navy Premium:**

All colors are in `oklch()` for perceptual uniformity.

| Token               | Value                      | Role                  |
|---------------------|----------------------------|-----------------------|
| `--background`      | `oklch(0.18 0.035 260)`    | Page background       |
| `--surface`         | `oklch(0.22 0.04 262)`     | Sidebar / cards       |
| `--surface-elevated`| `oklch(0.26 0.045 263)`    | Card gradient top     |
| `--primary`         | `oklch(0.66 0.19 255)`     | Electric blue accent  |
| `--cyan`            | `oklch(0.82 0.14 200)`     | Cyan highlight        |
| `--success`         | `oklch(0.74 0.16 155)`     | On-track green        |
| `--warning`         | `oklch(0.8 0.15 75)`       | At-risk amber         |
| `--destructive`     | `oklch(0.65 0.21 22)`      | Error red             |

**Typography:**

| Role         | Font           |
|--------------|----------------|
| Display/UI   | Space Grotesk  |
| Body         | Inter          |
| Monospace    | JetBrains Mono |

**Utility classes:**

- `.surface-card` — gradient card with elevated shadow
- `.hero-bg` — radial gradient hero background
- `.gradient-text` — primary→cyan gradient text fill
- `.grid-bg` — subtle grid pattern for hero sections

## Route Structure

```
/                   index.tsx       Marketing landing page
/auth/sign-in       auth.sign-in    Login form
/onboarding         onboarding      4-step setup wizard
/app                app.tsx         Authenticated layout shell
/app/               app.index       Dashboard overview
/app/goals          app.goals       Goal list + CRUD
/app/copilot        app.copilot     AI chat interface
/app/reports        app.reports     Charts + PDF export
/app/profile        app.profile     User settings
/app/settings       app.settings    Account settings
```

## API Client (`src/lib/api.ts`)

The `api` object is the single point of contact with the backend.

**Mock fallback:** when `VITE_API_BASE_URL` is not set every method returns fixture data after a 350 ms delay. The UI is fully functional without a running backend.

**Environment variable:**

```bash
# .env.local
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

**Auth tokens** are stored in `localStorage` under `ns_access_token` / `ns_refresh_token`. Call `setTokens()` after login and `clearTokens()` on logout.

## Component Conventions

- **PascalCase** file and component names
- Props typed with `type Props = {}` (not `interface`)
- No `React.FC` — plain function components
- Custom hooks in `src/hooks/` with `use` prefix
- Shared UI primitives in `src/components/ui/` (shadcn/ui)
- Feature components co-located with their route file

## Adding a New Route

1. Create `src/routes/app.myroute.tsx`
2. Export `Route = createFileRoute("/app/myroute")({ ... })`
3. TanStack Router auto-generates the route tree on `bun run dev`
4. Add a nav item in `src/components/app-shell.tsx` if it needs sidebar navigation

## Build

```bash
bun install
bun run dev        # dev server at :5173
bun run build      # production bundle
bun run preview    # preview production build
```

## Linting & Formatting

```bash
bun run lint       # ESLint
bun run format     # Prettier
```
