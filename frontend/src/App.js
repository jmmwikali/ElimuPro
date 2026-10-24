import { Navigate, Route, Routes } from 'react-router-dom';
import ProtectedRoute from './routes/ProtectedRoute';
import AppShell from './layouts/AppShell';
import { useAuth, homeFor } from './context/AuthContext';
import { BRAND } from './config/brand';
import Landing from './pages/Landing';
import AuthBook from './pages/AuthBook';
import Application from './pages/student/Application';
import Dashboard from './pages/student/Dashboard';
import { Profile, Results, Timetable, Fees, Announcements, Settings } from './pages/student/Pages';
import AdminDashboard from './pages/admin/Dashboard';
import { Applications, ApplicationDetail } from './pages/admin/Applications';
import { Students, StudentDetail } from './pages/admin/Students';
import Classes from './pages/admin/Classes';
import FeesAdmin from './pages/admin/Fees';
import AnnouncementsAdmin from './pages/admin/Announcements';
import Platform from './pages/admin/Platform';
import Pricing from './pages/admin/Pricing';
import Invoices from './pages/admin/Invoices';
import Billing from './pages/admin/Billing';
import Teachers from './pages/admin/Teachers';
import Parents from './pages/admin/Parents';
import ParentDashboard from './pages/parent/Dashboard';
import ParentChild from './pages/parent/Child';
import ParentAnnouncements from './pages/parent/Announcements';
import TeacherDashboard from './pages/teacher/Dashboard';
import TeacherClasses from './pages/teacher/Classes';
import TeacherResults from './pages/teacher/Results';
import TeacherAnnouncements from './pages/teacher/Announcements';
import ZeroQStudent from './pages/student/ZeroQ';
import Onboarding from './pages/student/Onboarding';
import ZeroQReview from './pages/admin/ZeroQReview';
import { ZeroQDashboard, ZeroQQueue, ZeroQScanner } from './pages/admin/ZeroQ';

const STUDENT_NAV = [
  { to: '/student', label: 'Home', icon: 'home', end: true }, { to: '/student/results', label: 'Results', icon: 'chart' },
  { to: '/student/timetable', label: 'Timetable', icon: 'clock' }, { to: '/student/fees', label: 'Fees', icon: 'wallet' },
  { to: '/student/zeroq', label: 'ZeroQ', icon: 'file' },
  { to: '/student/announcements', label: 'News', icon: 'bell' },
];
const STUDENT_SIDE = [...STUDENT_NAV, { to: '/student/onboarding', label: 'Admission progress', icon: 'chart' }, { to: '/student/profile', label: 'My Profile', icon: 'user' },
  { to: '/student/application', label: 'My Application', icon: 'file' }, { to: '/student/settings', label: 'Settings', icon: 'gear' }];
const APPLICANT_SIDE = [{ to: '/student/application', label: 'My Application', icon: 'file' }, { to: '/student/onboarding', label: 'Admission progress', icon: 'chart' }, { to: '/student/settings', label: 'Settings', icon: 'gear' }];

const ADMIN_NAV = [
  { to: '/admin', label: 'Dashboard', icon: 'home', end: true }, { to: '/admin/applications', label: 'Applications', icon: 'file' },
  { to: '/admin/zeroq', label: 'ZeroQ Admissions', icon: 'file' },
  { to: '/admin/zeroq-review', label: 'ZeroQ Review', icon: 'file' },
  { to: '/admin/students', label: 'Students', icon: 'users' }, { to: '/admin/teachers', label: 'Teachers', icon: 'book' }, { to: '/admin/parents', label: 'Parents', icon: 'users' }, { to: '/admin/classes', label: 'Classes & Streams', icon: 'school' },
  { to: '/admin/fees', label: 'Fees & Payments', icon: 'wallet' }, { to: '/admin/announcements', label: 'Announcements', icon: 'bell' },
  { to: '/admin/billing', label: 'Billing', icon: 'wallet' },
];
const BURSAR_NAV = [ADMIN_NAV[0], ADMIN_NAV.find((n) => n.to === '/admin/fees')];
const PLATFORM_NAV = [
  { to: '/platform', label: 'Schools', icon: 'school', end: true }, { to: '/platform/pricing', label: 'Pricing', icon: 'wallet' },
  { to: '/platform/invoices', label: 'Invoices', icon: 'file' },
];
const PARENT_NAV = [
  { to: '/parent', label: 'My children', icon: 'users', end: true }, { to: '/parent/announcements', label: 'News', icon: 'bell' },
  { to: '/parent/settings', label: 'Settings', icon: 'gear' },
];
const TEACHER_NAV = [
  { to: '/teacher', label: 'Home', icon: 'home', end: true }, { to: '/teacher/classes', label: 'Classes', icon: 'users' },
  { to: '/teacher/results', label: 'Results', icon: 'chart' }, { to: '/teacher/announcements', label: 'News', icon: 'bell' },
];

function StudentShell() {
  const { user } = useAuth();
  return user.is_enrolled
    ? <AppShell nav={STUDENT_SIDE} bottom={STUDENT_NAV} />
    : <AppShell nav={APPLICANT_SIDE} bottom={[{ to: '/student/application', label: 'Application', icon: 'file' }, { to: '/student/onboarding', label: 'Progress', icon: 'chart' }, { to: '/student/settings', label: 'Settings', icon: 'gear' }]} />;
}
function AdminShell() {
  const { user } = useAuth();
  return <AppShell nav={user.role === 'bursar' ? BURSAR_NAV : ADMIN_NAV} />;
}
function Home() { const { user, loading } = useAuth(); return loading ? null : user ? <Navigate to={homeFor(user)} replace /> : <Landing />; }

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      {/* /login and /signup share one persistent "open book" layout (AuthBook renders Login and Signup itself)
          so the page-turn can animate between them. Paths are unchanged. */}
      <Route element={<AuthBook />}>
        <Route path="/login" element={null} />
        <Route path="/signup" element={null} />
      </Route>

      <Route element={<ProtectedRoute roles={['student']} />}>
        <Route path="/student" element={<StudentShell />}>
          <Route index element={<Dashboard />} />
          <Route path="application" element={<Application />} />
          <Route path="onboarding" element={<Onboarding />} />
          <Route path="zeroq" element={<ZeroQStudent />} />
          <Route path="results" element={<Results />} />
          <Route path="timetable" element={<Timetable />} />
          <Route path="fees" element={<Fees />} />
          <Route path="announcements" element={<Announcements />} />
          <Route path="profile" element={<Profile />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute roles={['school_admin', 'principal', 'deputy_principal', 'bursar']} />}>
        <Route path="/admin" element={<AdminShell />}>
          <Route index element={<AdminDashboard />} />
          <Route path="fees" element={<FeesAdmin />} />
          <Route element={<ProtectedRoute roles={['school_admin', 'principal', 'deputy_principal']} />}>
            <Route path="applications" element={<Applications />} />
            <Route path="applications/:id" element={<ApplicationDetail />} />
            <Route path="zeroq" element={<ZeroQDashboard />} />
            <Route path="zeroq/queue" element={<ZeroQQueue />} />
            <Route path="zeroq-review" element={<ZeroQReview />} />
            <Route path="zeroq/scanner" element={<ZeroQScanner />} />
            <Route path="students" element={<Students />} />
            <Route path="students/:id" element={<StudentDetail />} />
            <Route path="teachers" element={<Teachers />} />
            <Route path="parents" element={<Parents />} />
            <Route path="classes" element={<Classes />} />
            <Route path="announcements" element={<AnnouncementsAdmin />} />
            <Route path="billing" element={<Billing />} />
          </Route>
        </Route>
      </Route>

      <Route element={<ProtectedRoute roles={['teacher', 'class_teacher']} />}>
        <Route path="/teacher" element={<AppShell nav={TEACHER_NAV} bottom={TEACHER_NAV} />}>
          <Route index element={<TeacherDashboard />} />
          <Route path="classes" element={<TeacherClasses />} />
          <Route path="results" element={<TeacherResults />} />
          <Route path="announcements" element={<TeacherAnnouncements />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute roles={['parent']} />}>
        <Route path="/parent" element={<AppShell nav={PARENT_NAV} bottom={PARENT_NAV} />}>
          <Route index element={<ParentDashboard />} />
          <Route path="children/:id" element={<ParentChild />} />
          <Route path="announcements" element={<ParentAnnouncements />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute roles={['super_admin']} />}>
        <Route path="/platform" element={<AppShell nav={PLATFORM_NAV} brandLabel={`${BRAND.name} Platform`} />}>
          <Route index element={<Platform />} />
          <Route path="pricing" element={<Pricing />} />
          <Route path="invoices" element={<Invoices />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}