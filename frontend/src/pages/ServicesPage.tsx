import { useCallback, useEffect, useState } from 'react'

import { createService, deleteService, getServices, updateService, type Service, type ServicePayload } from '../api/client'
import { ErrorState, LoadingState, SuccessMessage } from '../components/Feedback'
import { t } from '../i18n/uz'
import { userError } from '../lib/errors'
import { formatMoney } from '../lib/format'

const emptyForm: ServicePayload = { name: '', price_uzs: 0, duration_minutes: 30 }

export function ServicesPage() {
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [editing, setEditing] = useState<Service | null>(null)
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setServices(await getServices()) } catch (loadError) { setError(userError(loadError)) } finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  async function toggle(service: Service) {
    setError(null); setSuccess(null)
    try {
      const saved = await updateService(service.id, { is_active: !service.is_active })
      setServices((items) => items.map((item) => item.id === saved.id ? saved : item))
    } catch (saveError) { setError(userError(saveError, 'save')) }
  }

  async function remove(service: Service) {
    if (!window.confirm(t('SERVICE_DELETE_CONFIRM'))) return
    setError(null); setSuccess(null)
    try {
      await deleteService(service.id)
      setServices((items) => items.filter((item) => item.id !== service.id))
    } catch (deleteError) { setError(userError(deleteError, 'delete')) }
  }

  async function save(payload: ServicePayload) {
    setError(null); setSuccess(null)
    try {
      const saved = editing
        ? await updateService(editing.id, payload)
        : await createService(payload)
      setServices((items) => editing
        ? items.map((item) => item.id === saved.id ? saved : item)
        : [...items, saved].sort((first, second) => first.name.localeCompare(second.name, 'uz')))
      setShowForm(false); setEditing(null)
    } catch (saveError) { setError(userError(saveError, 'save')) }
  }

  if (loading) return <LoadingState />
  if (error && !services.length) return <ErrorState message={error} onRetry={() => void load()} />

  return (
    <section>
      <div className="page-heading"><div><p className="eyebrow">{t('NAV_SERVICES')}</p><h1>{t('SERVICES_TITLE')}</h1></div><button className="button primary" onClick={() => { setEditing(null); setShowForm(true) }}>{t('SERVICES_ADD')}</button></div>
      <SuccessMessage message={success} />
      {error && <p className="form-error" role="alert">{error}</p>}
      {showForm && <ServiceForm initial={editing ?? undefined} onSave={save} onCancel={() => { setShowForm(false); setEditing(null) }} />}
      {!services.length && !showForm ? <p className="empty-state">{t('SERVICES_EMPTY')}</p> : <div className="item-list">
        {services.map((service) => <article className="item-card" key={service.id}>
          <div><h2>{service.name}</h2><p>{formatMoney(service.price_uzs)} · {service.duration_minutes} {t('SERVICE_MINUTES')}</p></div>
          <span className={`status ${service.is_active ? 'active' : 'inactive'}`}>{service.is_active ? t('ACTIVE') : t('INACTIVE')}</span>
          <div className="item-actions"><button className="text-button" onClick={() => { setEditing(service); setShowForm(true) }}>{t('EDIT')}</button><button className="text-button" onClick={() => void toggle(service)}>{service.is_active ? t('DEACTIVATE') : t('ACTIVATE')}</button><button className="text-button danger" onClick={() => void remove(service)}>{t('DELETE')}</button></div>
        </article>)}
      </div>}
    </section>
  )
}

function ServiceForm({ initial, onSave, onCancel }: { initial?: Service; onSave: (payload: ServicePayload) => Promise<void>; onCancel: () => void }) {
  const [form, setForm] = useState<ServicePayload>(initial ? { name: initial.name, price_uzs: initial.price_uzs, duration_minutes: initial.duration_minutes } : emptyForm)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form.name.trim()) { setError(t('SERVICE_NAME_REQUIRED')); return }
    if (!Number.isInteger(form.price_uzs) || form.price_uzs < 0) { setError(t('SERVICE_PRICE_INVALID')); return }
    if (!Number.isInteger(form.duration_minutes) || form.duration_minutes <= 0) { setError(t('SERVICE_DURATION_INVALID')); return }
    setSaving(true); setError(null)
    try { await onSave({ ...form, name: form.name.trim() }) } catch { /* Parent supplies user feedback. */ } finally { setSaving(false) }
  }

  return <form className="form-card" onSubmit={submit}>
    <h2>{initial ? t('SERVICE_EDIT') : t('SERVICE_NEW')}</h2>
    {error && <p className="form-error" role="alert">{error}</p>}
    <label>{t('SERVICE_NAME')}<input value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} maxLength={255} required /></label>
    <label>{t('SERVICE_PRICE')} ({t('SERVICE_UZS')})<input value={form.price_uzs} onChange={(event) => setForm({ ...form, price_uzs: Number(event.target.value) })} type="number" inputMode="numeric" min="0" step="1" required /></label>
    <label>{t('SERVICE_DURATION')} ({t('SERVICE_MINUTES')})<input value={form.duration_minutes} onChange={(event) => setForm({ ...form, duration_minutes: Number(event.target.value) })} type="number" inputMode="numeric" min="1" step="1" required /></label>
    <div className="form-actions"><button className="button secondary" type="button" onClick={onCancel}>{t('CANCEL')}</button><button className="button primary" disabled={saving}>{saving ? t('LOADING') : t('SAVE')}</button></div>
  </form>
}
