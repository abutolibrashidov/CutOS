import { t, type UzKey } from '../i18n/uz'

export function formatMoney(value: number): string {
  return `${new Intl.NumberFormat('uz-UZ').format(value)} ${t('SERVICE_UZS')}`
}

export function dayName(weekday: number): string {
  return t(`DAY_${weekday}` as UzKey)
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('uz-UZ', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Tashkent',
  }).format(new Date(value))
}

export function toDateTimeLocal(value: string): string {
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60_000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}
