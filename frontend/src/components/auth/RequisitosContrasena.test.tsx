import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { RequisitosContrasena } from './RequisitosContrasena'

const requisito = (texto: string) =>
  screen.getByText(texto).closest('li') as HTMLLIElement

describe('RequisitosContrasena', () => {
  it('Dado una contraseña vacía, Cuando se muestra, Entonces ningún requisito está cumplido', () => {
    render(<RequisitosContrasena contrasena="" />)

    for (const texto of [
      'Al menos 8 caracteres',
      'Una letra mayúscula',
      'Una letra minúscula',
      'Un número',
    ]) {
      expect(requisito(texto)).toHaveAttribute('data-cumplido', 'false')
      expect(requisito(texto)).toHaveTextContent(/pendiente/)
    }
  })

  it('Dado una contraseña a medias, Cuando se escribe, Entonces solo se marcan los requisitos que cumple', () => {
    render(<RequisitosContrasena contrasena="abc" />)

    expect(requisito('Una letra minúscula')).toHaveAttribute('data-cumplido', 'true')
    expect(requisito('Una letra minúscula')).toHaveTextContent(/cumplido/)
    expect(requisito('Al menos 8 caracteres')).toHaveAttribute('data-cumplido', 'false')
    expect(requisito('Una letra mayúscula')).toHaveAttribute('data-cumplido', 'false')
    expect(requisito('Un número')).toHaveAttribute('data-cumplido', 'false')
  })

  it('Dado una contraseña segura, Cuando se escribe, Entonces todos los requisitos quedan cumplidos', () => {
    render(<RequisitosContrasena contrasena="Clave-segura-1" />)

    for (const item of screen.getAllByRole('listitem')) {
      expect(item).toHaveAttribute('data-cumplido', 'true')
    }
  })

  it('Dado una contraseña con tilde o eñe, Cuando se escribe, Entonces reconoce mayúsculas y minúsculas', () => {
    render(<RequisitosContrasena contrasena="Ñandú" />)

    expect(requisito('Una letra mayúscula')).toHaveAttribute('data-cumplido', 'true')
    expect(requisito('Una letra minúscula')).toHaveAttribute('data-cumplido', 'true')
  })
})
