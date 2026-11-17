import { useForm, type Resolver } from 'react-hook-form'
import {
  clienteSchema,
  type ClienteData,
  type ClienteFormValues,
} from '@/lib/reservaSchema'
import { useAuthStore } from '@/stores/useAuthStore'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { ArrowRight } from 'lucide-react'
import { botonPrimario, campo } from './estilos'
import { fechaLarga, formatearPrecio } from './formato'

// Resolver mínimo para Zod (no se usa @hookform/resolvers: no está en el stack aprobado).
const zodResolver: Resolver<ClienteFormValues> = (values) => {
  const r = clienteSchema.safeParse(values)
  if (r.success) return { values: r.data, errors: {} }
  const errors: Record<string, { type: string; message: string }> = {}
  for (const issue of r.error.issues) {
    const campo = String(issue.path[0])
    if (!errors[campo]) errors[campo] = { type: issue.code, message: issue.message }
  }
  return { values: {}, errors }
}

interface Props {
  error: string | null
  enviando: boolean
  onConfirmar: (cliente: ClienteData) => void
}

export function PasoConfirmar({ error, enviando, onConfirmar }: Props) {
  const servicio = useReservaWizardStore((s) => s.servicio)
  const barbero = useReservaWizardStore((s) => s.barbero)
  const fecha = useReservaWizardStore((s) => s.fecha)
  const hora = useReservaWizardStore((s) => s.hora)
  // Solo el cliente reserva a su propio nombre; el admin o el barbero agendan para
  // otra persona, así que su nombre no se precarga.
  const nombreCuenta = useAuthStore((s) =>
    s.user?.role === 'cliente' ? s.user.fullName : undefined,
  )
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ClienteFormValues>({
    resolver: zodResolver,
    // Quien tiene cuenta ya dio su nombre al registrarse: se precarga (editable).
    // El celular lo escribe siempre el cliente.
    defaultValues: { nombre: nombreCuenta ?? '', celular: '' },
  })

  return (
    <form
      id="form-confirmar"
      noValidate
      onSubmit={handleSubmit((v) => onConfirmar(v as unknown as ClienteData))}
      className="grid gap-6 md:grid-cols-[1fr_minmax(0,320px)]"
    >
      <div className="space-y-4">
        <p className="rounded-xl border border-[#B3263B]/25 bg-[#FBEEF0] p-4 text-sm font-medium text-[#101820]/80 dark:border-[#E5283C]/30 dark:bg-[#E5283C]/10 dark:text-[#F7F1E8]/85">
          Tu cita aún no está agendada: revisa el resumen y pulsa{' '}
          <strong>Confirmar reserva</strong> para reservarla.
        </p>
        <div className="space-y-1.5">
          <label
            htmlFor="nombre"
            className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75"
          >
            Nombre completo
          </label>
          <input
            id="nombre"
            autoComplete="name"
            aria-invalid={!!errors.nombre}
            className={campo}
            {...register('nombre')}
          />
          {errors.nombre && (
            <p className="text-xs text-[#B3263B] dark:text-[#E5283C]">
              {errors.nombre.message}
            </p>
          )}
        </div>
        <div className="space-y-1.5">
          <label
            htmlFor="celular"
            className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75"
          >
            Celular
          </label>
          <input
            id="celular"
            type="tel"
            inputMode="numeric"
            autoComplete="tel-national"
            aria-invalid={!!errors.celular}
            className={campo}
            {...register('celular')}
          />
          {errors.celular && (
            <p className="text-xs text-[#B3263B] dark:text-[#E5283C]">
              {errors.celular.message}
            </p>
          )}
        </div>
        {error && (
          <p
            role="alert"
            className="rounded-xl border border-[#B3263B]/25 bg-[#FBEEF0] p-3 text-sm text-[#B3263B] dark:border-[#E5283C]/30 dark:bg-[#E5283C]/10 dark:text-[#E5283C]"
          >
            {error}
          </p>
        )}
      </div>

      {/* Resumen estilo ticket de barbería */}
      <section className="relative overflow-hidden rounded-2xl border border-dashed border-[#101820]/25 bg-[#101820] p-5 text-[#F7F1E8] dark:border-[#F7F1E8]/25 dark:bg-[#0B1117]">
        <div
          className="bf-patron-rayas pointer-events-none absolute inset-0 opacity-50"
          aria-hidden="true"
        />
        <div className="relative">
          <h3 className="mb-4 font-[Barlow_Condensed] text-base font-bold tracking-widest text-[#F7F1E8] uppercase">
            Resumen
          </h3>
          <dl className="space-y-3">
            <Fila etiqueta="Servicio" valor={servicio?.nombre} />
            <Fila etiqueta="Profesional" valor={barbero?.nombre} />
            <Fila etiqueta="Fecha" valor={fecha ? fechaLarga(fecha) : undefined} />
            <Fila etiqueta="Hora" valor={hora ?? undefined} />
            <div className="flex items-baseline justify-between border-t border-dashed border-[#F7F1E8]/25 pt-3">
              <dt className="text-xs text-[#F7F1E8]/65">Total</dt>
              <dd className="font-[Barlow_Condensed] text-2xl font-bold text-[#F7F1E8]">
                {servicio ? formatearPrecio(servicio.precio) : '—'}
              </dd>
            </div>
          </dl>
        </div>
      </section>

      <div className="md:col-span-2">
        <button type="submit" className={`${botonPrimario} w-full`} disabled={enviando}>
          {enviando ? 'Confirmando…' : 'Confirmar reserva'}
          {!enviando && <ArrowRight className="size-4" />}
        </button>
      </div>
    </form>
  )
}

function Fila({ etiqueta, valor }: { etiqueta: string; valor?: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-xs text-[#F7F1E8]/65">{etiqueta}</dt>
      <dd className="text-right text-xs font-semibold text-[#F7F1E8] first-letter:uppercase">
        {valor ?? '—'}
      </dd>
    </div>
  )
}
