import { Link } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'

import { getBlockedTimes, getProfile, getSchedule, getServices, type BarberProfile, type ScheduleDay } from '../api/client'
import { ErrorState, LoadingState } from '../components/Feedback'
import { dayName } from '../lib/format'
import { userError } from '../lib/errors'
import { t } from '../i18n/uz'

export function DashboardPage() {
  const [profile, setProfile] = useState<BarberProfile | null>(null)
  const [activeServices, setActiveServices] = useState(0)
  const [schedule, setSchedule] = useState<ScheduleDay[]>([])
  const [blockedCount, setBlockedCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [nextProfile, services, nextSchedule, blockedTimes] = await Promise.all([
        getProfile(), getServices(), getSchedule(), getBlockedTimes(),
      ])
      setProfile(nextProfile)
      setActiveServices(services.filter((service) => service.is_active).length)
      setSchedule(nextSchedule)
      setBlockedCount(blockedTimes.filter((item) => new Date(item.end_at) > new Date()).length)
    } catch (loadError) {
      setError(userError(loadError))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={() => void load()} />

  const workingDays = schedule.filter((day) => day.is_working)
  const scheduleSummary = workingDays.length
    ? workingDays.map((day) => dayName(day.weekday).slice(0, 3)).join(', ')
    : t('DASH_NOT_CONFIGURED')

  return (
    <section>
      <p className="eyebrow">{t('NAV_HOME')}</p>
      <h1>{t('DASH_WELCOME')}, {profile?.full_name}</h1>
      <div className="summary-grid">
        <article className="summary-card"><span>{t('DASH_ACTIVE_SERVICES')}</span><strong>{activeServices}</strong></article>
        <article className="summary-card"><span>{t('DASH_WORKING_DAYS')}</span><strong>{workingDays.length}</strong><small>{scheduleSummary}</small></article>
        <article className="summary-card"><span>{t('DASH_BLOCKED_PERIODS')}</span><strong>{blockedCount}</strong></article>
      </div>
      <div className="quick-links">
        <Link to="/xizmatlar">{t('NAV_SERVICES')} <span>{t('DASH_OPEN_SECTION')} →</span></Link>
        <Link to="/ish-vaqti">{t('NAV_SCHEDULE')} <span>{t('DASH_OPEN_SECTION')} →</span></Link>
        <Link to="/band-vaqtlar">{t('NAV_BLOCKED')} <span>{t('DASH_OPEN_SECTION')} →</span></Link>
        <Link to="/profil">{t('NAV_PROFILE')} <span>{t('DASH_OPEN_SECTION')} →</span></Link>
      </div>
    </section>
  )
}
