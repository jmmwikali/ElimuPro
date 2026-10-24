// Single source of truth for the public brand. Change a value here (or the tagline through
// REACT_APP_BRAND_TAGLINE at build time) and every screen follows.
// Left out on purpose until confirmed: website URL, support email/phone, social links.
const PUBLIC = process.env.PUBLIC_URL || '';

export const BRAND = {
  name: 'ElimuNova',
  tagline: process.env.REACT_APP_BRAND_TAGLINE || 'Reimagining Education. Empowering Every Future.',
  description: 'ElimuNova is an integrated education platform connecting students, schools, parents and teachers.',
  mark: `${PUBLIC}/brand/elimunova-mark.png`,
  logoLight: `${PUBLIC}/brand/elimunova-logo-light.png`,
  logoDark: `${PUBLIC}/brand/elimunova-logo-dark.png`,
  // Brand sheet palette. Used for the wordmark only; the app's existing colours are unchanged.
  colors: { purple: '#8A4DFF', indigo: '#6B5BFF', blue: '#3B84FF', ink: '#1A1F36' },
};

export default BRAND;
