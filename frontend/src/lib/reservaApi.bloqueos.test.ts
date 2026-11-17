import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { MENSAJE_SIN_CONEXION } from '@/lib/mensajes'
import { useAuthStore } from '@/stores/useAuthStore'
import {
  actualizarBloqueoApi,
  crearBloqueoApi,
  eliminarBloqueoApi,
  listarMisCitasApi,
  obtenerBloqueosApi,
} from './reservaApi'

const respuesta = (cuerpo: unknown, status = 200) =>
  new Response(JSON.stringify(cuerpo), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })

const bloqueoApi = {
  id: 7,
  barber: 3,
  start_at: '2026-12-01T13:00:00Z',
  end_at: '2026-12-01T18:00:00Z',
  reason: 'Cita médica',
  affected_appointments: {
    total: 3,
    notified: 1,
    pending: 1,
    without_channel: [
      {
        id: 40,
        contact_name: 'Luis Visitante',
        contact_phone: '3001234567',
        start_at: '2026-12-01T09:30:00-05:00',
      },
    ],
  },
}

const formulario = {
  barberoId: 3,
  fecha: '2026-12-01',
  horaInicio: '08:00',
  horaFin: '13:00',
  motivo: 'Cita médica',
}

describe('API de bloqueos (admin)', () => {
  const fetchMock = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
    useAuthStore.setState({ accessToken: 'tok' })
  })
  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
    useAuthStore.setState({ accessToken: null })
  })

  it('Dado bloqueos en el backend, Cuando se listan, Entonces se piden a /blocks y se traducen a fecha y horas de Colombia', async () => {
    fetchMock.mockResolvedValue(respuesta([bloqueoApi]))

    const bloqueos = await obtenerBloqueosApi()

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/v1\/blocks$/)
    expect(init.headers.Authorization).toBe('Bearer tok')
    expect(bloqueos).toEqual([
      {
        id: 7,
        barberoId: 3,
        fecha: '2026-12-01',
        horaInicio: '08:00',
        horaFin: '13:00',
        motivo: 'Cita médica',
        citasAfectadas: {
          total: 3,
          avisadas: 1,
          pendientes: 1,
          sinCanal: [
            {
              id: 40,
              nombre: 'Luis Visitante',
              celular: '3001234567',
              inicio: '2026-12-01T09:30:00-05:00',
            },
          ],
        },
      },
    ])
  })

  it('Dado un bloqueo nuevo, Cuando se crea, Entonces envía barbero, inicio y fin con zona de Colombia y motivo', async () => {
    fetchMock.mockResolvedValue(respuesta(bloqueoApi, 201))

    const creado = await crearBloqueoApi(formulario)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/v1\/blocks$/)
    expect(init.method).toBe('POST')
    expect(JSON.parse(init.body)).toEqual({
      barber: 3,
      start_at: '2026-12-01T08:00:00-05:00',
      end_at: '2026-12-01T13:00:00-05:00',
      reason: 'Cita médica',
    })
    expect(creado.id).toBe(7)
  })

  it('Dado un bloqueo existente, Cuando se edita, Entonces usa PUT /blocks/{id} con el mismo contrato', async () => {
    fetchMock.mockResolvedValue(respuesta(bloqueoApi))

    await actualizarBloqueoApi('7', formulario)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/v1\/blocks\/7$/)
    expect(init.method).toBe('PUT')
    expect(JSON.parse(init.body).start_at).toBe('2026-12-01T08:00:00-05:00')
  })

  it('Dado un bloqueo existente, Cuando se elimina, Entonces usa DELETE /blocks/{id}', async () => {
    fetchMock.mockResolvedValue(new Response(null, { status: 204 }))

    await eliminarBloqueoApi(7)

    const [url, init] = fetchMock.mock.calls[0]
    expect(url).toMatch(/\/api\/v1\/blocks\/7$/)
    expect(init.method).toBe('DELETE')
  })

  it('Dado que el backend rechaza el bloqueo, Cuando se crea, Entonces muestra el motivo en español', async () => {
    fetchMock.mockResolvedValue(
      respuesta({ end_at: ['El fin debe ser posterior al inicio.'] }, 400),
    )

    await expect(crearBloqueoApi(formulario)).rejects.toThrow(
      'El fin debe ser posterior al inicio.',
    )
  })

  it('Dado que el usuario no es administrador, Cuando lista, Entonces explica que no tiene permiso', async () => {
    fetchMock.mockResolvedValue(respuesta({ detail: 'forbidden' }, 403))

    await expect(obtenerBloqueosApi()).rejects.toThrow(/no tienes permiso/i)
  })

  it('Dado que no hay conexión, Cuando lista, Entonces muestra el mensaje amigable', async () => {
    fetchMock.mockRejectedValue(new TypeError('Failed to fetch'))

    await expect(obtenerBloqueosApi()).rejects.toThrow(MENSAJE_SIN_CONEXION)
  })
})

describe('Mis citas: cita afectada por un bloqueo', () => {
  const fetchMock = vi.fn()
  beforeEach(() => {
    vi.stubGlobal('fetch', fetchMock)
  })
  afterEach(() => {
    fetchMock.mockReset()
    vi.unstubAllGlobals()
  })

  it('Dado una cita afectada, Cuando el cliente lista sus citas, Entonces llega marcada', async () => {
    const base = {
      status: 'PENDING',
      start_at: '2026-12-01T15:00:00Z',
      end_at: '2026-12-01T15:30:00Z',
      price: '25000.00',
      service: { id: 2, name: 'Corte', price: 25000, duration_minutes: 30 },
      barber: { id: 9, name: 'Thiago' },
    }
    fetchMock.mockResolvedValue(
      respuesta([
        { ...base, id: 1, affected_by_block: true },
        { ...base, id: 2, affected_by_block: false },
      ]),
    )

    const citas = await listarMisCitasApi()

    expect(citas.map((c) => c.afectadaPorBloqueo)).toEqual([true, false])
  })
})
