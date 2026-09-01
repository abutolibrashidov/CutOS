import axios, { type AxiosInstance } from 'axios'

export interface BarberProfile {
  id: string
  location_id: string | null
  telegram_id: number
  full_name: string
  phone: string | null
  bio: string | null
  avatar_url: string | null
  is_active: boolean
  created_at: string
}

export interface Service {
  id: string
  barber_id: string
  name: string
  price_uzs: number
  duration_minutes: number
  is_active: boolean
  created_at: string
}

export interface ServicePayload {
  name: string
  price_uzs: number
  duration_minutes: number
}

export interface ScheduleDay {
  id: string | null
  barber_id: string
  weekday: number
  start_time: string | null
  end_time: string | null
  is_working: boolean
}

export interface SchedulePayload {
  weekday: number
  start_time: string
  end_time: string
  is_working: boolean
}

export interface BlockedTime {
  id: string
  barber_id: string
  start_at: string
  end_at: string
  reason: string | null
  created_at: string
}

export interface BlockedTimePayload {
  start_at: string
  end_at: string
  reason: string | null
}

// Call ready() once at module load — safe and idempotent; tells Telegram the app has loaded.
try {
  window.Telegram?.WebApp?.ready()
} catch {
  // Expected outside Telegram (local browser dev).
}

function createApiClient(): AxiosInstance {
  const baseURL = import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1'

  const client = axios.create({
    baseURL,
    headers: { 'Content-Type': 'application/json' },
  })

  client.interceptors.request.use((config) => {
    // Read initData fresh on every request — avoids the race condition where
    // window.Telegram hasn't been injected yet when the module was first imported.
    const initData = window.Telegram?.WebApp?.initData ?? ''
    if (initData) {
      config.headers.Authorization = `tma ${initData}`
    } else if (import.meta.env.DEV && import.meta.env.VITE_DEV_TELEGRAM_ID) {
      // Development-only fallback — never active in production builds.
      config.headers.Authorization = `test ${import.meta.env.VITE_DEV_TELEGRAM_ID}`
    }
    return config
  })

  return client
}

export const apiClient = createApiClient()

export async function getProfile(): Promise<BarberProfile> {
  return (await apiClient.get<BarberProfile>('/barber/profile')).data
}

export async function updateProfile(payload: Pick<BarberProfile, 'full_name' | 'phone' | 'bio' | 'avatar_url'>): Promise<BarberProfile> {
  return (await apiClient.put<BarberProfile>('/barber/profile', payload)).data
}

export async function getServices(): Promise<Service[]> {
  return (await apiClient.get<Service[]>('/barber/services/')).data
}

export async function createService(payload: ServicePayload): Promise<Service> {
  return (await apiClient.post<Service>('/barber/services/', payload)).data
}

export async function updateService(id: string, payload: Partial<ServicePayload & Pick<Service, 'is_active'>>): Promise<Service> {
  return (await apiClient.put<Service>(`/barber/services/${id}`, payload)).data
}

export async function deleteService(id: string): Promise<void> {
  await apiClient.delete(`/barber/services/${id}`)
}

export async function getSchedule(): Promise<ScheduleDay[]> {
  return (await apiClient.get<ScheduleDay[]>('/barber/schedule/')).data
}

export async function updateSchedule(payload: SchedulePayload[]): Promise<ScheduleDay[]> {
  return (await apiClient.post<ScheduleDay[]>('/barber/schedule/', payload)).data
}

export async function getBlockedTimes(): Promise<BlockedTime[]> {
  return (await apiClient.get<BlockedTime[]>('/barber/blocked-times/')).data
}

export async function createBlockedTime(payload: BlockedTimePayload): Promise<BlockedTime> {
  return (await apiClient.post<BlockedTime>('/barber/blocked-times/', payload)).data
}

export async function updateBlockedTime(id: string, payload: BlockedTimePayload): Promise<BlockedTime> {
  return (await apiClient.put<BlockedTime>(`/barber/blocked-times/${id}`, payload)).data
}

export async function deleteBlockedTime(id: string): Promise<void> {
  await apiClient.delete(`/barber/blocked-times/${id}`)
}

export interface BarberAppointmentService {
  service_id: string
  service_name_at_booking: string
  price_at_booking: number
  duration_at_booking: number
}

export interface BarberAppointmentResponse {
  id: string
  barber_id: string
  customer_id: string
  start_at: string
  end_at: string
  status: string
  source: string
  price_at_booking: number
  duration_at_booking: number
  appointment_services: BarberAppointmentService[]
  notes: string | null
  created_at: string
  customer_full_name: string | null
  customer_phone: string | null
  barber_full_name: string | null
}

export interface WalkInPayload {
  full_name: string
  phone: string | null
  service_ids: string[]
  start_at: string
}

export async function getBarberAppointments(): Promise<BarberAppointmentResponse[]> {
  return (await apiClient.get<BarberAppointmentResponse[]>('/barber/appointments/')).data
}

export async function cancelBarberAppointment(id: string): Promise<BarberAppointmentResponse> {
  return (await apiClient.post<BarberAppointmentResponse>(`/barber/appointments/${id}/cancel`)).data
}

export async function createWalkIn(payload: WalkInPayload): Promise<BarberAppointmentResponse> {
  return (await apiClient.post<BarberAppointmentResponse>('/barber/appointments/walk-in/', payload)).data
}
