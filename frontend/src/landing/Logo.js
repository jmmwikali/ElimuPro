import { BRAND } from '../config/brand';

// The ElimuNova "N" mark on a white tile (as in the brand sheet's app icon) plus the wordmark.
export default function Logo({ light }) {
  return (
    <span className={`lp-brand${light ? ' light' : ''}`}>
      <span className="lp-logo-sq"><img src={BRAND.mark} alt="" width="34" height="34" /></span>
      <span>Elimu<b className="lp-nova">Nova</b></span>
    </span>
  );
}
