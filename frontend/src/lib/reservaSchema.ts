import { z } from 'zod'

export const clienteSchema = z.object({
  nombre: z
    .string()
    .trim()
    .min(3, 'Ingresa tu nombre completo')
    .max(80, 'El nombre es demasiado largo'),
  celular: z
    .string()
    .transform((v) => v.replace(/[\s-]/g, ''))
    .pipe(z.string().regex(/^3\d{9}$/, 'Ingresa un celular colombiano de 10 dígitos')),
})

export type ClienteFormValues = z.input<typeof clienteSchema>
export type ClienteData = z.output<typeof clienteSchema>
