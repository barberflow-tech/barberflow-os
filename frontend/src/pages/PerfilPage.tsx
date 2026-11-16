import '@fontsource-variable/inter'
import '@fontsource/barlow-condensed/600.css'
import '@fontsource/barlow-condensed/700.css'
import { ArrowLeft, CalendarPlus } from 'lucide-react'
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
import type { CitaConfirmada } from '@/lib/reservaApi'
import { useAuthStore } from '@/stores/useAuthStore'
import { useCitasStore } from '@/stores/useCitasStore'

export function PerfilPage() {
  const user = useAuthStore((s) => s.user)
  const { citas, isLoading, error, fetchMisCitas, cancelarCita, reprogramarCita } =
    useCitasStore()

  const [aReprogramar, setAReprogramar] = useState<CitaConfirmada | null>(null)
  const [aCancelar, setACancelar] = useState<CitaConfirmada | null>(null)
  const [cancelando, setCancelando] = useState(false)
  const [errorCancelar, setErrorCancelar] = useState<string | null>(null)
  const [aviso, setAviso] = useState<Aviso | null>(null)
  // Un solo «ahora» por render para que todas las tarjetas concuerden.
  const [ahora, setAhora] = useState(() => Date.now())

  useEffect(() => {
    void fetchMisCitas()
  }, [fetchMisCitas])

  // Refresca el reloj cada minuto: el botón de reprogramar se apaga solo al vencer el límite.
  useEffect(() => {
    const id = setInterval(() => setAhora(Date.now()), 60_000)
    return () => clearInterval(id)
  }, [])

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
    <div className="flex min-h-screen flex-col bg-[#F1F5F9] font-[Inter_Variable] dark:bg-[#0f1210]">
      <Navbar />
      <main className="flex flex-1 justify-center p-4 sm:p-8">
        <div className="w-full max-w-3xl">
          <Link
            to="/"
            className="mb-4 inline-flex items-center gap-1.5 text-sm font-medium text-slate-500 transition-colors hover:text-[#0B1B3A] dark:text-white/55 dark:hover:text-[#f4f1e9]"
          >
            <ArrowLeft className="size-4" aria-hidden="true" />
            Volver al inicio
          </Link>
          <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className={`${titulo} text-3xl`}>Mis citas</h1>
              <p className="text-sm text-slate-500 dark:text-white/55">
                {user?.email ?? 'Cliente'} · reprograma o cancela tus reservas
              </p>
            </div>
            <Link to="/reservar" className={`${botonPrimario} h-10`}>
              <CalendarPlus className="size-4" aria-hidden="true" />
              Nueva reserva
            </Link>
          </header>

          {aviso && <AvisoCita aviso={aviso} onCerrar={() => setAviso(null)} />}

          {isLoading && (
            <p className="text-sm text-slate-500 dark:text-white/55">Cargando citas…</p>
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
