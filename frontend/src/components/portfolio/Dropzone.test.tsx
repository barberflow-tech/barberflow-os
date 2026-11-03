import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { Dropzone } from './Dropzone'

function archivo(nombre: string, tipo: string, bytes = 1024) {
  const f = new File(['x'], nombre, { type: tipo })
  Object.defineProperty(f, 'size', { value: bytes })
  return f
}

const SEIS_MB = 6 * 1024 * 1024

function soltar(files: File[]) {
  fireEvent.drop(screen.getByTestId('dropzone'), { dataTransfer: { files } })
}

describe('Dropzone', () => {
  beforeEach(() => {
    let n = 0
    URL.createObjectURL = vi.fn(() => `blob:preview-${n++}`)
    URL.revokeObjectURL = vi.fn()
  })

  it('Dado un archivo de más de 5 MB, Cuando el barbero lo arrastra, Entonces se bloquea la carga y muestra un aviso', () => {
    const onUpload = vi.fn()
    render(<Dropzone onUpload={onUpload} />)

    soltar([archivo('grande.png', 'image/png', SEIS_MB)])

    expect(screen.getByRole('alert')).toHaveTextContent(/grande\.png/)
    expect(screen.getByRole('alert')).toHaveTextContent(/5 MB/)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /subir/i })).not.toBeInTheDocument()
    expect(onUpload).not.toHaveBeenCalled()
  })

  it('Dado un archivo que no es PNG/JPG/WEBP, Cuando el barbero lo arrastra, Entonces se bloquea la carga y muestra un aviso', () => {
    render(<Dropzone onUpload={vi.fn()} />)

    soltar([archivo('cv.pdf', 'application/pdf'), archivo('anim.gif', 'image/gif')])

    const aviso = screen.getByRole('alert')
    expect(aviso).toHaveTextContent(/cv\.pdf/)
    expect(aviso).toHaveTextContent(/anim\.gif/)
    expect(aviso).toHaveTextContent(/PNG, JPG o WEBP/)
    expect(screen.queryByRole('img')).not.toBeInTheDocument()
  })

  it('Dado una imagen válida, Cuando la arrastra, Entonces muestra su pre-visualización local sin aviso', () => {
    render(<Dropzone onUpload={vi.fn()} />)

    soltar([archivo('fade.webp', 'image/webp')])

    expect(screen.getByRole('img', { name: /fade\.webp/ })).toHaveAttribute(
      'src',
      'blob:preview-0',
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('Dado el selector de archivos, Cuando elige una sola foto, Entonces la agrega a la lista', async () => {
    const user = userEvent.setup({ applyAccept: false })
    render(<Dropzone onUpload={vi.fn()} />)

    await user.upload(
      screen.getByLabelText(/seleccionar imagen/i),
      archivo('a.jpg', 'image/jpeg'),
    )

    expect(screen.getAllByRole('img')).toHaveLength(1)
  })

  it('Dado el selector de archivos, Cuando elige varias fotos a la vez, Entonces agrega todas', async () => {
    const user = userEvent.setup({ applyAccept: false })
    render(<Dropzone onUpload={vi.fn()} />)

    await user.upload(screen.getByLabelText(/seleccionar imagen/i), [
      archivo('a.jpg', 'image/jpeg'),
      archivo('b.png', 'image/png'),
      archivo('c.webp', 'image/webp'),
    ])

    expect(screen.getAllByRole('img')).toHaveLength(3)
  })

  it('Dadas fotos válidas e inválidas juntas, Cuando las arrastra, Entonces acepta las válidas y avisa de las inválidas', () => {
    render(<Dropzone onUpload={vi.fn()} />)

    soltar([archivo('ok.png', 'image/png'), archivo('malo.pdf', 'application/pdf')])

    expect(screen.getAllByRole('img')).toHaveLength(1)
    expect(screen.getByRole('alert')).toHaveTextContent(/malo\.pdf/)
    expect(screen.getByRole('alert')).not.toHaveTextContent(/ok\.png/)
  })

  it('Dada una foto en la lista, Cuando la quita, Entonces desaparece y libera su pre-visualización', async () => {
    const user = userEvent.setup()
    render(<Dropzone onUpload={vi.fn()} />)
    soltar([archivo('a.png', 'image/png')])

    await user.click(screen.getByRole('button', { name: /quitar a\.png/i }))

    expect(screen.queryByRole('img')).not.toBeInTheDocument()
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:preview-0')
  })

  it('Dadas fotos válidas, Cuando pulsa subir, Entonces muestra la barra de progreso de cada una y al terminar las marca como subidas', async () => {
    const user = userEvent.setup()
    let avanzar: (pct: number) => void = () => {}
    let terminar: () => void = () => {}
    const onUpload = vi.fn((_f: File, onProgress: (pct: number) => void) => {
      avanzar = onProgress
      return new Promise<void>((res) => {
        terminar = res
      })
    })
    render(<Dropzone onUpload={onUpload} />)
    soltar([archivo('a.png', 'image/png')])

    await user.click(screen.getByRole('button', { name: /subir 1 foto/i }))

    expect(onUpload).toHaveBeenCalledTimes(1)
    expect(onUpload.mock.calls[0][0].name).toBe('a.png')
    avanzar(40)
    await waitFor(() =>
      expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '40'),
    )

    terminar()
    expect(await screen.findByText(/subida/i)).toBeInTheDocument()
    expect(screen.queryByRole('progressbar')).not.toBeInTheDocument()
  })

  it('Dadas varias fotos, Cuando pulsa subir, Entonces sube cada una', async () => {
    const user = userEvent.setup()
    const onUpload = vi.fn().mockResolvedValue(undefined)
    render(<Dropzone onUpload={onUpload} />)
    soltar([archivo('a.png', 'image/png'), archivo('b.jpg', 'image/jpeg')])

    await user.click(screen.getByRole('button', { name: /subir 2 fotos/i }))

    await waitFor(() => expect(onUpload).toHaveBeenCalledTimes(2))
  })

  it('Dado un fallo de la carga, Cuando falla, Entonces avisa en esa foto y permite reintentar', async () => {
    const user = userEvent.setup()
    const onUpload = vi
      .fn()
      .mockRejectedValueOnce(new Error('Sin conexión'))
      .mockResolvedValue(undefined)
    render(<Dropzone onUpload={onUpload} />)
    soltar([archivo('a.png', 'image/png')])

    await user.click(screen.getByRole('button', { name: /subir 1 foto/i }))

    const item = await screen.findByRole('listitem')
    expect(within(item).getByText(/sin conexión/i)).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: /subir 1 foto/i }))
    expect(await screen.findByText(/subida/i)).toBeInTheDocument()
  })
})
