import '@fontsource-variable/inter'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import { ArrowLeft, CalendarPlus, Moon, Sun, Sunset } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { botonPrimario, titulo } from '@/components/booking/wizard/estilos'
import { Footer } from '@/components/layout/Footer'
import { Navbar } from '@/components/layout/Navbar'
import { AvisoCita, type Aviso } from '@/components/perfil/AvisoCita'
import { ModalCancelar } from '@/components/perfil/ModalCancelar'
import { ModalReprogramar } from '@/components/perfil/ModalReprogramar'
import { cancelacionSeraTardia, textoHoras } from '@/components/perfil/reglas'
import { TarjetaCita } from '@/components/perfil/TarjetaCita'
import { TarjetaCitaCancelada } from '@/components/perfil/TarjetaCitaCancelada'
import type { CitaConfirmada } from '@/lib/reservaApi'
import { periodoSegunHora, primerNombre, saludoSegunHora } from '@/lib/saludo'
import { useAuthStore } from '@/stores/useAuthStore'
import { useCitasStore } from '@/stores/useCitasStore'

export function PerfilPage() {
  const user = useAuthStore((s) => s.user)
  const {
    citas,
    isLoading,
    error,
    canceladas,
    cargandoCanceladas,
    errorCanceladas,
    fetchMisCitas,
    fetchCanceladas,
    cancelarCita,
    reprogramarCita,
  } = useCitasStore()
  const [vista, setVista] = useState<'proximas' | 'canceladas'>('proximas')

  const [aReprogramar, setAReprogramar] = useState<CitaConfirmada | null>(null)
  const [aCancelar, setACancelar] = useState<CitaConfirmada | null>(null)
  const [cancelando, setCancelando] = useState(false)
  const [errorCancelar, setErrorCancelar] = useState<string | null>(null)
  const [aviso, setAviso] = useState<Aviso | null>(null)
  // Un solo «ahora» por render para que todas las tarjetas concuerden.
  const [ahora, setAhora] = useState(() => Date.now())

  const hora = new Date(ahora).getHours()
  const nombre = primerNombre(user?.fullName)
  const IconoDelDia = { manana: Sun, tarde: Sunset, noche: Moon }[
    periodoSegunHora(hora)
  ]

  useEffect(() => {
    void fetchMisCitas()
  }, [fetchMisCitas])

  // Refresca el reloj cada minuto: el botón de reprogramar se apaga solo al vencer el límite.
  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), 60_000)
    return () => clearInterval(id)
  }, [])

  function abrirVista(nueva: 'proximas' | 'canceladas') {
    setVista(nueva)
    if (nueva === 'canceladas') void fetchCanceladas()
  }

  async function confirmarCancelar() {
    if (!aCancelar) return
    setCancelando(true)
    setErrorCancelar(null)
    try {
      const { tardia } = await cancelarCita(aCancelar.id)
      setAviso({
        tipo: 'exito',
        titulo: 'Cita cancelada',
        detalle: `Tu cita de ${aCancelar.servicio.nombre} con ${aCancelar.barbero.nombre} ya no está agendada.`,
        nota: tardia
          ? `Se canceló con menos de ${textoHoras(aCancelar.horasAntelacion)} de antelación, por eso quedó registrada como cancelación tardía.`
          : undefined,
      })
      setACancelar(null)
    } catch (err) {
      setErrorCancelar(
        err instanceof Error ? err.message : 'Error al cancelar la cita.',
      )
    } finally {
      setCancelando(false)
    }
  }

  async function confirmarReprogramar(fecha: string, hora: string) {
    if (!aReprogramar) return
    // El backend exige ISO 8601 con zona; las franjas son hora de Colombia.
    await reprogramarCita(aReprogramar.id, `${fecha}T${hora}:00-05:00`)
    setAviso({
      tipo: 'exito',
      titulo: 'Cita reprogramada',
      detalle: `Tu cita de ${aReprogramar.servicio.nombre} quedó para el ${fecha} a las ${hora}.`,
    })
    setAReprogramar(null)
  }

  return (
    <div className="flex min-h-screen flex-col bg-[#FAFAF8] font-[Inter_Variable] text-[#101820] dark:bg-[#101820] dark:text-[#F7F1E8]">
      <Navbar />
      <main className="relative flex flex-1 justify-center overflow-hidden p-4 sm:p-8">
        <div
          className="bf-patron-rayas pointer-events-none absolute inset-0 opacity-40"
          aria-hidden="true"
        />
        <div className="relative w-full max-w-3xl">
          <Link
            to="/"
            className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-[#101820]/60 transition-colors hover:text-[#B3263B] dark:text-[#F7F1E8]/60 dark:hover:text-[#E5283C]"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Volver al inicio
          </Link>
          <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className={`${titulo} text-3xl`}>Mis citas</h1>
              <p className="bf-bienvenida flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm text-[#101820]/60 dark:text-[#F7F1E8]/60">
                <IconoDelDia
                  className="size-4 text-[#B3263B] dark:text-[#E5283C]"
                  aria-hidden="true"
                />
                <span className="font-semibold text-[#101820] dark:text-[#F7F1E8]">
                  {`¡${saludoSegunHora(hora)}${nombre ? `, ${nombre}` : ''}!`}
                </span>
                <span>Reprograma o cancela tus reservas.</span>
              </p>
            </div>
            <Link to="/reservar" className={`${botonPrimario} h-10`}>
              <CalendarPlus className="size-4" aria-hidden="true" />
              Nueva reserva
            </Link>
          </header>

          <div
            role="tablist"
            aria-label="Tus citas"
            className="mb-5 inline-flex rounded-xl border border-[#101820]/12 bg-white p-1 dark:border-white/10 dark:bg-[#151915]"
          >
            {(
              [
                ['proximas', 'Próximas'],
                ['canceladas', 'Canceladas'],
              ] as const
            ).map(([id, texto]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={vista === id}
                onClick={() => abrirVista(id)}
                className={
                  vista === id
                    ? 'rounded-lg bg-[#101820] px-4 py-1.5 text-sm font-semibold text-[#F7F1E8] dark:bg-[#E5283C] dark:text-white'
                    : 'rounded-lg px-4 py-1.5 text-sm font-medium text-[#101820]/60 hover:text-[#101820] dark:text-[#F7F1E8]/60 dark:hover:text-[#F7F1E8]'
                }
              >
                {texto}
              </button>
            ))}
          </div>

          {aviso && <AvisoCita aviso={aviso} onCerrar={() => setAviso(null)} />}

          {vista === 'canceladas' && (
            <>
              {cargandoCanceladas && (
                <p className="text-sm text-[#101820]/60 dark:text-[#F7F1E8]/60">
                  Cargando citas…
                </p>
              )}
              {errorCanceladas && (
                <p role="alert" className="text-sm text-[#E5283C] dark:text-red-300">
                  {errorCanceladas}
                </p>
              )}
              {!cargandoCanceladas && !errorCanceladas && canceladas.length === 0 && (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center dark:border-white/15 dark:bg-[#151915]">
                  <p className={`${titulo} text-xl`}>No tienes citas canceladas</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-white/55">
                    Aquí aparecerán las que canceles o cuya hora pase sin atenderse.
                  </p>
                </div>
              )}
              <ul className="space-y-4">
                {canceladas.map((c) => (
                  <TarjetaCitaCancelada key={c.id} cita={c} />
                ))}
              </ul>
            </>
          )}

          {vista === 'proximas' && (
            <>
              {isLoading && (
                <p className="text-sm text-[#101820]/60 dark:text-[#F7F1E8]/60">
                  Cargando citas…
                </p>
              )}
              {error && (
                <p role="alert" className="text-sm text-[#E5283C] dark:text-red-300">
                  {error}
                </p>
              )}

              {!isLoading && !error && citas.length === 0 && (
                <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center dark:border-white/15 dark:bg-[#151915]">
                  <p className={`${titulo} text-xl`}>Aún no tienes citas</p>
                  <p className="mt-1 text-sm text-slate-500 dark:text-white/55">
                    No tienes citas programadas actualmente.
                  </p>
                  <Link to="/reservar" className={`${botonPrimario} mt-4`}>
                    Reservar ahora
                  </Link>
                </div>
              )}

              <ul className="space-y-4">
                {citas.map((cita) => (
                  <TarjetaCita
                    key={cita.id}
                    cita={cita}
                    ahora={ahora}
                    onReprogramar={() => setAReprogramar(cita)}
                    onCancelar={() => {
                      setErrorCancelar(null)
                      setACancelar(cita)
                    }}
                  />
                ))}
              </ul>
            </>
          )}
        </div>
      </main>
      <Footer />

      {aCancelar && (
        <ModalCancelar
          cita={aCancelar}
          tardia={cancelacionSeraTardia(aCancelar, ahora)}
          enviando={cancelando}
          error={errorCancelar}
          onConfirmar={() => void confirmarCancelar()}
          onCerrar={() => setACancelar(null)}
        />
      )}
      {aReprogramar && (
        <ModalReprogramar
          cita={aReprogramar}
          onConfirmar={confirmarReprogramar}
          onCerrar={() => setAReprogramar(null)}
        />
      )}
    </div>
  )
}
