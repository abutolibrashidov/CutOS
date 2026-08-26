import { apiClient } from './client'

export interface LocationPublic {
  id: string
  name: string
  address: string | null
  city: string | null
}

export interface BarberPublic {
  id: string
  full_name: string
  bio: string | null
  avatar_url: string | null
}

export interface ServicePublic {
  id: string
  name: string
  price_uzs: number
  duration_minutes: number
}

export interface AvailabilityResponse {
  barber_id: string
  date: string
  slots: string[]
}

export interface AppointmentServiceSnapshot {
  service_id: string
  service_name_at_booking: string
  price_at_booking: number
  duration_at_booking: number
}

export interface AppointmentResponse {
  id: string
  barber_id: string
  customer_id: string
  start_at: string
  end_at: string
  status: string
  source: string
  price_at_booking: number
  duration_at_booking: number
  appointment_services: AppointmentServiceSnapshot[]
  notes: string | null
  created_at: string
  customer_full_name: string | null
  customer_phone: string | null
  barber_full_name: string | null
}

export interface BookingResponse {
  appointment: AppointmentResponse
  barber: BarberPublic
  services: AppointmentServiceSnapshot[]
  total_price_uzs: number
  total_duration_minutes: number
}

export interface BookingRequest {
  location_id: string
  barber_id: string | null
  service_ids: string[]
  start_at: string  // ISO UTC
}

export async function getLocations(): Promise<LocationPublic[]> {
  return (await apiClient.get<LocationPublic[]>('/customer/locations/')).data
}

export async function getBarbers(location_id: string): Promise<BarberPublic[]> {
  return (
    await apiClient.get<BarberPublic[]>('/customer/barbers/', {
      params: { location_id },
    })
  ).data
}

export async function getBarberServices(barber_id: string): Promise<ServicePublic[]> {
  return (
    await apiClient.get<ServicePublic[]>(`/customer/barbers/${barber_id}/services/`)
  ).data
}

export async function getAvailableSlots(
  barber_id: string,
  service_ids: string[],
  date: string,
): Promise<AvailabilityResponse> {
  const params = new URLSearchParams()
  for (const id of service_ids) {
    params.append('service_ids', id)
  }
  params.append('date', date)
  return (
    await apiClient.get<AvailabilityResponse>(
      `/customer/barbers/${barber_id}/available-slots/?${params.toString()}`,
    )
  ).data
}

export async function createBooking(payload: BookingRequest): Promise<BookingResponse> {
  return (await apiClient.post<BookingResponse>('/customer/book/', payload)).data
}

export async function getMyAppointments(): Promise<AppointmentResponse[]> {
  return (await apiClient.get<AppointmentResponse[]>('/customer/appointments/')).data
}

export async function cancelMyAppointment(id: string): Promise<{ id: string; status: string; message: string }> {
  return (
    await apiClient.post<{ id: string; status: string; message: string }>(
      `/customer/appointments/${id}/cancel`,
    )
  ).data
}
