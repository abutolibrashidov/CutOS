import { t } from '../i18n/uz'

export function LoadingState() {
  return <p className="state-message">{t('LOADING')}</p>
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="error-state" role="alert">
      <p>{message}</p>
      {onRetry && <button className="button secondary" onClick={onRetry}>{t('RETRY')}</button>}
    </div>
  )
}

export function SuccessMessage({ message }: { message: string | null }) {
  return message ? <p className="success-message" role="status">{message}</p> : null
}
