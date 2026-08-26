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

export function formatUtcClock(value: string): string {
  const date = new Date(value)
  const hours = String(date.getUTCHours()).padStart(2, '0')
  const minutes = String(date.getUTCMinutes()).padStart(2, '0')
  return `${hours}:${minutes}`
}

export function formatUtcDate(value: string): string {
  return new Date(value).toISOString().split('T')[0]
}

export function localDateTimeInputToUtcIso(value: string): string {
  return `${value}:00.000Z`
}
