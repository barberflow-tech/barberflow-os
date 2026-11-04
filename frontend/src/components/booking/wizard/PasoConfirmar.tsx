import { Link } from 'react-router-dom'
import { useForm, type Resolver } from 'react-hook-form'
import {
  clienteSchema,
  type ClienteData,
  type ClienteFormValues,
} from '@/lib/reservaSchema'
import { useReservaWizardStore } from '@/stores/useReservaWizardStore'
import { campo } from './estilos'
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
  requiereSesion?: boolean
  onConfirmar: (cliente: ClienteData) => void
}

export function PasoConfirmar({ error, requiereSesion, onConfirmar }: Props) {
  const servicio = useReservaWizardStore((s) => s.servicio)
  const barbero = useReservaWizardStore((s) => s.barbero)
  const fecha = useReservaWizardStore((s) => s.fecha)
  const hora = useReservaWizardStore((s) => s.hora)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ClienteFormValues>({
    resolver: zodResolver,
    defaultValues: { nombre: '', celular: '' },
  })

  return (
    <form
      id="form-confirmar"
      noValidate
      onSubmit={handleSubmit((v) => onConfirmar(v as unknown as ClienteData))}
      className="grid gap-6 md:grid-cols-[1fr_minmax(0,320px)]"
    >
      <div className="space-y-4">
        <div className="space-y-1.5">
          <label
            htmlFor="nombre"
            className="text-xs font-semibold text-slate-600 dark:text-white/65"
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
            <p className="text-xs text-[#E5283C] dark:text-[#d7b36a]">
              {errors.nombre.message}
            </p>
          )}
        </div>
        <div className="space-y-1.5">
          <label
            htmlFor="celular"
            className="text-xs font-semibold text-slate-600 dark:text-white/65"
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
            <p className="text-xs text-[#E5283C] dark:text-[#d7b36a]">
              {errors.celular.message}
            </p>
          )}
        </div>
        {error && (
          <p
            role="alert"
            className="rounded-xl bg-[#FEF2F3] dark:bg-[#d7b36a]/10 p-3 text-sm text-[#E5283C] dark:text-[#d7b36a]"
          >
            {error}{' '}
            {requiereSesion && (
              <Link to="/login" className="font-semibold underline">
                Iniciar sesión
              </Link>
            )}
          </p>
        )}
      </div>

      <section className="rounded-2xl bg-slate-50 dark:bg-white/5 p-5">
        <h3 className="mb-4 text-sm font-bold text-[#0B1B3A] dark:text-[#f4f1e9]">
          Resumen
        </h3>
        <dl className="space-y-3">
          <Fila etiqueta="Servicio" valor={servicio?.nombre} />
          <Fila etiqueta="Profesional" valor={barbero?.nombre} />
          <Fila etiqueta="Fecha" valor={fecha ? fechaLarga(fecha) : undefined} />
          <Fila etiqueta="Hora" valor={hora ?? undefined} />
          <div className="flex items-baseline justify-between border-t border-slate-200 dark:border-white/10 pt-3">
            <dt className="text-xs text-slate-500 dark:text-white/55">Total</dt>
            <dd className="text-xl font-bold text-[#0B1B3A] dark:text-[#f4f1e9]">
              {servicio ? formatearPrecio(servicio.precio) : '—'}
            </dd>
          </div>
        </dl>
      </section>
    </form>
  )
}

function Fila({ etiqueta, valor }: { etiqueta: string; valor?: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-xs text-slate-500 dark:text-white/55">{etiqueta}</dt>
      <dd className="text-right text-xs font-semibold text-[#0B1B3A] dark:text-[#f4f1e9] first-letter:uppercase">
        {valor ?? '—'}
      </dd>
    </div>
  )
}
