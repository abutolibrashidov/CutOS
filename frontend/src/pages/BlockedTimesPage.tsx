import { useCallback, useEffect, useState } from 'react'

import { createBlockedTime, deleteBlockedTime, getBlockedTimes, updateBlockedTime, type BlockedTime, type BlockedTimePayload } from '../api/client'
import { ErrorState, LoadingState, SuccessMessage } from '../components/Feedback'
import { t } from '../i18n/uz'
import { userError } from '../lib/errors'
import { formatDateTime, toDateTimeLocal } from '../lib/format'

const emptyForm: BlockedTimePayload = { start_at: '', end_at: '', reason: null }

export function BlockedTimesPage() {
  const [blockedTimes, setBlockedTimes] = useState<BlockedTime[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)
  const [editing, setEditing] = useState<BlockedTime | null>(null)
  const [showForm, setShowForm] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setBlockedTimes(await getBlockedTimes()) } catch (loadError) { setError(userError(loadError)) } finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  async function remove(blockedTime: BlockedTime) {
    if (!window.confirm(t('BLOCKED_DELETE_CONFIRM'))) return
    setError(null); setSuccess(null)
    try {
      await deleteBlockedTime(blockedTime.id)
      setBlockedTimes((items) => items.filter((item) => item.id !== blockedTime.id))
    } catch (deleteError) { setError(userError(deleteError, 'delete')) }
  }

  async function save(payload: BlockedTimePayload) {
    setError(null); setSuccess(null)
    try {
      const saved = editing
        ? await updateBlockedTime(editing.id, payload)
        : await createBlockedTime(payload)
      setBlockedTimes((items) => (editing
        ? items.map((item) => (item.id === saved.id ? saved : item))
        : [...items, saved]
      ).sort((first, second) => first.start_at.localeCompare(second.start_at)))
      setShowForm(false); setEditing(null)
    } catch (saveError) { setError(userError(saveError, 'save')) }
  }

  if (loading) return <LoadingState />
  if (error && !blockedTimes.length) return <ErrorState message={error} onRetry={() => void load()} />

  return (
    <section>
      <div className="page-heading"><div><p className="eyebrow">{t('NAV_BLOCKED')}</p><h1>{t('BLOCKED_TITLE')}</h1></div><button className="button primary" onClick={() => { setEditing(null); setShowForm(true) }}>{t('BLOCKED_ADD')}</button></div>
      <SuccessMessage message={success} />
      {error && <p className="form-error" role="alert">{error}</p>}
      {showForm && <BlockedTimeForm initial={editing ?? undefined} onSave={save} onCancel={() => { setShowForm(false); setEditing(null) }} />}
      {!blockedTimes.length && !showForm ? <p className="empty-state">{t('BLOCKED_EMPTY')}</p> : <div className="item-list">
        {blockedTimes.map((blockedTime) => <article className="item-card" key={blockedTime.id}>
          <div><h2>{blockedTime.reason ?? t('BLOCKED_REASON_OPTIONAL')}</h2><p>{formatDateTime(blockedTime.start_at)} – {formatDateTime(blockedTime.end_at)}</p></div>
          <div className="item-actions"><button className="text-button" onClick={() => { setEditing(blockedTime); setShowForm(true) }}>{t('EDIT')}</button><button className="text-button danger" onClick={() => void remove(blockedTime)}>{t('DELETE')}</button></div>
        </article>)}
      </div>}
    </section>
  )
}

function BlockedTimeForm({ initial, onSave, onCancel }: { initial?: BlockedTime; onSave: (payload: BlockedTimePayload) => Promise<void>; onCancel: () => void }) {
  // start_at/end_at are kept in <input type="datetime-local"> format (no timezone)
  // while the form is open; they are only converted to ISO/UTC on submit.
  const [form, setForm] = useState<BlockedTimePayload>(initial
    ? { start_at: toDateTimeLocal(initial.start_at), end_at: toDateTimeLocal(initial.end_at), reason: initial.reason }
    : emptyForm)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!form.start_at || !form.end_at) { setError(t('BLOCKED_TIME_INVALID')); return }
    if (new Date(form.end_at) <= new Date(form.start_at)) { setError(t('BLOCKED_TIME_INVALID')); return }
    setSaving(true); setError(null)
    try {
      await onSave({
        ...form,
        start_at: new Date(form.start_at).toISOString(),
        end_at: new Date(form.end_at).toISOString(),
        reason: form.reason?.trim() ? form.reason.trim() : null,
      })
    } catch { /* Parent supplies user feedback. */ } finally { setSaving(false) }
  }

  const reasonPresets: Array<{ key: 'REASON_LUNCH' | 'REASON_PERSONAL' | 'REASON_REST' | 'REASON_OTHER' }> = [
    { key: 'REASON_LUNCH' }, { key: 'REASON_PERSONAL' }, { key: 'REASON_REST' }, { key: 'REASON_OTHER' },
  ]

  return <form className="form-card" onSubmit={submit}>
    <h2>{initial ? t('BLOCKED_EDIT') : t('BLOCKED_NEW')}</h2>
    {error && <p className="form-error" role="alert">{error}</p>}
    <label>{t('BLOCKED_START')}<input value={form.start_at} onChange={(event) => setForm({ ...form, start_at: event.target.value })} type="datetime-local" required /></label>
    <label>{t('BLOCKED_END')}<input value={form.end_at} onChange={(event) => setForm({ ...form, end_at: event.target.value })} type="datetime-local" required /></label>
    <label>{t('BLOCKED_REASON_OPTIONAL')}<input value={form.reason ?? ''} onChange={(event) => setForm({ ...form, reason: event.target.value })} maxLength={500} list="blocked-reason-presets" /></label>
    <datalist id="blocked-reason-presets">
      {reasonPresets.map(({ key }) => <option key={key} value={t(key)} />)}
    </datalist>
    <div className="form-actions"><button className="button secondary" type="button" onClick={onCancel}>{t('CANCEL')}</button><button className="button primary" disabled={saving}>{saving ? t('LOADING') : t('SAVE')}</button></div>
  </form>
}