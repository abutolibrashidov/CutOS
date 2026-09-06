import { Navigate, NavLink, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'

import { t } from './i18n/uz'
import { checkAdmin, getProfile } from './api/client'
import { ErrorState, LoadingState } from './components/Feedback'
import { BlockedTimesPage } from './pages/BlockedTimesPage'
import { DashboardPage } from './pages/DashboardPage'
import { ProfilePage } from './pages/ProfilePage'
import { SchedulePage } from './pages/SchedulePage'
import { ServicesPage } from './pages/ServicesPage'
import { BookingWizardPage } from './pages/BookingWizardPage'
import { MyAppointmentsPage } from './pages/MyAppointmentsPage'
import { BarberAppointmentsPage } from './pages/BarberAppointmentsPage'
import { AdminDashboardPage } from './pages/AdminDashboardPage'

const navigation = [
  { to: '/', label: 'NAV_HOME', icon: '⌂' },
  { to: '/buyurtmalar', label: 'NAV_APPOINTMENTS', icon: '▤' },
  { to: '/xizmatlar', label: 'NAV_SERVICES', icon: '✂' },
  { to: '/ish-vaqti', label: 'NAV_SCHEDULE', icon: '◷' },
  { to: '/band-vaqtlar', label: 'NAV_BLOCKED', icon: '▣' },
  { to: '/profil', label: 'NAV_PROFILE', icon: '◉' },
] as const

function WorkspaceLayout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="eyebrow">{t('APP_NAME')}</p>
      </header>
      <main className="page-content"><Outlet /></main>
      <nav className="bottom-nav" aria-label="Asosiy menyu">
        {navigation.map((item) => (
          <NavLink key={item.to} to={item.to} end={item.to === '/'} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span aria-hidden="true">{item.icon}</span>
            <span>{t(item.label)}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  )
}

function AdminLayout() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="eyebrow">{t('APP_NAME')} — {t('ADMIN_TITLE')}</p>
      </header>
      <main className="page-content"><Outlet /></main>
    </div>
  )
}

const customerNavigation = [
  { to: '/booking', label: 'BOOK_NOW', icon: '✂' },
  { to: '/buyurtmalarim', label: 'NAV_MY_BOOKINGS', icon: '◷' },
] as const

function CustomerLayout({ isBarber }: { isBarber: boolean }) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <p className="eyebrow">{t('APP_NAME')}</p>
      </header>
      <main className="page-content"><Outlet /></main>
      <nav className="bottom-nav" aria-label="Mijoz menyusi">
        {customerNavigation.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
            <span aria-hidden="true">{item.icon}</span>
            <span>{t(item.label)}</span>
          </NavLink>
        ))}
        {isBarber && (
          <NavLink to="/" className="nav-item">
            <span aria-hidden="true">⚙</span>
            <span>{t('NAV_HOME')}</span>
          </NavLink>
        )}
      </nav>
    </div>
  )
}

function App() {
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null)
  const [isBarber, setIsBarber] = useState<boolean | null>(null)
  const [loading, setLoading] = useState(true)

  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    async function checkUser() {
      try {
        const adminRes = await checkAdmin()
        if (adminRes?.is_admin === true) {
          setIsAdmin(true)
          setIsBarber(false)
          setLoading(false)
          return
        }
        setIsAdmin(false)
      } catch {
        setIsAdmin(false)
      }

      try {
        await getProfile()
        setIsBarber(true)
      } catch {
        setIsBarber(false)
      } finally {
        setLoading(false)
      }
    }
    void checkUser()
  }, [])

  useEffect(() => {
    if (!loading && isAdmin && location.pathname === '/') {
      navigate('/admin', { replace: true })
    }
  }, [loading, isAdmin, location.pathname, navigate])

  if (loading) return <LoadingState />

  return (
    <Routes>
      {/* Admin workspace */}
      {isAdmin ? (
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<AdminDashboardPage />} />
          <Route path="/" element={<Navigate to="/admin" replace />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Route>
      ) : isBarber ? (
        <>
          {/* Barber routes */}
          <Route element={<WorkspaceLayout />}>
            <Route path="/" element={<DashboardPage />} />
            <Route path="/buyurtmalar" element={<BarberAppointmentsPage />} />
            <Route path="/xizmatlar" element={<ServicesPage />} />
            <Route path="/ish-vaqti" element={<SchedulePage />} />
            <Route path="/band-vaqtlar" element={<BlockedTimesPage />} />
            <Route path="/profil" element={<ProfilePage />} />
            <Route path="*" element={<DashboardPage />} />
          </Route>

          {/* Customer routes accessible to barber */}
          <Route element={<CustomerLayout isBarber={true} />}>
            <Route path="/booking" element={<BookingWizardPage />} />
            <Route path="/buyurtmalarim" element={<MyAppointmentsPage />} />
          </Route>
        </>
      ) : (
        <>
          {/* Customer routes when not admin and not barber */}
          <Route element={<CustomerLayout isBarber={false} />}>
            <Route path="/booking" element={<BookingWizardPage />} />
            <Route path="/buyurtmalarim" element={<MyAppointmentsPage />} />
            <Route path="/admin" element={<ErrorState message={t('ADMIN_ACCESS_DENIED')} />} />
            <Route path="*" element={<BookingWizardPage />} />
          </Route>
        </>
      )}
    </Routes>
  )
}

export default App


