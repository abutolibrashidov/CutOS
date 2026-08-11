import { NavLink, Outlet, Route, Routes } from 'react-router-dom'

import { t } from './i18n/uz'
import { BlockedTimesPage } from './pages/BlockedTimesPage'
import { DashboardPage } from './pages/DashboardPage'
import { ProfilePage } from './pages/ProfilePage'
import { SchedulePage } from './pages/SchedulePage'
import { ServicesPage } from './pages/ServicesPage'

const navigation = [
  { to: '/', label: 'NAV_HOME', icon: '⌂' },
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

function App() {
  return (
    <Routes>
      <Route element={<WorkspaceLayout />}>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/xizmatlar" element={<ServicesPage />} />
        <Route path="/ish-vaqti" element={<SchedulePage />} />
        <Route path="/band-vaqtlar" element={<BlockedTimesPage />} />
        <Route path="/profil" element={<ProfilePage />} />
        <Route path="*" element={<DashboardPage />} />
      </Route>
    </Routes>
  )
}

export default App
