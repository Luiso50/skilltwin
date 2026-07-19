# CONTEXT - SkillTwin Project

## Project Overview
SkillTwin is a modular automation/management platform featuring intelligent agents for various business departments (Legal, Marketing, Operations, Development). It converts expert knowledge into monetizable digital twins (AI clones).

## Current Status
- **Structure:** Modular architecture fully established.
- **Backend:** Python HTTP server with 18+ endpoints (server.py).
- **Frontend:** Dashboard, admin panel, client portal, landing page.
- **Tests:** 48 unit tests passing across all modules.
- **Status:** Production-ready prototype. All modules functional.

## Architecture
```
skilltwin/
├── cerebro/          # Central dashboard, HTTP server, portal
├── dep_desarrollo/   # Cloning motor, knowledge DB (7 clones)
├── dep_marketing/    # Sales intelligence, market research
├── dep_legal/        # Contracts, ethics, privacy policies
├── dep_operaciones/  # Finance, orders, payments, orchestration
├── docs/             # Public landing (GitHub Pages ready)
├── website/          # Editable landing for branding
└── tests/            # 48 unit tests
```

## Technical Stack
- **Backend:** Python (http.server, JSON databases, threading)
- **Frontend:** HTML, CSS, JavaScript (Chart.js)
- **AI Integration:** Gemini API (optional, works offline)
- **DevOps:** Docker, PowerShell/Bash scripts
- **Data Storage:** JSON files (thread-safe with locks)

## Test Coverage
| Module | Tests | Status |
|--------|-------|--------|
| motor_clonacion | 11 | 100% |
| gestor_financiero | 10 | 100% |
| agente_ventas | 7 | 100% |
| generador_contratos | 8 | 100% |
| server/config | 8 | 100% |
| gestor_contactos | 1 | 100% |
| gestor_pagos_ordenes | 4 | 100% |
| **Total** | **48** | **All passing** |

## Key Features
- 7 AI clones across 5 industries (COBOL, Finance, Security, UX, Data Science, Legal, Sales)
- Intelligent command routing via Gemini AI
- Automated order orchestration (Legal → Development → Operations → Delivery)
- Financial dashboards with cash flow, receivables, payables
- Contract generation with customizable commission rates
- Contact form with backend integration and email fallback

## Recent Actions
- Added 5 new clones (cybersecurity, UX, data science, legal, sales)
- Created 48 unit tests for all modules
- Updated CONTEXT.md to reflect real project state

## Backlog / Next Steps
- [ ] API documentation (docs/API.md)
- [ ] Security hardening (env vars for API keys, admin auth)
- [ ] Migrate JSON to SQLite for production
- [ ] Real email integration
- [ ] Stripe payment integration
- [ ] CI/CD with GitHub Actions
