# Frontend raster asset inventory

This inventory records every raster image referenced by the shipping templates and static frontend assets as of the frontend-redesign finishing pass. It is intentionally limited to product assets; review screenshots under `.impeccable/review/` are QA evidence and do not ship.

## Independent inventory

| Asset | Origin | Technical inspection | Shipping references | Disposition |
|---|---|---|---|---|
| Canonical devLink logo source | `https://ss-static-001.esmsv.com/r/content/host2/4172d4e2978b9da867fe259f4df844c8//editor/transparente.webp` | WebP, 1024×1024, RGBA, transparent, one frame. SHA-256 `3973F2646611263C465CD369AE82C3F64E712B7DED30A9A6D4329F4A846DF265`. | 22 references across the public site, login, legal/docs pages, welcome email, Suite Lite campaign email, and email preview. | Authoritative pre-existing project source. Retained as the visual source of truth. |
| Pinterest-hosted logo copy | `https://i.pinimg.com/736x/91/ed/e3/91ede3b85e27883ee1d20c0539b0bf60.jpg` | JPEG, 736×736, RGB, opaque white canvas. SHA-256 `D0707D8A462335A8F1C13F93145BA195148918641D23A6666D897D3CC6618EF7`. | Three references: two in `templates/email-campana-chatbot-webapp.html` and one in `templates/email-campana-servicios-inline.html`. | Reject for shipping: third-party Pinterest dependency, opaque background, and no project-controlled provenance. Replace with the canonical email PNG below. |
| Canonical email-safe devLink logo | `static/images/devlink-logo-email.png` | PNG, 1024×1024, RGBA, transparent. Decoded pixels are identical to the canonical WebP source. SHA-256 after embedded provenance: `67F9643AAAE6F50EB60C159381DA755DF02C3B9CABA61B264F69CBBDD991F116`. | Intended canonical URL: `https://devlink.com.ar/static/images/devlink-logo-email.png`. | Shipping replacement for every email logo raster. The exact source origin is embedded in the PNG `impeccable:prompt` text chunk. |

No other PNG, JPEG, WebP, GIF, ICO, raster data URI, or CSS raster URL is referenced by the shipping `templates/` and `static/` trees.

## Production record

- Source origin embedded verbatim: `Origin: https://ss-static-001.esmsv.com/r/content/host2/4172d4e2978b9da867fe259f4df844c8//editor/transparente.webp`
- Processing: decoded the existing 1024×1024 RGBA WebP and saved the same pixel grid as an optimized PNG. No crop, resize, recolor, redraw, or generative modification was applied.
- Transparency: preserved; alpha extrema remain 0–255 and the non-transparent bounding box remains `(68, 153, 950, 887)`.
- Email rationale: PNG is broadly supported by email clients and avoids the opaque white canvas of the Pinterest JPEG while preserving the established logo on the dark navy email header.
