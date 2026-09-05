import { useEffect, useState } from 'react'
import {
  type AdminBarber,
  type AdminBarberPayload,
  createAdminBarber,
  getAdminBarbers,
  toggleBarberActive,
  updateAdminBarber,
} from '../api/client'
import { ErrorState, LoadingState } from '../components/Feedback'
import { t } from '../i18n/uz'

interface LocationOption {
  id: string
  name: string
}

export function AdminDashboardPage() {
  const [barbers, setBarbers] = useState<AdminBarber[]>([])
  const [locations, setLocations] = useState<LocationOption[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)

  // Modal states
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingBarber, setEditingBarber] = useState<AdminBarber | null>(null)
  const [submitting, setSubmitting] = useState(false)

  // Form state
  const [formData, setFormData] = useState<{
    telegram_id: string
    full_name: string
    phone: string
    location_id: string
    bio: string
    avatar_url: string
    is_active: boolean
  }>({
    telegram_id: '',
    full_name: '',
    phone: '',
    location_id: '',
    bio: '',
    avatar_url: '',
    is_active: true,
  })

  async function fetchData() {
    try {
      setLoading(true)
      setError(null)
      const data = await getAdminBarbers()
      setBarbers(data)

      // Fetch customer locations for dropdown selection
      try {
        const locRes = await fetch('/api/v1/customer/locations/')
        if (locRes.ok) {
          const locs = await locRes.json()
          setLocations(locs)
        }
      } catch {
        // Ignored if locations endpoint fails
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || t('SERVER_ERROR'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void fetchData()
  }, [])

  function handleOpenAdd() {
    setEditingBarber(null)
    setActionError(null)
    setFormData({
      telegram_id: '',
      full_name: '',
      phone: '',
      location_id: locations[0]?.id || '',
      bio: '',
      avatar_url: '',
      is_active: true,
    })
    setIsModalOpen(true)
  }

  function handleOpenEdit(barber: AdminBarber) {
    setEditingBarber(barber)
    setActionError(null)
    setFormData({
      telegram_id: String(barber.telegram_id),
      full_name: barber.full_name,
      phone: barber.phone || '',
      location_id: barber.location_id || '',
      bio: barber.bio || '',
      avatar_url: barber.avatar_url || '',
      is_active: barber.is_active,
    })
    setIsModalOpen(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setActionError(null)
    setSubmitting(true)

    try {
      if (editingBarber) {
        const payload: Partial<AdminBarberPayload> = {
          full_name: formData.full_name,
          phone: formData.phone || null,
          location_id: formData.location_id || null,
          bio: formData.bio || null,
          avatar_url: formData.avatar_url || null,
          is_active: formData.is_active,
        }
        await updateAdminBarber(editingBarber.id, payload)
      } else {
        const payload: AdminBarberPayload = {
          telegram_id: Number(formData.telegram_id),
          full_name: formData.full_name,
          phone: formData.phone || null,
          location_id: formData.location_id || null,
          bio: formData.bio || null,
          avatar_url: formData.avatar_url || null,
          is_active: formData.is_active,
        }
        await createAdminBarber(payload)
      }

      setIsModalOpen(false)
      await fetchData()
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || t('SAVE_ERROR'))
    } finally {
      setSubmitting(false)
    }
  }

  async function handleToggleActive(barber: AdminBarber) {
    try {
      setActionError(null)
      await toggleBarberActive(barber.id, !barber.is_active)
      await fetchData()
    } catch (err: any) {
      setActionError(err?.response?.data?.detail || t('SAVE_ERROR'))
    }
  }

  if (loading) return <LoadingState />
  if (error) return <ErrorState message={error} onRetry={fetchData} />

  return (
    <div className="admin-dashboard-container" style={{ padding: '1rem', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, margin: 0 }}>{t('ADMIN_TITLE')}</h1>
          <p style={{ color: 'var(--text-muted, #8e8e93)', margin: '0.25rem 0 0 0', fontSize: '0.9rem' }}>
            {t('ADMIN_BARBERS')}
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="btn-primary"
          style={{
            padding: '0.6rem 1.2rem',
            borderRadius: '8px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          + {t('ADMIN_ADD_BARBER')}
        </button>
      </div>

      {actionError && (
        <div style={{ padding: '0.75rem 1rem', borderRadius: '8px', backgroundColor: '#ffe5e5', color: '#cc0000', marginBottom: '1rem' }}>
          {actionError}
        </div>
      )}

      {barbers.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem 1rem', color: 'var(--text-muted, #8e8e93)' }}>
          <p>{t('ADMIN_NO_BARBERS')}</p>
        </div>
      ) : (
        <div className="table-responsive" style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-color, #e5e5ea)' }}>
                <th style={{ padding: '0.75rem 0.5rem' }}>{t('ADMIN_FULL_NAME')}</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>{t('ADMIN_TELEGRAM_ID')}</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>{t('ADMIN_LOCATION')}</th>
                <th style={{ padding: '0.75rem 0.5rem' }}>{t('ADMIN_STATUS')}</th>
                <th style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>Amallar</th>
              </tr>
            </thead>
            <tbody>
              {barbers.map((b) => (
                <tr key={b.id} style={{ borderBottom: '1px solid var(--border-color, #f2f2f7)' }}>
                  <td style={{ padding: '0.75rem 0.5rem', fontWeight: 600 }}>
                    {b.full_name}
                    {b.phone && <div style={{ fontSize: '0.8rem', color: 'var(--text-muted, #8e8e93)', fontWeight: 400 }}>{b.phone}</div>}
                  </td>
                  <td style={{ padding: '0.75rem 0.5rem', fontFamily: 'monospace' }}>{b.telegram_id}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>{b.location_name || '—'}</td>
                  <td style={{ padding: '0.75rem 0.5rem' }}>
                    <span
                      style={{
                        padding: '0.25rem 0.5rem',
                        borderRadius: '4px',
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        backgroundColor: b.is_active ? '#e6f9e6' : '#ffe5e5',
                        color: b.is_active ? '#008000' : '#cc0000',
                      }}
                    >
                      {b.is_active ? t('ADMIN_ACTIVE') : t('ADMIN_INACTIVE')}
                    </span>
                  </td>
                  <td style={{ padding: '0.75rem 0.5rem', textAlign: 'right' }}>
                    <button
                      onClick={() => handleOpenEdit(b)}
                      style={{
                        marginRight: '0.5rem',
                        padding: '0.35rem 0.75rem',
                        borderRadius: '6px',
                        border: '1px solid #ccc',
                        background: 'transparent',
                        cursor: 'pointer',
                      }}
                    >
                      {t('EDIT')}
                    </button>
                    <button
                      onClick={() => void handleToggleActive(b)}
                      style={{
                        padding: '0.35rem 0.75rem',
                        borderRadius: '6px',
                        border: 'none',
                        backgroundColor: b.is_active ? '#ff3b30' : '#34c759',
                        color: '#fff',
                        cursor: 'pointer',
                      }}
                    >
                      {b.is_active ? t('ADMIN_DEACTIVATE') : t('ADMIN_ACTIVATE')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Add / Edit Barber Modal */}
      {isModalOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 1000,
            padding: '1rem',
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--bg-card, #ffffff)',
              color: 'var(--text-color, #000000)',
              borderRadius: '12px',
              padding: '1.5rem',
              maxWidth: '500px',
              width: '100%',
              boxShadow: '0 10px 25px rgba(0,0,0,0.2)',
            }}
          >
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, marginTop: 0 }}>
              {editingBarber ? t('ADMIN_EDIT_BARBER') : t('ADMIN_ADD_BARBER')}
            </h2>

            <form onSubmit={(e) => void handleSubmit(e)}>
              {!editingBarber && (
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                    {t('ADMIN_TELEGRAM_ID')} *
                  </label>
                  <input
                    type="number"
                    required
                    placeholder="Masalan, 123456789"
                    value={formData.telegram_id}
                    onChange={(e) => setFormData({ ...formData, telegram_id: e.target.value })}
                    style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid #ccc' }}
                  />
                </div>
              )}

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {t('ADMIN_FULL_NAME')} *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Masalan, Sherzod Aliyev"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid #ccc' }}
                />
              </div>

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {t('ADMIN_PHONE')}
                </label>
                <input
                  type="text"
                  placeholder="+998901234567"
                  value={formData.phone}
                  onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid #ccc' }}
                />
              </div>

              {locations.length > 0 && (
                <div style={{ marginBottom: '1rem' }}>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                    {t('ADMIN_LOCATION')}
                  </label>
                  <select
                    value={formData.location_id}
                    onChange={(e) => setFormData({ ...formData, location_id: e.target.value })}
                    style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid #ccc' }}
                  >
                    <option value="">— Tanlanmagan —</option>
                    {locations.map((loc) => (
                      <option key={loc.id} value={loc.id}>
                        {loc.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.25rem' }}>
                  {t('PROFILE_BIO')}
                </label>
                <textarea
                  rows={2}
                  value={formData.bio}
                  onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
                  style={{ width: '100%', padding: '0.6rem', borderRadius: '6px', border: '1px solid #ccc' }}
                />
              </div>

              <div style={{ marginBottom: '1.5rem', display: 'flex', alignItems: 'center' }}>
                <input
                  type="checkbox"
                  id="is_active_check"
                  checked={formData.is_active}
                  onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  style={{ marginRight: '0.5rem' }}
                />
                <label htmlFor="is_active_check" style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                  {t('ADMIN_ACTIVE')}
                </label>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.5rem' }}>
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  style={{
                    padding: '0.6rem 1.2rem',
                    borderRadius: '6px',
                    border: '1px solid #ccc',
                    background: 'transparent',
                    cursor: 'pointer',
                  }}
                >
                  {t('CANCEL')}
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="btn-primary"
                  style={{
                    padding: '0.6rem 1.2rem',
                    borderRadius: '6px',
                    fontWeight: 600,
                    cursor: submitting ? 'wait' : 'pointer',
                  }}
                >
                  {t('SAVE')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
