import { Link, useLocation } from 'react-router-dom';
import { useFetch } from '../hooks/useFetch';
import { Loading, Alert } from './ui';

/**
 * Gate: when ZeroQ is required for the school, students must have a ZeroQ pass
 * before they can use Results, Fees, Timetable, etc.
 * CareerGPS is recommended but does not hard-block (link is still prominent).
 */
export default function ModuleGate({ children, requireZeroQ = true }) {
  const location = useLocation();
  const allowed = ['/student/zeroq', '/student/careergps', '/student/onboarding', '/student/application', '/student/settings', '/student/profile'];
  const isAllowedPath = allowed.some((p) => location.pathname.startsWith(p));

  const { data, loading } = useFetch(requireZeroQ && !isAllowedPath ? '/zeroq/my' : null);

  if (!requireZeroQ || isAllowedPath) return children;
  if (loading) return <Loading />;

  // No ZeroQ record or no active pass → block
  const hasPass = data && data.pass && data.pass.status === 'active';
  if (!hasPass) {
    return (
      <div className="stack" style={{ maxWidth: 520, margin: '2rem auto' }}>
        <div className="card">
          <h2>ZeroQ account required</h2>
          <p>You need an active ZeroQ pass before you can use Results, Fees, Timetable and other school features.</p>
          <Alert>ZeroQ is an independent module. Complete it first, then come back here.</Alert>
          <div style={{ marginTop: '1.25rem' }}>
            <Link to="/student/zeroq" className="btn primary" style={{ display: 'inline-block', padding: '.75rem 1.5rem', textDecoration: 'none' }}>
              Open ZeroQ →
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return children;
}
