// Requisitos mínimos de una contraseña al registrarse. El backend exige además que
// no sea común, ni solo números, ni parecida al correo; eso solo lo puede decidir él.

export interface RequisitoContrasena {
  id: string
  texto: string
  cumple: (contrasena: string) => boolean
}

export const REQUISITOS_CONTRASENA: RequisitoContrasena[] = [
  {
    id: 'longitud',
    texto: 'Al menos 8 caracteres',
    cumple: (c) => c.length >= 8,
  },
  {
    id: 'mayuscula',
    texto: 'Una letra mayúscula',
    cumple: (c) => /\p{Lu}/u.test(c),
  },
  {
    id: 'minuscula',
    texto: 'Una letra minúscula',
    cumple: (c) => /\p{Ll}/u.test(c),
  },
  {
    id: 'numero',
    texto: 'Un número',
    cumple: (c) => /\d/.test(c),
  },
]

export const contrasenaCumpleRequisitos = (contrasena: string): boolean =>
  REQUISITOS_CONTRASENA.every((requisito) => requisito.cumple(contrasena))
