# Branding: ElimuNova

The platform was renamed from ElimuPro to **ElimuNova**. This page records what changed, what was kept on purpose,
and what still needs a decision from you.

## Central configuration

| Where | What |
| --- | --- |
| `frontend/src/config/brand.js` | Name, tagline, description, logo paths, brand palette. Every screen reads it. |
| `REACT_APP_BRAND_TAGLINE` (build time) / `BRAND_TAGLINE` (API env) | Change the tagline without touching code. Default: "Reimagining Education. Empowering Every Future." |
| `backend/app/config/__init__.py` (`BRAND_NAME`) | Used by Apex AI and API messages. |
| `frontend/src/components/BrandLockup.js`, `landing/Logo.js` | The only two places that draw the logo and wordmark. |

Not set because they are not confirmed: website URL, support email or phone, social links, canonical URL, sitemap.

## What changed

- Landing page, navigation, footer, sign-in and sign-up pages, sidebars, mobile menu, platform console, Billing,
  Pricing, ZeroQ student page, Apex AI (assistant name, prompts, component list, API messages).
- Page title, meta description, Open Graph and Twitter tags, install manifest (name and short name), favicon, app icons.
- Logo: the "N" mark (white tile, as in the brand sheet's app icon) beside the wordmark. App icons, `favicon-32.png`,
  `og-image.png` and `brand/*` are cut from the supplied brand images. `careergps-logo.png` had "by ElimuPro" painted into
  the picture, so that line now reads "by ElimuNova". `zeroq-logo.svg` text updated.
- Documentation: README, Apex AI, Billing, ZeroQ.
- Service worker cache renamed `elimupro-shell-v1` to `elimunova-shell-v1`; on first load the old cache is deleted so
  installed copies pick up the new icons.

## Kept on purpose (renaming would break something)

| Identifier | Why it stays |
| --- | --- |
| `elimupro_token` (browser storage key), `elimupro:unauthorized` (event) | Renaming signs every user out. |
| `elimupro` database name and user (compose, `.env.example`, SETUP) | Existing databases and volumes use it. |
| `"service": "ElimuPro API"` in `/health` | Uptime monitors may match on it. Change it when you update the monitors. |
| `*@elimupro.demo` demo logins | Seeded accounts, test fixtures and README credentials. |
| npm package name `elimupro-frontend`, GitHub repository, Vercel project names | Tied to deployments and integrations. |
| `elimupro-logo.png` | Old unused file; not deleted. |
| Module names ZeroQ, CareerGPS, Apex AI | Unchanged; they appear as parts of ElimuNova. |

GradeGPS and SafeHaven AI are named in the rebrand brief, but they do not exist in this codebase. They are not added to
the site or to Apex AI's knowledge, so nothing claims features that are not built.

## Logo notes

- Two marks were supplied: the "N" (brand sheet, app icon, vertical logos) and an "E" horizontal logo from Meta AI. The
  brand sheet uses the N throughout, so the N is the official mark here. Tell me if the E should be used instead.
- The supplied images are phone screenshots. The crops are good for icons, the header and share previews. Request
  clean vector or transparent-background files from the designer for print work; `docs/brand/` holds a reference copy
  of the brand sheet (palette: purple #8A4DFF, indigo #6B5BFF, blue #3B84FF, ink #1A1F36).
- `og:image` needs an absolute URL. Build with `PUBLIC_URL=https://<your confirmed domain>`, and add `og:url` and a
  canonical link at that point.

## Connecting a new domain (when you own one)

1. Add the domain to the Vercel project and set the DNS records Vercel shows.
2. Set the API's `FRONTEND_URL` to the exact new origin (CORS) and rebuild the frontend with `PUBLIC_URL` set.
3. Update the Cyzora webhook URL if the API address changes, and any OAuth or email-link settings you add later.
4. Keep the old domain redirecting until traffic has moved.
