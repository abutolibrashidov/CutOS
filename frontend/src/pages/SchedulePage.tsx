import { useCallback, useEffect, useState } from 'react'

import { getSchedule, updateSchedule, type ScheduleDay } from '../api/client'
import { ErrorState, LoadingState, SuccessMessage } from '../components/Feedback'
import { t } from '../i18n/uz'
import { userError } from '../lib/errors'
import { dayName } from '../lib/format'

const defaultStart = '09:00:00'
const defaultEnd = '18:00:00'

function inputTime(value: string | null, fallback: string): string {
  return (value ?? fallback).slice(0, 5)
}

export function SchedulePage() {
  const [days, setDays] = useState<ScheduleDay[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setDays(await getSchedule()) } catch (loadError) { setError(userError(loadError)) } finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  function change(weekday: number, update: Partial<ScheduleDay>) {
    setDays((items) => items.map((item) => item.weekday === weekday ? { ...item, ...update } : item))
  }

  async function save() {
    for (const day of days) {
      const start = inputTime(day.start_time, defaultStart)
      const end = inputTime(day.end_time, defaultEnd)
      if (day.is_working && end <= start) { setError(t('SCHEDULE_TIME_INVALID')); return }
    }
    setSaving(true); setError(null); setSuccess(null)
    try {
      await updateSchedule(days.map((day) => ({
        weekday: day.weekday,
        start_time: inputTime(day.start_time, defaultStart),
        end_time: inputTime(day.end_time, defaultEnd),
        is_working: day.is_working,
      })))
      await load(); setSuccess(t('SCHEDULE_SAVED'))
    } catch (saveError) { setError(userError(saveError, 'save')) } finally { setSaving(false) }
  }

  if (loading) return <LoadingState />
  if (error && !days.length) return <ErrorState message={error} onRetry={() => void load()} />

  return <section>
    <p className="eyebrow">{t('NAV_SCHEDULE')}</p><h1>{t('SCHEDULE_TITLE')}</h1><p className="page-description">{t('SCHEDULE_DESCRIPTION')}</p>
    <SuccessMessage message={success} />
    {error && <p className="form-error" role="alert">{error}</p>}
    <div className="schedule-list">{days.map((day) => <article className="schedule-card" key={day.weekday}>
      <div className="schedule-top"><h2>{dayName(day.weekday)}</h2><label className="switch-label"><input type="checkbox" checked={day.is_working} onChange={(event) => change(day.weekday, { is_working: event.target.checked })} /><span>{day.is_working ? t('WORKING_DAY') : t('DAY_OFF')}</span></label></div>
      <div className="time-fields"><label>{t('START_TIME')}<input type="time" disabled={!day.is_working} value={inputTime(day.start_time, defaultStart)} onChange={(event) => change(day.weekday, { start_time: event.target.value })} /></label><label>{t('END_TIME')}<input type="time" disabled={!day.is_working} value={inputTime(day.end_time, defaultEnd)} onChange={(event) => change(day.weekday, { end_time: event.target.value })} /></label></div>
    </article>)}</div>
    <button className="button primary full-width" disabled={saving} onClick={() => void save()}>{saving ? t('LOADING') : t('SAVE')}</button>
  </section>
}
