# Changelog

All notable changes to Northstar are documented here.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- FastAPI backend with async PostgreSQL via asyncpg
- JWT authentication (access + refresh tokens, bcrypt passwords)
- Monte Carlo simulation engine (10 000 log-normal paths per goal)
- Financial optimizer (contribution, risk-shift, and combined strategies)
- Goal-based planning service with automatic probability refresh
- AI Copilot endpoint (GPT-4o with rule-based fallback)
- Alembic migration scaffold with initial schema (001)
- Full test suite: unit tests for simulation engine and optimizer,
  integration tests for auth and goals APIs
- `docker-compose.yml` orchestrating PostgreSQL + backend + frontend
- Complete documentation: README, architecture, backend, frontend, database,
  CONTRIBUTING, CHANGELOG, CLAUDE.md
- Frontend `api.ts` updated to call real endpoints with mock fallback

---

## [0.1.0] — 2025-01-01

### Added
- TanStack Start frontend scaffolded by Lovable
- Deep Navy Premium design system (oklch colour palette)
- Marketing landing page with hero, features, how-it-works, CTA
- Sign-in page (form UI, no backend yet)
- Onboarding placeholder wizard
- Dashboard route with net-worth chart, allocation pie, goals summary, AI suggestions
- Goals route with Monte Carlo probability badges and new-goal modal
- AI Copilot chat interface (mock responses)
- Reports route with bar chart
- Mock data fixtures and placeholder API service layer
