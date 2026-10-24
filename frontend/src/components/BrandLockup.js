import { BRAND } from '../config/brand';

// App-side brand lockup: the "N" mark on a white tile and the wordmark. The landing page has its own (landing/Logo.js).
export default function BrandLockup({ mark = true }) {
  return (
    <span className="brand-lockup">
      {mark && <img className="brand-mark" src={BRAND.mark} alt="" width="28" height="28" />}
      <span>{BRAND.name.slice(0, 5)}<b>{BRAND.name.slice(5)}</b></span>
    </span>
  );
}
