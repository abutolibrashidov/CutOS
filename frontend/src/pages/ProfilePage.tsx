import { useCallback, useEffect, useState } from 'react'

import { getProfile, updateProfile, type BarberProfile } from '../api/client'
import { ErrorState, LoadingState, SuccessMessage } from '../components/Feedback'
import { t } from '../i18n/uz'
import { userError } from '../lib/errors'

export function ProfilePage() {
  const [profile, setProfile] = useState<BarberProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setProfile(await getProfile()) } catch (loadError) { setError(userError(loadError)) } finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!profile?.full_name.trim()) { setError(t('PROFILE_NAME_REQUIRED')); return }
    setSaving(true); setError(null); setSuccess(null)
    try {
      const saved = await updateProfile({
        full_name: profile.full_name.trim(),
        phone: profile.phone?.trim() || null,
        bio: profile.bio?.trim() || null,
        avatar_url: profile.avatar_url?.trim() || null,
      })
      setProfile(saved); setSuccess(t('PROFILE_SAVED'))
    } catch (saveError) { setError(userError(saveError, 'save')) } finally { setSaving(false) }
  }

  if (loading) return <LoadingState />
  if (error && !profile) return <ErrorState message={error} onRetry={() => void load()} />
  if (!profile) return null

  return (
    <section>
      <p className="eyebrow">{t('NAV_PROFILE')}</p><h1>{t('PROFILE_TITLE')}</h1>
      <SuccessMessage message={success} />
      {error && <p className="form-error" role="alert">{error}</p>}
      <form className="form-card" onSubmit={submit}>
        <label>{t('PROFILE_NAME')}<input value={profile.full_name} onChange={(event) => setProfile({ ...profile, full_name: event.target.value })} maxLength={255} required /></label>
        <label>{t('PROFILE_PHONE')}<input value={profile.phone ?? ''} onChange={(event) => setProfile({ ...profile, phone: event.target.value })} inputMode="tel" maxLength={30} /></label>
        <label>{t('PROFILE_BIO')}<textarea value={profile.bio ?? ''} onChange={(event) => setProfile({ ...profile, bio: event.target.value })} rows={4} /></label>
        <label>{t('PROFILE_AVATAR')}<input value={profile.avatar_url ?? ''} onChange={(event) => setProfile({ ...profile, avatar_url: event.target.value })} type="url" /></label>
        <button className="button primary" disabled={saving}>{saving ? t('LOADING') : t('SAVE')}</button>
      </form>
    </section>
  )
}
