# Task 7 verification/evidence report

## Status

Verification evidence and the single detector/mechanical-fix pass are complete. The controller-owned independent finish review and `DESIGN.md` remain intentionally pending under the binding ordering ruling. No reviewer/documenter was spawned and `DESIGN.md` was not created or modified.

## Functional verification

- Initial `python manage.py test -v 2`: PASS — 30 tests, 0 failures/errors, 52.355s. Playwright/installed-Chrome behavior tests ran rather than skipping.
- Final post-fix `python manage.py test -v 2`: PASS — 30 tests, 0 failures/errors, 15.623s. Output ended with `OK` and `System check identified no issues (0 silenced)`.
- Initial and final `python manage.py check`: PASS — `System check identified no issues (0 silenced)`.
- `git diff --check`: clean (only Git's expected LF→CRLF working-copy notices were emitted).

### Live-server environment isolation

`python manage.py runserver 127.0.0.1:8000 --noreload` completed Django's system checks but did not bind port 8000. It blocked in `BaseCommand.check_migrations()` while `MigrationExecutor` attempted the configured remote PostgreSQL connection through psycopg. The process was interrupted after a separate request confirmed that 127.0.0.1:8000 was not accepting connections. This is isolated from the frontend implementation: the full test suite intentionally skips the unused database and passed.

Public and authenticated evidence therefore uses Django's real `render_to_string` path with `RequestFactory`, the production templates/routes/stylesheet/scripts, and controlled representative context objects. This is the brief-authorized fallback for unavailable PostgreSQL/Mongo-backed pages; it does not write representative values into production content.

## Screenshot evidence

Capture engine: installed Chrome through Playwright. Desktop viewport: 1440×900. Mobile viewport: 390×844. Every context emulated reduced motion, disabled residual animation/transition during capture, scrolled to `0`, waited for fonts, captured full page, and validated non-trivial text plus a non-black background. The final 20 PNGs were each opened and visually inspected once after the mechanical fixes.

Automated manifest: `.impeccable/review/capture-manifest.json` (18 entries). Every entry records:

- `scrollY: 0`
- `horizontalOverflowPx: 0`
- `consoleErrors: []`
- installed Chrome as the browser
- a light non-black body background

Reproducible capture harness: `.impeccable/review/capture_screenshots.py`.

Core required captures:

- `.impeccable/review/desktop.png`
- `.impeccable/review/mobile.png`

Per-surface reviewed captures:

- Homepage: `homepage-desktop.png`, `homepage-mobile.png`
- Login: `login-desktop.png`, `login-mobile.png`
- Documentation: `docs-desktop.png`, `docs-mobile.png`
- Client dashboard: `client-dashboard-desktop.png`, `client-dashboard-mobile.png`
- Client WhatsApp report: `client-report-desktop.png`, `client-report-mobile.png`
- Client editor: `client-editor-desktop.png`, `client-editor-mobile.png`
- Admin dashboard: `admin-dashboard-desktop.png`, `admin-dashboard-mobile.png`
- Admin user list: `admin-users-list-desktop.png`, `admin-users-list-mobile.png`
- Admin user form: `admin-user-form-desktop.png`, `admin-user-form-mobile.png`

Visual-inspection result: no blank, black, top-offset, or wrong-surface capture. Narrow report/admin tables remain inside their intended horizontal scroll containers on mobile; their partial off-screen columns do not create page-level overflow. The client report's mobile update-status panel has generous unused vertical space and should be evaluated by the controller's independent visual reviewer; it was not changed because this phase was restricted to detector-reported mechanical fixes.

## Impeccable detector

Run count: exactly one. It was not rerun after fixes.

Command:

```powershell
node C:\Users\edespinoza\.codex\skills\impeccable\scripts\detect.mjs --json templates static/styles.css
```

Exit status: 1. The detector reported `DEGRADED` because `htmlparser2`, `css-select`, `css-tree`, and `domutils` were unavailable, then fell back to regex matching. It explicitly warned that custom properties, selector matching, and computed contrast were not evaluated and that findings are an undercount.

### Exact JSON findings

```json
[
  {
    "antipattern": "side-tab",
    "name": "Side-tab accent border",
    "description": "Thick colored border on one side of a card — the most recognizable tell of AI-generated UIs. Use a subtler accent or remove it entirely.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-bienvenida.html",
    "line": 3,
    "snippet": "border-left:4px solid #1264f6"
  },
  {
    "antipattern": "overused-font",
    "name": "Overused font",
    "description": "Inter, Roboto, Fraunces, Geist, Plus Jakarta Sans, and Space Grotesk are used on so many sites they no longer feel distinctive. Each new wave of AI-generated UIs converges on the same handful of faces. Choose a face that gives your interface personality.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-bienvenida.html",
    "line": 1,
    "snippet": "font-family:Arial"
  },
  {
    "antipattern": "flat-type-hierarchy",
    "name": "Flat type hierarchy",
    "description": "Font sizes are too close together — no clear visual hierarchy. Use fewer sizes with more contrast (aim for at least a 1.25 ratio between steps).",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-bienvenida.html",
    "line": 1,
    "snippet": "Sizes: 16px, 18px, 20px (ratio 1.3:1)"
  },
  {
    "antipattern": "side-tab",
    "name": "Side-tab accent border",
    "description": "Thick colored border on one side of a card — the most recognizable tell of AI-generated UIs. Use a subtler accent or remove it entirely.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-chatbot-webapp.html",
    "line": 10,
    "snippet": "border-left:4px solid #06d6ff"
  },
  {
    "antipattern": "border-accent-on-rounded",
    "name": "Border accent on rounded element",
    "description": "Thick accent border on a rounded card — the border clashes with the rounded corners. Remove the border or the border-radius.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-chatbot-webapp.html",
    "line": 16,
    "snippet": "border-top:4px solid"
  },
  {
    "antipattern": "overused-font",
    "name": "Overused font",
    "description": "Inter, Roboto, Fraunces, Geist, Plus Jakarta Sans, and Space Grotesk are used on so many sites they no longer feel distinctive. Each new wave of AI-generated UIs converges on the same handful of faces. Choose a face that gives your interface personality.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-chatbot-webapp.html",
    "line": 4,
    "snippet": "font-family:Arial"
  },
  {
    "antipattern": "side-tab",
    "name": "Side-tab accent border",
    "description": "Thick colored border on one side of a card — the most recognizable tell of AI-generated UIs. Use a subtler accent or remove it entirely.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-servicios-inline.html",
    "line": 80,
    "snippet": "border-left: 4px solid #07162d"
  },
  {
    "antipattern": "side-tab",
    "name": "Side-tab accent border",
    "description": "Thick colored border on one side of a card — the most recognizable tell of AI-generated UIs. Use a subtler accent or remove it entirely.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-servicios-inline.html",
    "line": 104,
    "snippet": "border-left: 4px solid #1264f6"
  },
  {
    "antipattern": "side-tab",
    "name": "Side-tab accent border",
    "description": "Thick colored border on one side of a card — the most recognizable tell of AI-generated UIs. Use a subtler accent or remove it entirely.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-servicios-inline.html",
    "line": 128,
    "snippet": "border-left: 4px solid #06d6ff"
  },
  {
    "antipattern": "side-tab",
    "name": "Side-tab accent border",
    "description": "Thick colored border on one side of a card — the most recognizable tell of AI-generated UIs. Use a subtler accent or remove it entirely.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-servicios-inline.html",
    "line": 152,
    "snippet": "border-left: 4px solid #06d6ff"
  },
  {
    "antipattern": "side-tab",
    "name": "Side-tab accent border",
    "description": "Thick colored border on one side of a card — the most recognizable tell of AI-generated UIs. Use a subtler accent or remove it entirely.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-suite-lite-inline.html",
    "line": 44,
    "snippet": "border-left: 3px solid #1264f6"
  },
  {
    "antipattern": "side-tab",
    "name": "Side-tab accent border",
    "description": "Thick colored border on one side of a card — the most recognizable tell of AI-generated UIs. Use a subtler accent or remove it entirely.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-suite-lite-inline.html",
    "line": 45,
    "snippet": "border-left: 3px solid #06d6ff"
  },
  {
    "antipattern": "overused-font",
    "name": "Overused font",
    "description": "Inter, Roboto, Fraunces, Geist, Plus Jakarta Sans, and Space Grotesk are used on so many sites they no longer feel distinctive. Each new wave of AI-generated UIs converges on the same handful of faces. Choose a face that gives your interface personality.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-campana-suite-lite-inline.html",
    "line": 23,
    "snippet": "font-family: Arial"
  },
  {
    "antipattern": "overused-font",
    "name": "Overused font",
    "description": "Inter, Roboto, Fraunces, Geist, Plus Jakarta Sans, and Space Grotesk are used on so many sites they no longer feel distinctive. Each new wave of AI-generated UIs converges on the same handful of faces. Choose a face that gives your interface personality.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\templates\\email-preview.html",
    "line": 1,
    "snippet": "font-family:Arial"
  },
  {
    "antipattern": "side-tab",
    "name": "Side-tab accent border",
    "description": "Thick colored border on one side of a card — the most recognizable tell of AI-generated UIs. Use a subtler accent or remove it entirely.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\static\\styles.css",
    "line": 1585,
    "snippet": "border-left: 3px solid var(--brand-500)"
  },
  {
    "antipattern": "overused-font",
    "name": "Overused font",
    "description": "Inter, Roboto, Fraunces, Geist, Plus Jakarta Sans, and Space Grotesk are used on so many sites they no longer feel distinctive. Each new wave of AI-generated UIs converges on the same handful of faces. Choose a face that gives your interface personality.",
    "severity": "warning",
    "category": "slop",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\static\\styles.css",
    "line": 87,
    "snippet": "font-family: Inter"
  },
  {
    "antipattern": "layout-transition",
    "name": "Layout property animation",
    "description": "Animating width, height, padding, or margin causes layout thrash and janky performance. Use transform and opacity instead, or grid-template-rows for height animations.",
    "severity": "warning",
    "category": "quality",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\static\\styles.css",
    "line": 759,
    "snippet": "transition: padding-top"
  },
  {
    "antipattern": "layout-transition",
    "name": "Layout property animation",
    "description": "Animating width, height, padding, or margin causes layout thrash and janky performance. Use transform and opacity instead, or grid-template-rows for height animations.",
    "severity": "warning",
    "category": "quality",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\static\\styles.css",
    "line": 1242,
    "snippet": "transition: padding"
  },
  {
    "antipattern": "layout-transition",
    "name": "Layout property animation",
    "description": "Animating width, height, padding, or margin causes layout thrash and janky performance. Use transform and opacity instead, or grid-template-rows for height animations.",
    "severity": "warning",
    "category": "quality",
    "file": "D:\\devLink_web\\.worktrees\\frontend-redesign\\static\\styles.css",
    "line": 2584,
    "snippet": "transition: padding"
  }
]
```

## Mechanical fix batch

Applied once with `apply_patch`; detector was not rerun afterward.

- Replaced thick one-sided email/card accents with quiet one-pixel full borders, including matching preview markup.
- Replaced the rounded CTA's thick top accent with a one-pixel border.
- Replaced detector-flagged Arial/Inter declarations with compatible Tahoma/Verdana email stacks and a local Segoe Variable/system web stack.
- Increased the welcome email section heading step from 20px to 24px to make the 16/18/24 hierarchy explicit.
- Replaced padding transitions and padding-hover shifts with transform-based hover movement; stabilized the fixed-header content offset.
- Converted `.form-interest` from a 3px side tab/asymmetric radius to a one-pixel full border/10px radius.

Because the detector could not be rerun under the one-run rule, targeted source checks were used only to confirm removal of the exact mechanical patterns. Post-fix `rg` checks found no 3–4px left/right accents, no transition declaration animating padding/width/height/margin, and none of the detector-flagged Arial/Inter declarations in `templates` or `static/styles.css`.

## Concerns and handoff

- Detector coverage is degraded/regex-only due missing parser modules; its 19 warnings are not a complete computed-style/accessibility audit.
- Live route serving remains blocked by the configured remote PostgreSQL migration check; the controlled Chrome render path is fully documented and reproducible.
- The independent finish verdict and `DESIGN.md` are still required after this evidence commit and are intentionally left to the controller.
- No production content, routes, database behavior, permissions, forms, or template conditions were fabricated or changed by this phase.
