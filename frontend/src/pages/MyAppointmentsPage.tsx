import { useCallback, useEffect, useState } from 'react'
import { getMyAppointments, cancelMyAppointment, type AppointmentResponse } from '../api/customer'
import { ErrorState, LoadingState } from '../components/Feedback'
import { t } from '../i18n/uz'
import { userError } from '../lib/errors'
import { formatMoney, formatUtcClock, formatUtcDate } from '../lib/format'

export function MyAppointmentsPage() {
  const [appointments, setAppointments] = useState<AppointmentResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getMyAppointments()
      setAppointments(data)
    } catch (err: unknown) {
      setError(userError(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const handleCancel = async (id: string) => {
    if (!window.confirm(t('CANCEL_CONFIRM'))) return
    setActionError(null)
    setSuccessMessage(null)
    try {
      await cancelMyAppointment(id)
      setSuccessMessage(t('CANCEL_SUCCESS'))
      // Refresh list
      await load()
    } catch (err: unknown) {
      setActionError(userError(err))
    }
  }

  const isCancellable = (appointment: AppointmentResponse) => {
    if (appointment.status !== 'confirmed' && appointment.status !== 'pending') {
      return false
    }
    const start = new Date(appointment.start_at).getTime()
    const now = new Date().getTime()
    const diffMs = start - now
    // 60 minutes cutoff
    return diffMs > 60 * 60 * 1000
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
  if (error) return <ErrorState message={error} onRetry={() => void load()} />

  return (
    <section>
      <p className="eyebrow">{t('MY_BOOKINGS')}</p>
      <h1>{t('NAV_MY_BOOKINGS')}</h1>

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

      {appointments.length === 0 ? (
        <div className="empty-state">
          <p>{t('NO_BOOKINGS')}</p>
        </div>
      ) : (
        <div className="item-list">
          {appointments.map(appt => {
            const dateStr = formatUtcDate(appt.start_at)
            const timeStr = formatUtcClock(appt.start_at)

            return (
              <article key={appt.id} className="appointment-item">
                <header className="appointment-header">
                  <span>{dateStr} — {timeStr}</span>
                  <span className={getStatusClass(appt.status)}>{getStatusLabel(appt.status)}</span>
                </header>

                <ul className="appointment-services-list" style={{ listStyleType: 'none', margin: '0.25rem 0', padding: 0 }}>
                  {appt.barber_full_name && (
                    <li style={{ fontSize: '0.9rem' }}>{t('BARBER')}: {appt.barber_full_name}</li>
                  )}
                  {appt.appointment_services.map((s, idx) => (
                    <li key={idx} style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                      • {s.service_name_at_booking} ({s.duration_at_booking} min)
                    </li>
                  ))}
                </ul>

                <footer className="appointment-footer">
                  <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                    {t('TOTAL_PRICE')}: <strong>{formatMoney(appt.price_at_booking)}</strong>
                  </span>
                  
                  {isCancellable(appt) && (
                    <button
                      className="text-button danger"
                      onClick={() => void handleCancel(appt.id)}
                      style={{ padding: '0.25rem 0.5rem', fontWeight: 600 }}
                    >
                      {t('CANCEL_BOOKING')}
                    </button>
                  )}
                </footer>
              </article>
            )
          })}
        </div>
      )}
    </section>
  )
}
