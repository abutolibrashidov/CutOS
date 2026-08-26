import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  getLocations,
  getBarbers,
  getBarberServices,
  getAvailableSlots,
  createBooking,
  type LocationPublic,
  type BarberPublic,
  type ServicePublic,
  type BookingResponse,
} from '../api/customer'
import { ErrorState, LoadingState } from '../components/Feedback'
import { t } from '../i18n/uz'
import { userError } from '../lib/errors'
import { formatMoney, formatUtcClock, formatUtcDate } from '../lib/format'

type Step = 'location' | 'barber' | 'services' | 'date' | 'time' | 'review' | 'confirm'

export function BookingWizardPage() {
  const [step, setStep] = useState<Step>('location')
  
  // Selection state
  const [locations, setLocations] = useState<LocationPublic[]>([])
  const [selectedLocation, setSelectedLocation] = useState<LocationPublic | null>(null)
  
  const [barbers, setBarbers] = useState<BarberPublic[]>([])
  const [selectedBarber, setSelectedBarber] = useState<BarberPublic | null>(null) // null represents "Any Barber"
  const [isAnyBarber, setIsAnyBarber] = useState(false)
  
  const [services, setServices] = useState<ServicePublic[]>([])
  const [selectedServices, setSelectedServices] = useState<ServicePublic[]>([])
  
  const [selectedDate, setSelectedDate] = useState<string | null>(null) // YYYY-MM-DD
  const [slots, setSlots] = useState<string[]>([])
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null) // UTC ISO
  
  const [bookingResult, setBookingResult] = useState<BookingResponse | null>(null)

  // Loading & error states
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 1. Fetch locations on load
  const loadLocations = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const locs = await getLocations()
      setLocations(locs)
      if (locs.length === 1) {
        setSelectedLocation(locs[0])
        setStep('barber')
      }
    } catch (err: unknown) {
      setError(userError(err))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadLocations()
  }, [loadLocations])

  // 2. Fetch barbers when location is selected
  useEffect(() => {
    if (!selectedLocation) return
    const fetchBarbersList = async () => {
      setLoading(true)
      setError(null)
      try {
        const barbs = await getBarbers(selectedLocation.id)
        setBarbers(barbs)
      } catch (err: unknown) {
        setError(userError(err))
      } finally {
        setLoading(false)
      }
    }
    void fetchBarbersList()
  }, [selectedLocation])

  // 3. Fetch services
  const loadServices = useCallback(async () => {
    if (!selectedLocation) return
    setLoading(true)
    setError(null)
    try {
      if (selectedBarber) {
        // Specific barber services
        const svcs = await getBarberServices(selectedBarber.id)
        setServices(svcs)
      } else {
        // Any barber: load and merge unique service names from all active barbers
        const allServices = await Promise.all(
          barbers.map(b => getBarberServices(b.id).catch(() => []))
        )
        const merged: ServicePublic[] = []
        const seen = new Set<string>()
        allServices.flat().forEach(s => {
          const nameKey = s.name.trim().toLowerCase()
          if (!seen.has(nameKey)) {
            seen.add(nameKey)
            merged.push(s)
          }
        })
        setServices(merged)
      }
    } catch (err: unknown) {
      setError(userError(err))
    } finally {
      setLoading(false)
    }
  }, [selectedBarber, selectedLocation, barbers])

  useEffect(() => {
    if (step === 'services') {
      void loadServices()
    }
  }, [step, loadServices])

  // 4. Fetch available slots
  const loadSlots = useCallback(async () => {
    if (!selectedLocation || !selectedDate || selectedServices.length === 0) return
    setLoading(true)
    setError(null)
    try {
      const serviceIds = selectedServices.map(s => s.id)
      if (selectedBarber) {
        const res = await getAvailableSlots(selectedBarber.id, serviceIds, selectedDate)
        setSlots(res.slots)
      } else {
        // Any barber: fetch slots for all barbers who support these services, then take the union
        const slotsPromises = barbers.map(async b => {
          // Find matching services for this barber by name
          const bSvcs = await getBarberServices(b.id).catch(() => [])
          const bMatchingIds: string[] = []
          for (const s of selectedServices) {
            const match = bSvcs.find(bs => bs.name.trim().toLowerCase() === s.name.trim().toLowerCase())
            if (match) bMatchingIds.push(match.id)
          }
          if (bMatchingIds.length === selectedServices.length) {
            const res = await getAvailableSlots(b.id, bMatchingIds, selectedDate).catch(() => ({ slots: [] }))
            return res.slots
          }
          return []
        })
        const allSlots = await Promise.all(slotsPromises)
        const unionSlots = Array.from(new Set(allSlots.flat())).sort()
        setSlots(unionSlots)
      }
    } catch (err: unknown) {
      setError(userError(err))
    } finally {
      setLoading(false)
    }
  }, [selectedLocation, selectedBarber, selectedServices, selectedDate, barbers])

  useEffect(() => {
    if (step === 'time' && selectedDate) {
      void loadSlots()
    }
  }, [step, selectedDate, loadSlots])

  // Helpers
  const handleSelectLocation = (loc: LocationPublic) => {
    setSelectedLocation(loc)
    setStep('barber')
  }

  const handleSelectBarber = (barber: BarberPublic | null) => {
    setSelectedBarber(barber)
    setIsAnyBarber(barber === null)
    setSelectedServices([])
    setStep('services')
  }

  const handleToggleService = (service: ServicePublic) => {
    setSelectedServices(prev => {
      const exists = prev.some(s => s.id === service.id)
      if (exists) {
        return prev.filter(s => s.id !== service.id)
      } else {
        return [...prev, service]
      }
    })
  }

  const handleConfirmServices = () => {
    if (selectedServices.length === 0) return
    setSelectedDate(null)
    setSelectedSlot(null)
    setStep('date')
  }

  const handleSelectDate = (dateStr: string) => {
    setSelectedDate(dateStr)
    setSelectedSlot(null)
    setStep('time')
  }

  const handleSelectSlot = (slotStr: string) => {
    setSelectedSlot(slotStr)
    setStep('review')
  }

  const handleBook = async () => {
    if (!selectedLocation || selectedServices.length === 0 || !selectedSlot) return
    setLoading(true)
    setError(null)
    try {
      const res = await createBooking({
        location_id: selectedLocation.id,
        barber_id: isAnyBarber ? null : selectedBarber?.id || null,
        service_ids: selectedServices.map(s => s.id),
        start_at: selectedSlot,
      })
      setBookingResult(res)
      setStep('confirm')
    } catch (err: unknown) {
      setError(userError(err))
    } finally {
      setLoading(false)
    }
  }

  // Get next 7 days for date selector
  const getDateOptions = () => {
    const dates = []
    const now = new Date()
    for (let i = 0; i < 7; i++) {
      const d = new Date()
      d.setDate(now.getDate() + i)
      const year = d.getFullYear()
      const month = String(d.getMonth() + 1).padStart(2, '0')
      const day = String(d.getDate()).padStart(2, '0')
      const dateStr = `${year}-${month}-${day}`
      const weekdayIndex = d.getDay()
      // format weekday index from standard (0=Sun, 6=Sat) to model's index (0=Mon, 6=Sun)
      const weekdayModel = weekdayIndex === 0 ? 6 : weekdayIndex - 1
      dates.push({
        dateStr,
        dayNum: d.getDate(),
        weekdayLabel: t(`DAY_${weekdayModel}` as any).slice(0, 3),
      })
    }
    return dates
  }

  const totalDuration = selectedServices.reduce((sum, s) => sum + s.duration_minutes, 0)
  const totalPrice = selectedServices.reduce((sum, s) => sum + s.price_uzs, 0)

  if (loading && step === 'location') return <LoadingState />
  if (error && step === 'location') return <ErrorState message={error} onRetry={() => void loadLocations()} />

  return (
    <section className="booking-section">
      <div className="page-heading">
        <p className="eyebrow">{t('BOOK_NOW')}</p>
        {step !== 'location' && step !== 'confirm' && (
          <span className="step-indicator">
            {step === 'barber' && '1/5'}
            {step === 'services' && '2/5'}
            {step === 'date' && '3/5'}
            {step === 'time' && '4/5'}
            {step === 'review' && '5/5'}
          </span>
        )}
      </div>

      {error && step !== 'location' && (
        <div style={{ color: 'var(--danger)', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>
      )}

      {/* STEP 1: LOCATIONS */}
      {step === 'location' && (
        <>
          <h1>{t('SELECT_LOCATION')}</h1>
          <div className="selection-grid">
            {locations.map(loc => (
              <button
                key={loc.id}
                className="selectable-card"
                onClick={() => handleSelectLocation(loc)}
              >
                <strong style={{ fontSize: '1.1rem' }}>{loc.name}</strong>
                {loc.address && <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{loc.address}</span>}
              </button>
            ))}
          </div>
        </>
      )}

      {/* STEP 2: BARBERS */}
      {step === 'barber' && (
        <>
          <h1>{t('SELECT_BARBER')}</h1>
          <div className="selection-grid">
            <button
              className="selectable-card selected"
              onClick={() => handleSelectBarber(null)}
              style={{ borderLeft: '4px solid var(--primary)' }}
            >
              <strong style={{ color: 'var(--primary)' }}>{t('ANY_BARBER')}</strong>
              <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                {t('ANY_BARBER_HINT')}
              </span>
            </button>

            {barbers.map(b => (
              <button
                key={b.id}
                className="selectable-card"
                onClick={() => handleSelectBarber(b)}
              >
                <strong>{b.full_name}</strong>
                {b.bio && <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>{b.bio}</span>}
              </button>
            ))}
          </div>
          <div className="wizard-actions">
            <button className="button secondary" onClick={() => setStep('location')}>{t('BACK')}</button>
          </div>
        </>
      )}

      {/* STEP 3: SERVICES */}
      {step === 'services' && (
        <>
          <h1>{t('SELECT_SERVICES')}</h1>
          {loading ? (
            <LoadingState />
          ) : (
            <div className="selection-grid">
              {services.map(s => {
                const isSelected = selectedServices.some(item => item.name === s.name)
                return (
                  <div
                    key={s.id}
                    className={`service-selection-item${isSelected ? ' selected' : ''}`}
                    onClick={() => handleToggleService(s)}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      readOnly
                    />
                    <div className="service-info">
                      <strong>{s.name}</strong>
                      <div className="service-meta">
                        <span>{formatMoney(s.price_uzs)}</span>
                        <span>{s.duration_minutes} {t('SERVICE_MINUTES')}</span>
                      </div>
                    </div>
                  </div>
                )
              })}
            </div>
          )}

          {selectedServices.length > 0 && (
            <div className="item-card" style={{ marginTop: '1rem', backgroundColor: 'rgba(29, 78, 216, 0.02)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                <span>{t('TOTAL_DURATION')}:</span>
                <strong>{totalDuration} {t('SERVICE_MINUTES')}</strong>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>{t('TOTAL_PRICE')}:</span>
                <strong>{formatMoney(totalPrice)}</strong>
              </div>
            </div>
          )}


          <div className="wizard-actions">
            <button className="button secondary" onClick={() => setStep('barber')}>{t('BACK')}</button>
            <button
              className="button primary"
              disabled={selectedServices.length === 0}
              onClick={handleConfirmServices}
            >
              {t('CONTINUE')}
            </button>
          </div>
        </>
      )}

      {/* STEP 4: DATE */}
      {step === 'date' && (
        <>
          <h1>{t('SELECT_DATE')}</h1>
          <div className="date-selector-grid">
            {getDateOptions().map(opt => (
              <button
                key={opt.dateStr}
                className={`date-card${selectedDate === opt.dateStr ? ' selected' : ''}`}
                onClick={() => handleSelectDate(opt.dateStr)}
              >
                <span className="weekday">{opt.weekdayLabel}</span>
                <span className="day">{opt.dayNum}</span>
              </button>
            ))}
          </div>
          <div className="wizard-actions">
            <button className="button secondary" onClick={() => setStep('services')}>{t('BACK')}</button>
          </div>
        </>
      )}

      {/* STEP 5: TIME */}
      {step === 'time' && (
        <>
          <h1>{t('SELECT_TIME')}</h1>
          {loading ? (
            <LoadingState />
          ) : slots.length === 0 ? (
            <div className="empty-state">
              <p>{t('NO_SLOTS')}</p>
            </div>
          ) : (
            <div className="slot-selection-grid">
              {slots.map(slot => {
                return (
                  <button
                    key={slot}
                    className={`slot-card${selectedSlot === slot ? ' selected' : ''}`}
                    onClick={() => handleSelectSlot(slot)}
                  >
                    {formatUtcClock(slot)}
                  </button>
                )
              })}
            </div>
          )}
          <div className="wizard-actions">
            <button className="button secondary" onClick={() => setStep('date')}>{t('BACK')}</button>
          </div>
        </>
      )}

      {/* STEP 6: REVIEW */}
      {step === 'review' && (
        <>
          <h1>{t('REVIEW_BOOKING')}</h1>
          <div className="checkout-review">
            <div className="review-item">
              <span className="review-label">{t('BARBER')}</span>
              <strong className="review-value">
                {isAnyBarber ? t('ANY_BARBER') : selectedBarber?.full_name}
              </strong>
            </div>
            <div className="review-item" style={{ flexDirection: 'column', gap: '0.25rem', alignItems: 'flex-start' }}>
              <span className="review-label">{t('SERVICES')}</span>
              <div style={{ width: '100%' }}>
                {selectedServices.map(s => (
                  <div key={s.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem' }}>
                    <span>• {s.name}</span>
                    <span>{formatMoney(s.price_uzs)}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="review-item">
              <span className="review-label">{t('DATE')}</span>
              <strong className="review-value">{selectedDate}</strong>
            </div>
            <div className="review-item">
              <span className="review-label">{t('TIME')}</span>
              <strong className="review-value">
                {selectedSlot ? formatUtcClock(selectedSlot) : ''}
              </strong>
            </div>
            <div className="review-item" style={{ borderTop: '1px solid var(--border)', paddingTop: '0.75rem', marginTop: '0.25rem' }}>
              <span className="review-label" style={{ color: 'var(--text)', fontWeight: 600 }}>{t('TOTAL_PRICE')}</span>
              <strong className="review-value" style={{ color: 'var(--primary)', fontSize: '1.2rem' }}>
                {formatMoney(totalPrice)}
              </strong>
            </div>
          </div>

          <div className="wizard-actions">
            <button className="button secondary" onClick={() => setStep('time')} disabled={loading}>
              {t('BACK')}
            </button>
            <button className="button primary" onClick={() => void handleBook()} disabled={loading}>
              {loading ? t('LOADING') : t('CONFIRM_BOOKING')}
            </button>
          </div>
        </>
      )}

      {/* STEP 7: CONFIRMATION SUCCESS */}
      {step === 'confirm' && bookingResult && (
        <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
          <div style={{ fontSize: '4rem', color: 'var(--success)', marginBottom: '1rem' }}>✓</div>
          <h1>{t('BOOKING_SUCCESS')}</h1>
          
          <div className="checkout-review" style={{ marginTop: '1.5rem', textAlign: 'left' }}>
            <div className="review-item">
              <span className="review-label">{t('BOOKING_ID')}</span>
              <code style={{ fontSize: '0.85rem' }}>{bookingResult.appointment.id}</code>
            </div>
            <div className="review-item">
              <span className="review-label">{t('BARBER')}</span>
              <strong className="review-value">{bookingResult.barber.full_name}</strong>
            </div>
            <div className="review-item">
              <span className="review-label">{t('DATE')}</span>
              <strong className="review-value">
                {formatUtcDate(bookingResult.appointment.start_at)}
              </strong>
            </div>
            <div className="review-item">
              <span className="review-label">{t('TIME')}</span>
              <strong className="review-value">
                {formatUtcClock(bookingResult.appointment.start_at)}
              </strong>
            </div>
            <div className="review-item">
              <span className="review-label">{t('TOTAL_PRICE')}</span>
              <strong className="review-value" style={{ color: 'var(--primary)' }}>
                {formatMoney(bookingResult.total_price_uzs)}
              </strong>
            </div>
          </div>


          <div style={{ marginTop: '2rem' }}>
            <Link to="/buyurtmalarim" className="button primary full-width">
              {t('NAV_MY_BOOKINGS')}
            </Link>
          </div>
        </div>
      )}
    </section>
  )
}
