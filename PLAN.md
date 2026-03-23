# Aergia CV Builder — Final Plan

## 1. Architecture Overview

### Single-Origin Design

FastAPI serves both the built frontend and the API from the same domain/port.

```
http://api-server:8000/        ← React SPA (index.html)
http://api-server:8000/api/v1/auth/login         ← API
http://api-server:8000/api/v1/cvs                ← API

http://api-server:8000/static/index.html         ← SPA entry
http://api-server:8000/static/assets/abc.js      ← SPA bundles
```

CORS is not needed at all. The desktop Tauri wrapper loads the same URL.

### Tech Stack

| Layer | Choice |
|---|---|
| **Backend** | FastAPI (Python 3.12) + uvicorn |
| **Database** | PostgreSQL 16 |
| **ORM** | SQLAlchemy 2.0 + Alembic |
| **Auth** | bcrypt + JWT (python-jose) |
| **Files** | Local filesystem (`/app/uploads/`) |
| **PDF** | Puppeteer in-process |
| **Frontend** | React 19 + TypeScript 5 + Vite 5 |
| **State** | Zustand |
| **Forms** | React Hook Form + Zod |
| **Styling** | Tailwind CSS + CSS Modules (templates) |
| **Drag & Drop** | dnd-kit |
| **Icons** | lucide-react |
| **Animations** | motion (motion.dev) |
| **HTTP Client** | axios |
| **Container** | Docker + docker-compose (2 containers) |
| **Desktop** | Tauri 2.x (future, loads same URL) |

### VPS Specs (Netcup Starter Dedicated)

2 vCore (x86), 4GB DDR5 ECC, 128GB NVMe, 1GB/s port

```
Service            Memory     CPU (idle)     CPU (active)
Postgres           ~150MB     0.1-0.3        0.3-0.5
FastAPI (2w)       ~100MB     0              0.1
Puppeteer (on)     ~150MB     0              0.5-1.0
Nginx (if used)    ~30MB      0              0.05
OS + buffers       ~300MB     -              -
─────────────────
Total              ~730MB     0.1-0.3        0.6-1.4
```

Budget: 730MB used, 4GB available. Comfortable margin.

---

## 2. Database Schema

### users

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | gen_random_uuid() |
| email | VARCHAR(255) UNIQUE | Login credential |
| password_hash | VARCHAR(255) NOT NULL | bcrypt cost 12 |
| is_verified | BOOLEAN DEFAULT true | Auto-verified |
| created_at | TIMESTAMP DEFAULT now() | |
| updated_at | TIMESTAMP DEFAULT now() | |

### cvs

| Column | Type | Notes |
|---|---|---|
| id | UUID PK | gen_random_uuid() |
| user_id | UUID FK → users.id ON DELETE CASCADE | Owner |
| title | VARCHAR(255) NOT NULL | |
| description | VARCHAR(500) | |
| template_id | VARCHAR(50) NOT NULL | Refers to template |
| customizations | JSONB DEFAULT '{}' | Colors, fonts, spacing |
| sections | JSONB NOT NULL | Section order + data |
| metadata | JSONB DEFAULT '{}' | |
| is_active | BOOLEAN DEFAULT true | Soft-delete flag |
| created_at | TIMESTAMP DEFAULT now() | |
| updated_at | TIMESTAMP DEFAULT now() | |

### templates (read-only, seeded once)

| Column | Type | Notes |
|---|---|---|
| id | VARCHAR(50) PK | Template identifier |
| name | VARCHAR(100) NOT NULL | Display name |
| description | TEXT | |
| preview_image_url | VARCHAR(500) | Local static path |
| layout_config | JSONB NOT NULL | {columns, widths, margins} |
| section_schema | JSONB NOT NULL | Sections & field definitions |
| default_customizations | JSONB | Default colors/fonts/spacing |
| is_system | BOOLEAN DEFAULT true | Can't delete system templates |
| created_at | TIMESTAMP DEFAULT now() | |

---

## 3. CV Section Data Model

```json
{
  "instances": [
    {
      "id": "sec_uuid_1",
      "type": "profile",
      "title": "Profile",
      "enabled": true,
      "data": {
        "name": "Jane Doe",
        "title": "Software Engineer",
        "email": "jane@example.com",
        "phone": "+1 555-1234",
        "location": "Boston, MA",
        "summary": "5+ years building...",
        "photo_url": "/uploads/user_photo.jpg"
      }
    },
    {
      "id": "sec_uuid_2",
      "type": "experience",
      "title": "Work Experience",
      "enabled": true,
      "data": [
        {
          "id": "exp_1",
          "company": "Acme Corp",
          "position": "Senior Engineer",
          "start_date": "2022-01",
          "end_date": null,
          "current": true,
          "location": "Boston, MA",
          "description": "Led team of 5..."
        }
      ]
    },
    {
      "id": "sec_uuid_3",
      "type": "education",
      "title": "Education",
      "enabled": true,
      "data": [...]
    }
  ]
}
```

Each section is a self-contained instance with its own ID, type, title, enabled state, and data. Order is determined by array position. Multiple instances of the same type are permitted (e.g. two "experience" sections with different titles).

---

## 4. CV Section Types (7 Section Types)

Each section is a **SectionInstance** — a self-contained object with its own `id`, `type`, `title` (user-customizable), `enabled` flag, and `data`. Multiple instances of the same type are allowed (e.g. two "Experience" sections). The data shapes per type:

| Section Type | Fields | Data Shape |
|---|---|---|
| Profile | name, title, email, phone, location, summary, photo_url | Single object |
| Experience | company, position, start_date, end_date, current, location, description | Array |
| Education | institution, degree, start_date, end_date, current, gpa | Array |
| Skills | id, category, items[] | Array |
| Projects | name, url, start_date, end_date, description, tech_stack[] | Array |
| Languages | language, proficiency | Array |
| Certifications | name, issuer, date, credential_url | Array |

---

## 5. Seed Templates (3 Generic)

### Generic Modern
- Layout: 2 columns (30% sidebar / 70% content)
- Colors: accent color header, light sidebar background
- Font: Inter or system-ui
- Sections: profile in sidebar, main content with experience → education → skills

### Generic Classic
- Layout: single column
- Colors: black headers, gray divider lines
- Font: Georgia or Crimson
- Sections: bold name header, sections below in order

### Generic Minimal
- Layout: single column
- Colors: grayscale, no decoration
- Font: clean sans-serif, medium weight
- Sections: pure content, no borders or backgrounds

---

## 6. API Endpoints

### Auth
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/auth/register` | Create account (auto-verified) |
| POST | `/api/v1/auth/login` | Access token + refresh token |
| POST | `/api/v1/auth/refresh` | New access token |
| POST | `/api/v1/auth/logout` | Invalidate refresh token |
| POST | `/api/v1/auth/change-password` | Change own password |

### CVs
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/cvs` | List user's CVs |
| POST | `/api/v1/cvs` | Create new CV |
| GET | `/api/v1/cvs/{id}` | Get CV detail |
| PATCH | `/api/v1/cvs/{id}` | Update sections/customizations |
| DELETE | `/api/v1/cvs/{id}` | Soft-delete |
| POST | `/api/v1/cvs/{id}/copy` | Clone CV |
| POST | `/api/v1/cvs/{id}/export/pdf` | Generate PDF |
| GET | `/api/v1/cvs/{id}/preview` | Render preview HTML |

### Assets
| Method | Path | Description |
|---|---|---|
| POST | `/api/v1/assets` | Upload photo |
| DELETE | `/api/v1/assets/{id}` | Remove photo |

### Templates
| Method | Path | Description |
|---|---|---|
| GET | `/api/v1/templates` | List all templates |
| GET | `/api/v1/templates/{id}` | Get template config |

### Response Shapes

```
/auth/register    → 201 Created
/auth/login       → { access_token, refresh_token, token_type: "bearer" }
/auth/refresh     → { access_token }
/auth/logout      → 200 OK
/auth/change-password → 200 OK

/cvs POST         → { id, title, template_id, sections, created_at }
/cvs GET          → [ { id, title, template_id, created_at, updated_at } ]
/cvs/{id} GET     → { id, title, description, template_id, customizations, sections, metadata }
/cvs/{id} PATCH   → updated CV object
/cvs/{id} DELETE  → 204 No Content
/cvs/{id}/copy    → { id, title, template_id, sections, created_at } (new CV)
/cvs/{id}/export/pdf → application/pdf stream
/cvs/{id}/preview → { html: "string" }

/assets POST      → 200 OK
/assets/{id} DELETE → 200 OK

/templates GET    → [ { id, name, description, preview_image_url } ]
/templates/{id} GET → { ...config, section_schema, default_customizations }
```

---

## 7. Auth Flow

```
REGISTER:
  POST /api/v1/auth/register
  Body: { email, password }
  Response: 201 Created
  → Account auto-verified, no email required

LOGIN:
  POST /api/v1/auth/login
  Body: { email, password }
  Response: { access_token (15min), refresh_token (7d), token_type: "bearer" }
  → Tokens stored in Zustand store (localStorage)

ACCESS:
  → axios interceptor adds Authorization: Bearer {access_token} on every API call

REFRESH:
  POST /api/v1/auth/refresh
  Body: { refresh_token }
  → New access_token only

LOGOUT:
  POST /api/v1/auth/logout
  → Invalidate refresh token on server, clear tokens from client

CHANGE PASSWORD:
  POST /api/v1/auth/change-password
  Body: { old_password, new_password }
  Response: 200 OK
```

**Implementation details:**
- Password hashing: bcrypt with cost factor 12
- JWT: python-jose (algorithm HS256)
- Token storage: Zustand store in localStorage

---

## 8. PDF Flow (In-Process Puppeteer)

1. User clicks "Export PDF" in BuilderPage
2. POST `/api/v1/cvs/{id}/export/pdf`
3. Backend fetches CV data + template config
4. Builds HTML string matching the CVPreview component exactly
5. Launches Puppeteer (headless, no-sandbox)
6. Renders HTML string to PDF (A4, margins: 0)
7. Returns PDF as response stream
8. Closes browser

Key: HTML is built from the **same React templates** as the preview component. Same DOM structure, same class names, same inline styles.

---

## 9. File Storage (Local)

Photo upload flow:
1. User selects file in ProfileForm
2. Client sends multipart/form-data to POST `/api/v1/assets`
3. Backend generates filename `{user_id}_{uuid}.{ext}`
4. Validates: max 5MB, image/jpeg/png/webp
5. Saves to `/app/uploads/`
6. Returns `{ url: `/uploads/${filename}` }`

Serving photos via FastAPI:
```python
@app.get("/uploads/{filename}")
async def serve_photo(filename: str):
    return FileResponse(f"/app/uploads/{filename}")
```

Static files served by FastAPI:
```python
app.mount("/static", StaticFiles(directory="/app/static"))
```

SPA fallback route for client-side routing.

---

## 10. Template System

1. User picks a template from the gallery
2. Backend stores `template_id` on the CV record
3. Frontend loads template config (layout + section schema)
4. Frontend renders sections using the selected template's React components (CSS Modules)
5. Customization panel overrides template defaults (colors, fonts, spacing)

Template config structure:
```json
{
  "id": "generic-modern",
  "name": "Modern",
  "layout": { "columns": 2, "widths": [30, 70], "margins": {...} },
  "section_order": ["profile", "experience", "education", "skills", "projects", "languages", "certifications"],
  "section_schema": { "profile": { "fields": [...] }, ... },
  "default_customizations": { "colors": {}, "fonts": {}, "spacing": {} }
}
```

Customization overrides stored in `cvs.customizations`, applied as CSS variables on the preview root element.

---

## 11. State Management (Zustand)

### authStore
- user, access_token, refresh_token, isAuthenticated
- login(), register(), logout(), changePassword()

### cvStore
- currentCV, cvList
- **Instance CRUD:** addInstance(), removeInstance(), updateInstanceData(), reorderInstances(), toggleInstance(), renameInstance()
- createCV(), copyCV(), deleteCV(), setTemplate(), saveCV(), exportPDF(), autoSave()

### templateStore
- templateList, currentTemplate, availableSections
- customize(color, font, spacing)

### uiStore
- builderSidebarOpen, cvListSidebarOpen, toast, isSaving, zoomLevel

---

## 12. Docker Compose

```yaml
services:
  api:
    build:
      context: .
      dockerfile: api/Dockerfile
    ports:
      - "8000:8000"
    volumes:
      - uploads_data:/app/uploads
    environment:
      - DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@postgres:5432/${DB_NAME}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped

  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${DB_USER:-aergia_user}
      POSTGRES_PASSWORD: ${DB_PASS:-aergia_pass}
      POSTGRES_DB: ${DB_NAME:-aergia}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-aergia_user}"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  uploads_data:
  postgres_data:
```

Build context is the repo root (`.`), because the Dockerfile needs access to both `api/` and `web/` directories for the multi-stage build.

---

## 13. Deployment Checklist

1. Provision VPS (minimum 2 vCPU, 4GB RAM, 50GB SSD)
2. Install Docker + Docker Compose
3. Clone repo to `/opt/aergia`
4. Copy `.env.example` to `.env`, fill in secrets (`SECRET_KEY`, `DB_PASS`)
5. `docker compose up -d`
6. Run migrations: `docker compose exec api alembic upgrade head`
7. Verify: `curl http://your-vps-ip:8000/healthz`
8. (Optional) Set up Cloudflare Tunnel or Caddy for HTTPS

---

## 14. Security Summary

- Password hashing: bcrypt cost factor 12
- Access token: 15-minute JWT expiry
- Refresh token: 7-day JWT expiry
- File upload: 5MB max, image/jpeg/png/webp only
- SQL injection: prevented by SQLAlchemy ORM
- XSS: prevented by React auto-escape, sanitize photo filenames
- CSRF: not a concern with bearer token in localStorage (single-origin)
- Rate limiting: 10 req/min per IP on auth endpoints
- Data isolation: user_id FK on all queries (middleware check)

---

## 15. Testing Summary

### Frameworks
- Backend: pytest + httpx (TestClient)
- Frontend: Vitest + React Testing Library

### Test Inventory
- Backend: 16 tests (3 unit + 13 integration)
- Frontend: 20 tests (12 component + 6 unit + 2 infrastructure)
- End-to-end: 1 comprehensive flow test
- Total: 37 tests

### Locations
```
api/tests/
├── conftest.py
├── test_auth.py                    ← T1, T2, T3
├── test_cvs.py                     ← T6, T7, T8
├── test_assets.py                  ← T9
├── test_templates.py               ← T10
├── test_preview.py                 ← T44              ⚡ Phase 4
├── test_sections.py                ← T13, T14, T15
├── unit/
│   ├── conftest.py
│   ├── test_security.py            ← T1 (password hashing, JWT)
│   └── test_schemas.py             ← T2, T15 (Pydantic validation)

web/src/
├── lib/store/__tests__/
│   ├── authStore.test.ts           ← T4
│   ├── cvStore.test.ts             ← T11
│   └── sectionInstanceStore.test.ts ← T46              ⚡ Phase 5
├── components/__tests__/
│   ├── LoginForm.test.tsx          ← T5
│   ├── RegisterForm.test.tsx       ← T5
│   ├── CvList.test.tsx             ← T12, T35.2       ⚡ Phase 3.5
│   ├── SectionList.test.tsx        ← T17, T18, T35.1  ⚡ Phase 5
│   ├── TemplateSwitcher.test.tsx   ← T19
│   ├── CustomizePanel.test.tsx     ← T20, T48          ⚡ Phase 6
│   ├── SectionEditors.test.tsx     ← T17, T35.3       ⚡ Phase 3.5
│   ├── AddSectionModal.test.tsx    ← T47              ⚡ Phase 6
│   ├── ExportButton.test.tsx       ← T53
│   └── Toast.test.tsx              ← T55
├── hooks/__tests__/
│   └── useAutoSave.test.ts         ← T51, T54
└── api/__tests__/
    └── client.test.ts              ← auth interceptor injection
```

---

## 16. Folder Structure

```
aergia/
├── docker-compose.yml
├── .env.example
│
├── api/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   │   └── env.py
│   ├── main.py
│   └── app/
│       ├── __init__.py
│       ├── app.py                      ← FastAPI app (mount routers + serve static)
│       ├── config.py                   ← pydantic-settings
│       ├── core/
│       │   ├── auth.py                 ← JWT create/verify/refresh
│       │   ├── deps.py                 ← FastAPI injection deps
│       │   └── auth.py                 ← bcrypt hashing + JWT
│       ├── db/
│       │   ├── session.py              ← SessionLocal, engine, Base
│       │   └── seed.py                 ← seed templates on boot
│       ├── models/
│       │   ├── user.py
│       │   ├── cv.py
│       │   └── template.py
│       ├── schemas/
│       │   ├── auth.py
│       │   ├── cv.py
│       │   ├── template.py
│       │   └── photo.py
│       ├── routes/
│       │   ├── auth.py
│       │   ├── cvs.py
│       │   └── assets.py
│       ├── services/
│       │   ├── auth.py
│       │   ├── cv.py
│       │   ├── photo.py
│       │   ├── pdf.py
│       │   └── renderer.py              ← HTML preview generation (Phase 4)
│       └── uploads/
│
├── web/
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── postcss.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── components/
│       │   ├── auth/
│       │   ├── builder/
│       │   ├── preview/
│       │   ├── cv-list/
│       │   │   ├── CvCard.tsx
│       │   │   ├── CreateCvModal.tsx          ← Phase 3.5
│       │   │   └── DeleteCvModal.tsx          ← Phase 3.5
│       │   ├── template-browser/
│       │   │   └── TemplateBrowser.tsx        ← Phase 3.5
│       │   ├── customization/
│       │   └── common/
│       │       ├── PhotoUpload.tsx
│       │       ├── ProtectedRoute.tsx
│       │       ├── Modal.tsx                  ← Phase 3.5 (shared)
│       │       └── AccordionPanel.tsx         ← Phase 3.5 (shared)
│       ├── lib/
│       │   ├── store/
│       │   ├── api/
│       │   ├── sections/
│       │   ├── validators/
│       │   │   ├── auth.ts                    ← login + register schemas
│       │   │   └── sections.ts               ← 7 section Zod schemas (Phase 4)
│       │   └── templates/
│       │       └── config.ts                 ← Frontend template metadata (Phase 3.5)
│       └── pages/
│
├── scripts/
│   └── seed_generic_templates.py
├── desktop/                            ← Tauri wrapper (future)
├── PLAN.md                             ← This file (will be in .gitignore)
├── .gitignore
└── README.md
```

---

## 17. Phased Development Plan

### Phase 1 — Foundation (Auth)

| # | Task | Status |
|---|---|---|---|
| 1 | Set up docker-compose.yml with Postgres service | ✅ |
| 2 | Initialize FastAPI project (main.py, config, models, schemas) | ✅ |
| 3 | Implement users model + table migration | ✅ |
| 4 | Auth: register, login, refresh, logout, change-password | ✅ |
| 5 | Initialize React + TS + Vite + Tailwind project | ✅ |
| 6 | Login + register pages with forms (HookForm + Zod) | ✅ |
| 7 | Zustand authStore + JWT token management | ✅ |
| 8 | Axios interceptor for Bearer token | ✅ |
| 9 | Protected routes (redirect to login if unauthenticated) | ✅ |
| T1 | Pytest: password hashing + JWT creation/validation (unit) | ✅ |
| T2 | Pytest: register endpoint schema validation (unit) | ✅ |
| T3 | Pytest: auth flow (register → login → protected call → logout) (integration) | ✅ |
| T4 | Vitest: authStore actions (login, logout, refresh) (unit) | ✅ |
| T5 | Vitest: register + login form validation + submission (component) | ✅ |
| 10 | Manual test: register → login → protected API call → logout | ☐ |

### Phase 2 — CV Core

| # | Task | Status |
|---|---|---|
| 11 | Implement cvs + templates models + migrations | ✅ |
| 12 | CV CRUD endpoints (list, create, get, update, delete, copy) | ✅ |
| 13 | Seed 3 generic templates (modern, classic, minimal) | ✅ |
| 14 | CV list page with cards (title, template indicator, actions) | ✅ |
| 15 | Copy/clone CV UI (copy action on card) | ✅ |
| 16 | Build builder page layout (split pane: editor | preview) | ✅ |
| 17 | Asset upload endpoint (filesystem) + photo UI | ✅ |
| T6 | Pytest: CV CRUD flow (create → get → update → delete) | ✅ |
| T7 | Pytest: CV copy creates independent clone | ✅ |
| T8 | Pytest: CV data isolation by user_id | ✅ |
| T9 | Pytest: photo upload (valid + invalid file, size limit) | ✅ |
| T10 | Pytest: template seed creates 3 templates | ✅ |
| T11 | Vitest: cvStore actions (create, copy, delete, save) | ✅ |
| T12 | Vitest: cvList page renders cards with actions | ✅ |
| 18 | Manual test: create CV → see in list → copy → both work | ☐ |

### Phase 3 — Sections + Preview

| # | Task | Status |
|---|---|---|
| 19 | ProfileSection editor + renderer | ✅ |
| 20 | ExperienceSection editor (repeatable entries) + renderer | ✅ |
| 21 | EducationSection editor + renderer | ✅ |
| 22 | SkillsSection editor + renderer | ✅ |
| 23 | ProjectsSection editor + renderer | ✅ |
| 24 | LanguagesSection editor + renderer | ✅ |
| 25 | CertificationsSection editor + renderer | ✅ |
| 26 | Section list with drag-and-drop (dnd-kit) | ✅ |
| 27 | Enable/disable section toggles | ✅ |
| 28 | Build generic-modern template renderer | ✅ |
| 29 | Build generic-classic template renderer | ✅ |
| 30 | Build generic-minimal template renderer | ✅ |
| 31 | Template switching in preview (instant) | ✅ |
| 32 | Customization panel (color, font, spacing) | ✅ |
| T13 | Pytest: section data stored correctly in JSONB | ✅ |
| T14 | Pytest: section ordering preserved through update | ✅ |
| T15 | Pytest: validation rejects invalid section data | ✅ |
| T16 | Pytest: all 3 templates render preview HTML correctly | ✅ |
| T17 | Vitest: each section editor renders + accepts input (7 tests) | ✅ |
| T18 | Vitest: section drag-and-drop reorders correctly | ✅ |
| T19 | Vitest: template switcher swaps renderer + applies config | ✅ |
| T20 | Vitest: customization panel updates CSS variables | ✅ |

### Phase 3.5 — Polish & UX (NEW)

| # | Task | Status |
|---|---|---|
| 33 | Install lucide-react, motion, @tailwindcss/forms | ✅ |
| 34 | Create shared Modal + AccordionPanel components | ✅ |
| 35 | Replace enable/disable checkboxes with eye icons (Eye/EyeOff) | ✅ |
| 36 | Create CV modal (title + template selection) | ✅ |
| 37 | Delete CV confirmation modal | ✅ |
| 38 | Repeatable entry accordion (6 section editors) | ✅ |
| 39 | CV grid layout refinement (responsive cols, card polish) | ✅ |
| 40 | Add Section UI (dropdown to add new section types) | ✅ |
| 41 | Template Browser UI (visual template selector in builder) | ✅ |
| 42 | Motion animations across all components | ✅ |
| T35.1 | Vitest: section list eye icons, add section dropdown | ✅ |
| T35.2 | Vitest: create/delete CV modals | ☐ |
| T35.3 | Vitest: accordion expand/collapse on all 6 editors | ☐ |

### Phase 4 — Data Integrity & Backend Preview (NEW)

| # | Task | Status |
|---|---|---|
| 43 | Section Zod validation schemas (7 sections) | ✅ |
| 44 | Backend preview endpoint (HTML renderer service + route) | ✅ |
| T44 | Pytest: preview endpoint renders correct HTML for all 3 templates | ✅ |

### Phase 5 — Section Instance Model (Architectural Refactor)

The core data model for sections is restructured from `{ order, enabled, data }` to `SectionInstance[]`. This enables multiple sections of the same type, per-instance custom titles, and a simpler data flow throughout the app.

| # | Task | Status |
|---|---|---|---|
| 45 | Define `SectionInstance` type + restructure `types.ts` | ✅ |
| 46 | Update `cvStore.ts` with instance CRUD (add, remove, reorder, toggle, rename) | ✅ |
| 47 | Update `SectionList.tsx` + `SectionEditorPanel.tsx` + `SectionRegistry.tsx` for instances | ✅ |
| 48 | Update `TemplateSwitcher.tsx` + all 3 template renderers to accept instances[] | ✅ |
| 49 | Update `BuilderPage.tsx` — replace old section handlers with instance-focused ones | ✅ |
| 50 | Default: new CVs start with only 1 enabled profile instance | ✅ |
| 51 | Update backend `CVCreate` default, `renderer.py` for new format | ✅ |
| 52 | Investigate & fix sub-section CRUD controls (trace EducationEditor → PATCH → reload) | ✅ |
| T45 | Update existing test data shapes for new SectionInstance format | ✅ |
| T46 | Vitest: section instance CRUD (add, remove, reorder, toggle, rename) | ✅ |

### Phase 6 — Add Section Modal & Customization UX

| # | Task | Status |
|---|---|---|
| 53 | Grid modal for adding sections (replaces dropdown, 3-column card grid) | ✅ |
| 54 | Collapsible customization panel (toggle icon in builder header) | ✅ |
| 55 | Inline section title editing (click title → text input) | ✅ |
| T47 | Vitest: add section grid modal renders all types, click adds instance | ✅ |
| T48 | Vitest: customization panel hidden by default, icon toggles visibility | ✅ |

### Phase 7 — PDF Export & Auto-Save

| # | Task | Status |
|---|---|---|
| 56 | In-process PDF export (Playwright) | ✅ |
| 57 | Preview = PDF exact match (print styles) | ✅ |
| 58 | Auto-save with debounce (3s) | ✅ |
| 59 | Validation errors display (Zod + components) | ✅ |
| 60 | Toast notifications, loading states, empty states | ✅ |
| 61 | Error handling UI (ErrorBoundary, axios toasts) | ✅ |
| 56.5 | Routing paths overhaul (AppLayout, Settings, 404) | ✅ |
| T49 | Pytest: PDF export returns valid PDF for all templates | ✅ |
| T50 | Pytest: PDF content matches CV data | ✅ |
| T51 | Pytest/TS: auto-save debounces correctly (unit) | ☐ |
| T52 | Pytest: PDF export fails gracefully for non-existent CV | ✅ |
| T53 | Vitest: PDF export trigger + success/fail handling | ☐ |
| T54 | Vitest: auto-save debounced save fires at correct interval | ☐ |
| T55 | Vitest: toast system renders success/error (component) | ☐ |
| T56 | E2E: full user journey (login → create → edit → switch template → export → logout) | ☐ |
| 62 | Final integration testing | ☐ |

### Phase 8 — Production Deployment ✅

| # | Task | Status |
|---|---|---|
| 8.1 | Docker Compose: add api service with uploads volume | ✅ |
| 8.2 | Multi-stage Dockerfile (frontend builds inside API image) | ✅ |
| 8.3 | dev.sh: playwright install, .env loading, --prod/--build flags | ✅ |
| 8.4 | Rate limiting with slowapi (auth 10/min, global 100/min) | ✅ |
| 8.5 | Enhanced health check + security middleware | ✅ |
| 8.6 | DEPLOY.md documentation | ✅ |

### Phase 9 — Builder UX & Polish

| # | Task | Status |
|---|---|---|
| 63 | Delete confirmation modal on section remove | ✅ |
| 64 | Sub-section accordions closed by default | ✅ |
| 65 | Sub-section drag-to-reorder via dnd-kit (6 editors) | ✅ |
| 66 | Builder tabs: replace side-by-side panel with "Content" / "Customize" tabs | ✅ |
| T9.1 | Vitest: section delete modal renders and confirms/aborts | ☐ |
| T9.2 | Vitest: accordion starts closed by default | ☐ |
| T9.3 | Vitest: sub-section drag reorders entries array correctly | ☐ |
| T9.4 | Vitest: builder tab switching renders correct panel | ☐ |
| 67 | Manual test: full flow — reorder sub-sections in experience, confirm order persists after reload | ☐ |

### Phase 9.5 — Bug Fixes for Phase 9

| # | Task | Status |
|---|---|---|
| 9.5.1 | Install @testing-library/user-event (missing dep) | ✅ |
| 9.5.2 | Fix localStorage not available in jsdom (authStore tests) | ✅ |
| 9.5.3 | Delete stale sectionInstanceStore.test.ts (methods removed from cvStore) | ✅ |
| 9.5.4 | Fix SectionEditors.test.tsx: click accordion to expand before asserting fields | ✅ |
| 9.5.5 | Fix CustomizePanel.test.tsx: add missing store mocks, rewrite T48 for tab layout | ✅ |
| 9.5.6 | Single DndContext refactor: unify nested DndContexts to fix sub-section drag auto-save | ✅ |
| T9.5 | All frontend tests pass (0 failures) | ✅ |

### Phase 10 — Customize Tab Enhancement & UI Cleanup

| # | Task | Status |
|---|---|---|
| 70 | Remove Palette button from BuilderPage header | ✅ |
| 71 | Remove template "Change" badge from BuilderPage header | ✅ |
| 72 | Add `templateId` and `onTemplateChange` props to `CustomizePanel` + inline template selector (3 cards: Modern, Classic, Minimal) | ✅ |
| 73 | Remove `TemplateBrowser` modal component entirely | ✅ |
| 74 | Remove `showTemplateBrowser` state and related logic from `BuilderPage` | ✅ |
| 75 | Clean up unused imports in `BuilderPage` | ✅ |
| T10.1 | Vitest: CustomizePanel renders inline template selector with correct active state | ☐ |
| T10.2 | Vitest: clicking a template card triggers `onTemplateChange` | ☐ |
| T10.3 | Vitest: template selector only visible in Customize tab (not Content) | ☐ |
| 76 | Manual test: switch template from Customize → preview updates → persists after reload | ☐ |

**Files changed:**
- `web/src/pages/BuilderPage.tsx` — removed Palette button, template badge, TemplateBrowser import/modal/state
- `web/src/components/customization/CustomizePanel.tsx` — added inline template cards at top
- `web/src/components/template-browser/TemplateBrowser.tsx` — deleted (replaced by inline selector)
- `web/src/components/__tests__/CustomizePanel.test.tsx` — updated props, replaced Palette-button tests with tab-bar tests

### Phase 10.5 — Per-Instance Style Overrides

**Goal:** Let users customize font, color, and weight on individual section instances (by `id`). Global styles remain as defaults. Per-instance overrides beat globals. Changing templates strips all per-instance styles.

**No DB migration needed** — `SectionInstance[]` is stored as JSONB. The new `style` field passes through automatically. No Pydantic schema change needed.

| # | Task | Status |
|---|---|---|
| 78 | Add `SectionStyle` type (`font`, `color`, `weight`) + `style?: SectionStyle` to `SectionInstance` in `types.ts` | ☐ |
| 79 | Add `section-{type}` CSS class to preview wrapper in `SectionPreviewPanel.tsx` | ☐ |
| 80 | Apply `instance.style` inline overrides (font, color, weight) in `SectionPreviewPanel` — on wrapper div + heading | ☐ |
| 81 | Add `onUpdateStyle: (sectionId, style)` callback, thread through `SectionList` | ☐ |
| 82 | Add collapsible "Style" sub-panel (Font, Color, Weight controls) in each section's accordion | ☐ |
| 83 | Wire `handleUpdateStyle` in `BuilderPage.tsx` → `setLocalInstances` | ☐ |
| 84 | In `handleTemplateChange`, strip `style` from all instances before saving | ☐ |
| 85 | Manual test: set per-instance style → preview updates → switch template → styles reset | ☐ |
| 86 | Update backend `renderer.py` to apply per-instance styles in `render_instance_panel` | ☐ |
| T11.1 | Vitest: `onUpdateStyle` fires with correct values | ☐ |
| T11.2 | Vitest: `SectionPreviewPanel` renders with per-instance styles applied | ☐ |
| T11.3 | Vitest: `section-{type}` class present on preview wrapper | ☐ |
| T11.4 | Vitest: template change strips per-instance styles | ☐ |
| T11.5 | Pytest: backend renders per-instance styles | ☐ |

### Phase 11 — Desktop Tauri (moved from old Phase 9)

| # | Task | Status |
|---|---|---|
| 11.1 | Initialize Tauri 2.x in `desktop/` | ☐ |
| 11.2 | Configure Tauri to load `http://api-server:8000/` | ☐ |
| 11.3 | Add native menu + system tray | ☐ |

---

## 18. Frontend Serving (Single Origin)

FastAPI serves static files directly from the built React app:

```
Single image (api:8000):
  /              → index.html (SPA entry)
  /static/*      → bundled JS/CSS assets
  /api/v1/*      → API routes
  /uploads/*     → user uploaded photos
```

Static serving implemented in `app.py` — mounts `StaticFiles` for `/static/` and `/uploads/`, with an SPA catch-all for client-side routing.

No reverse proxy required. The FastAPI app is the only web server.

---

## 19. Key Configuration Files

### .env
```
DATABASE_URL=postgresql+asyncpg://aergia_user:aergia_pass@postgres:5432/aergia
SECRET_KEY=generate_with_secrets module
```

### API dependencies
```
fastapi>=0.115
uvicorn[standard]>=0.30
sqlalchemy>=2.0
alembic>=1.13
asyncpg>=0.29
python-jose[cryptography]>=3.3
bcrypt>=4.1
python-multipart>=0.0.9
pydantic>=2.7
pypdf>=4.2
pillow>=10.4
slowapi>=0.1.9
playwright>=1.48
```

