import { useCallback, useEffect, useState } from 'react'
import {
  getBarberAppointments,
  cancelBarberAppointment,
  createWalkIn,
  getServices,
  type BarberAppointmentResponse,
  type Service,
} from '../api/client'
import { ErrorState, LoadingState } from '../components/Feedback'
import { t } from '../i18n/uz'
import { userError } from '../lib/errors'
import { formatMoney, formatUtcClock, formatUtcDate, localDateTimeInputToUtcIso } from '../lib/format'

type Tab = 'list' | 'walk-in'

export function BarberAppointmentsPage() {
  const [tab, setTab] = useState<Tab>('list')
  const [appointments, setAppointments] = useState<BarberAppointmentResponse[]>([])
  const [services, setServices] = useState<Service[]>([])
  
  // Walk-in form state
  const [walkInName, setWalkInName] = useState('')
  const [walkInPhone, setWalkInPhone] = useState('')
  const [selectedServiceIds, setSelectedServiceIds] = useState<string[]>([])
  const [walkInDateTime, setWalkInDateTime] = useState('') // YYYY-MM-DDTHH:MM

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [appts, svcs] = await Promise.all([
        getBarberAppointments(),
        getServices(),
      ])
      setAppointments(appts)
      setServices(svcs.filter(s => s.is_active))
    } catch (err: unknown) {
      setError(userError(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadData()
  }, [loadData])

  const handleCancel = async (id: string) => {
    if (!window.confirm(t('CANCEL_CONFIRM'))) return
    setActionError(null)
    setSuccessMessage(null)
    try {
      await cancelBarberAppointment(id)
      setSuccessMessage(t('CANCEL_SUCCESS'))
      await loadData()
    } catch (err: unknown) {
      setActionError(userError(err))
    }
  }

  const handleToggleService = (id: string) => {
    setSelectedServiceIds(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    )
  }

  const handleWalkInSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setActionError(null)
    setSuccessMessage(null)

    if (!walkInName.trim()) {
      setActionError(t('PROFILE_NAME_REQUIRED'))
      return
    }
    if (selectedServiceIds.length === 0) {
      setActionError(t('SELECT_SERVICES'))
      return
    }
    if (!walkInDateTime) {
      setActionError(t('SCHEDULE_TIME_INVALID'))
      return
    }

    try {
      await createWalkIn({
        full_name: walkInName,
        phone: walkInPhone.trim() || null,
        service_ids: selectedServiceIds,
        start_at: localDateTimeInputToUtcIso(walkInDateTime),
      })

      setSuccessMessage(t('WALKIN_SUCCESS'))
      // Reset form
      setWalkInName('')
      setWalkInPhone('')
      setSelectedServiceIds([])
      setWalkInDateTime('')
      setTab('list')
      await loadData()
    } catch (err: unknown) {
      setActionError(userError(err, 'save'))
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'confirmed': return t('STATUS_CONFIRMED')
      case 'pending': return t('STATUS_PENDING')
      case 'completed': return t('STATUS_COMPLETED')
      case 'cancelled': return t('STATUS_CANCELLED')
      case 'no_show': return t('STATUS_NO_SHOW')
      default: return status
    }
  }

  const getStatusClass = (status: string) => {
    switch (status) {
      case 'confirmed':
      case 'completed':
        return 'status active'
      case 'cancelled':
      case 'no_show':
        return 'status inactive'
      default:
        return 'status'
    }
  }

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={() => void loadData()} />

  return (
    <section>
      <p className="eyebrow">{t('APP_NAME')}</p>
      
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem' }}>
        <button
          className={`button ${tab === 'list' ? 'primary' : 'secondary'}`}
          onClick={() => { setTab('list'); setActionError(null); setSuccessMessage(null); }}
          style={{ flex: 1 }}
        >
          {t('NAV_APPOINTMENTS')}
        </button>
        <button
          className={`button ${tab === 'walk-in' ? 'primary' : 'secondary'}`}
          onClick={() => { setTab('walk-in'); setActionError(null); setSuccessMessage(null); }}
          style={{ flex: 1 }}
        >
          {t('WALKIN_TAB')}
        </button>
      </div>

      {successMessage && (
        <p className="success-message" role="status" style={{ marginBottom: '1rem' }}>
          {successMessage}
        </p>
      )}

      {actionError && (
        <div style={{ color: 'var(--danger)', marginBottom: '1rem', fontSize: '0.9rem' }}>
          {actionError}
        </div>
      )}

      {/* TAB 1: BUYURTMALAR RO'YHATI */}
      {tab === 'list' && (
        appointments.length === 0 ? (
          <div className="empty-state">
            <p>{t('WALKIN_EMPTY')}</p>
          </div>
        ) : (
          <div className="item-list">
            {appointments.map(appt => {
              const dateStr = formatUtcDate(appt.start_at)
              const timeStr = formatUtcClock(appt.start_at)
              const customerName = appt.customer_full_name || t('CUSTOMER')
              const sourceLabel = appt.source === 'walkin' ? t('SOURCE_WALKIN') : t('SOURCE_ONLINE')

              return (
                <article key={appt.id} className="appointment-item">
                  <header className="appointment-header">
                    <span>{dateStr} — {timeStr}</span>
                    <span className={getStatusClass(appt.status)}>{getStatusLabel(appt.status)}</span>
                  </header>

                  <div style={{ margin: '0.25rem 0' }}>
                    <p style={{ fontWeight: 500, margin: 0, fontSize: '0.95rem' }}>
                      {t('CUSTOMER')}: {customerName} ({t('SOURCE')}: {sourceLabel})
                    </p>
                    <ul style={{ listStyleType: 'none', margin: '0.25rem 0', padding: 0 }}>
                      {appt.appointment_services.map((s, idx) => (
                        <li key={idx} style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          • {s.service_name_at_booking} ({s.duration_at_booking} min) — {formatMoney(s.price_at_booking)}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <footer className="appointment-footer">
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                      {t('TOTAL_PRICE')}: <strong>{formatMoney(appt.price_at_booking)}</strong>
                    </span>
                    
                    {appt.status !== 'cancelled' && appt.status !== 'completed' && (
                      <button
                        className="text-button danger"
                        onClick={() => void handleCancel(appt.id)}
                        style={{ padding: '0.25rem 0.65rem', fontWeight: 600, fontSize: '0.85rem' }}
                      >
                        {t('CANCEL_BOOKING')}
                      </button>
                    )}
                  </footer>
                </article>
              )
            })}
          </div>
        )
      )}

      {/* TAB 2: WALK-IN QO'SHISH */}
      {tab === 'walk-in' && (
        <form onSubmit={handleWalkInSubmit} className="form-card">
          <h2>{t('WALKIN_TITLE')}</h2>
          
          <label>
            {t('WALKIN_NAME')} *
            <input
              type="text"
              required
              value={walkInName}
              onChange={e => setWalkInName(e.target.value)}
              placeholder={t('WALKIN_NAME_PLACEHOLDER')}
            />
          </label>

          <label>
            {t('WALKIN_PHONE')}
            <input
              type="text"
              value={walkInPhone}
              onChange={e => setWalkInPhone(e.target.value)}
              placeholder={t('WALKIN_PHONE_PLACEHOLDER')}
            />
          </label>

          <label>
            {t('WALKIN_START')} *
            <input
              type="datetime-local"
              required
              value={walkInDateTime}
              onChange={e => setWalkInDateTime(e.target.value)}
            />
          </label>

          <div>
            <span style={{ fontWeight: 500, fontSize: '0.875rem', display: 'block', marginBottom: '0.5rem' }}>
              {t('SELECT_SERVICES')} *
            </span>
            <div className="selection-grid" style={{ gap: '0.5rem' }}>
              {services.map(s => {
                const isSelected = selectedServiceIds.includes(s.id)
                return (
                  <div
                    key={s.id}
                    className={`service-selection-item${isSelected ? ' selected' : ''}`}
                    onClick={() => handleToggleService(s.id)}
                    style={{ padding: '0.75rem' }}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      readOnly
                    />
                    <div style={{ marginLeft: '0.5rem' }}>
                      <strong style={{ fontSize: '0.9rem' }}>{s.name}</strong>
                      <span style={{ display: 'block', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                        {formatMoney(s.price_uzs)} • {s.duration_minutes} min
                      </span>
                    </div>
                  </div>
                )
              })}
            </div>
          </div>

          <div style={{ marginTop: '1rem' }}>
            <button type="submit" className="button primary full-width">
              {t('WALKIN_SUBMIT')}
            </button>
          </div>
        </form>
      )}
    </section>
  )
}
