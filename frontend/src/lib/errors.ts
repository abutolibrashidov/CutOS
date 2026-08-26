import axios from 'axios'

import { t } from '../i18n/uz'

export function userError(error: unknown, fallback: 'save' | 'delete' | 'load' = 'load'): string {
  if (axios.isAxiosError(error)) {
    if (error.response?.status === 401 || error.response?.status === 403) return t('AUTH_ERROR')
    const detail = error.response?.data?.detail
    if (typeof detail === 'string' && error.response?.status && error.response.status < 500) {
      return detail
    }
    if (error.response?.status === 422) return t('VALIDATION_ERROR')
    if (error.response?.status && error.response.status >= 500) return t('SERVER_ERROR')
  }

  if (fallback === 'save') return t('SAVE_ERROR')
  if (fallback === 'delete') return t('DELETE_ERROR')
  return t('UNKNOWN_ERROR')
}
