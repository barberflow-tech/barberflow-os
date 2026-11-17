import { Scissors } from 'lucide-react'
import React, { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  AuthError,
  iniciarSesion,
  registrarCuenta,
  restablecerContrasena,
  solicitarRecuperacion,
} from '@/lib/authApi'
import { contrasenaCumpleRequisitos } from '@/lib/requisitosContrasena'
import { useAuthStore } from '@/stores/useAuthStore'
import { RequisitosContrasena } from './RequisitosContrasena'

// 1. Esquema para Login
const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'El correo electrónico es requerido')
    .email('Ingrese un correo electrónico válido'),
  password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
  rememberMe: z.boolean().optional(),
})

// 2. Esquema para Registro
const registerSchema = z.object({
  fullName: z.string().min(3, 'El nombre completo debe tener al menos 3 caracteres'),
  email: z
    .string()
    .min(1, 'El correo electrónico es requerido')
    .email('Ingrese un correo electrónico válido'),
  password: z
    .string()
    .refine(
      contrasenaCumpleRequisitos,
      'Completa todos los requisitos de la contraseña',
    ),
  rememberMe: z.boolean().optional(),
})

// 3. Esquema para Olvidé Contraseña
const forgotSchema = z.object({
  email: z
    .string()
    .min(1, 'El correo electrónico es requerido')
    .email('Ingrese un correo electrónico válido'),
})

// 4. Esquema para elegir la nueva contraseña (pantalla del enlace del correo)
const resetSchema = z
  .object({
    password: z.string().min(8, 'La contraseña debe tener al menos 8 caracteres'),
    confirm: z.string().min(1, 'Confirma tu contraseña'),
  })
  .refine((datos) => datos.password === datos.confirm, {
    path: ['confirm'],
    message: 'Las contraseñas no coinciden',
  })

type ResetFormData = z.infer<typeof resetSchema>
type LoginFormData = z.infer<typeof loginSchema>
type RegisterFormData = z.infer<typeof registerSchema>
type ForgotFormData = z.infer<typeof forgotSchema>

type PasoAuth = 'login' | 'register'

interface LoginFormProps {
  /** Pestaña con la que abre el formulario (la página la deduce de la URL). */
  pasoInicial?: PasoAuth
  /** Avisa al cambiar entre «Iniciar sesión» y «Registrarme» para reflejarlo en la URL. */
  onPasoChange?: (paso: PasoAuth) => void
  /** Credenciales del enlace del correo (/restablecer?uid=…&token=…): abre «nueva contraseña». */
  restablecer?: { uid: string; token: string }
}

export const LoginForm: React.FC<LoginFormProps> = ({
  pasoInicial = 'login',
  onPasoChange,
  restablecer,
}) => {
  const setSession = useAuthStore((state) => state.setSession)
  const [isLoading, setIsLoading] = useState(false)
  const [authError, setAuthError] = useState<string | null>(null)

  // Estados de navegación entre vistas
  const [currentStep, setCurrentStep] = useState<
    'login' | 'register' | 'forgot' | 'forgot-success' | 'reset'
  >(restablecer ? 'reset' : pasoInicial)
  // Si la URL cambia (botón «atrás» del navegador), la pestaña la sigue.
  const [pasoPrevio, setPasoPrevio] = useState(pasoInicial)
  if (pasoInicial !== pasoPrevio) {
    setPasoPrevio(pasoInicial)
    setCurrentStep(pasoInicial)
  }
  const irA = (paso: PasoAuth) => {
    setCurrentStep(paso)
    onPasoChange?.(paso)
  }
  const [showPassword, setShowPassword] = useState(false)
  const [sentEmail, setSentEmail] = useState('')

  // Alertas dinámicas en pantalla
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [resendNotification, setResendNotification] = useState<string | null>(null)
  const [isResending, setIsResending] = useState(false)

  // Forms con React Hook Form + Zod
  const loginForm = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    mode: 'onTouched',
  })

  const registerForm = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    mode: 'onTouched',
  })

  const passwordRegistro = useWatch({ control: registerForm.control, name: 'password' })

  const forgotForm = useForm<ForgotFormData>({
    resolver: zodResolver(forgotSchema),
    mode: 'onTouched',
  })

  const resetForm = useForm<ResetFormData>({
    resolver: zodResolver(resetSchema),
    mode: 'onTouched',
  })

  // Submit Login
  const onLoginSubmit = async (data: LoginFormData) => {
    setIsLoading(true)
    setAuthError(null)
    try {
      setSession(await iniciarSesion(data.email, data.password))
    } catch (err) {
      setAuthError(
        err instanceof AuthError
          ? err.message
          : 'Ocurrió un error inesperado. Inténtalo de nuevo.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  // Submit Registro (redirige a login con banner verde)
  const onRegisterSubmit = async (data: RegisterFormData) => {
    setIsLoading(true)
    setAuthError(null)
    try {
      await registrarCuenta(data.fullName, data.email, data.password)
      loginForm.setValue('email', data.email)
      setSuccessMessage('Cuenta creada con éxito. Ya puedes iniciar sesión.')
      irA('login')
    } catch (err) {
      setAuthError(
        err instanceof AuthError
          ? err.message
          : 'Ocurrió un error inesperado. Inténtalo de nuevo.',
      )
    } finally {
      setIsLoading(false)
    }
  }

  const mensajeDe = (err: unknown) =>
    err instanceof AuthError
      ? err.message
      : 'Ocurrió un error inesperado. Inténtalo de nuevo.'

  // Submit Olvidé Contraseña: el backend envía el correo con Resend.
  const onForgotSubmit = async (data: ForgotFormData) => {
    setIsLoading(true)
    setAuthError(null)
    setResendNotification(null)
    try {
      await solicitarRecuperacion(data.email)
      setSentEmail(data.email)
      setCurrentStep('forgot-success')
    } catch (err) {
      setAuthError(mensajeDe(err))
    } finally {
      setIsLoading(false)
    }
  }

  // Accion Reenviar Correo (UX optimizada sin alert del navegador)
  const handleResendCode = async () => {
    setIsResending(true)
    setResendNotification(null)
    setAuthError(null)
    try {
      await solicitarRecuperacion(sentEmail)
      setResendNotification('Enlace de recuperación reenviado con éxito a tu correo.')
    } catch (err) {
      setAuthError(mensajeDe(err))
    } finally {
      setIsResending(false)
    }
  }

  // Submit nueva contraseña: con el uid y el token del enlace del correo.
  const onResetSubmit = async (data: ResetFormData) => {
    if (!restablecer) return
    setIsLoading(true)
    setAuthError(null)
    try {
      await restablecerContrasena(restablecer.uid, restablecer.token, data.password)
      setSuccessMessage('Contraseña actualizada. Ya puedes iniciar sesión.')
      irA('login')
    } catch (err) {
      setAuthError(mensajeDe(err))
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="w-full max-w-5xl mx-auto min-h-[620px] grid grid-cols-1 lg:grid-cols-12 rounded-3xl overflow-hidden border border-[#101820]/12 shadow-2xl bg-[#FAFAF8] dark:border-[#F7F1E8]/12 dark:bg-[#16202B]">
      {/* Panel decorativo de marca: solo en desktop. En móvil el formulario va limpio. */}
      <div className="hidden lg:col-span-5 lg:flex bg-[#101820] text-[#F7F1E8] p-8 sm:p-12 flex-col justify-between relative overflow-hidden">
        <div
          className="bf-grano pointer-events-none absolute inset-0"
          aria-hidden="true"
        />
        <div
          className="bf-patron-rayas pointer-events-none absolute inset-0 opacity-70"
          aria-hidden="true"
        />
        <div
          className="absolute -right-20 -bottom-20 w-80 h-80 bg-[#B3263B]/25 rounded-full blur-3xl pointer-events-none"
          aria-hidden="true"
        />
        <div
          className="absolute -left-20 -top-20 w-80 h-80 bg-[#174A7E]/30 rounded-full blur-3xl pointer-events-none"
          aria-hidden="true"
        />

        <div className="relative z-10 space-y-6">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 border border-[#F7F1E8]/40 bg-[#101820] rounded-lg flex items-center justify-center text-[#F7F1E8]">
              <Scissors className="size-5" aria-hidden="true" />
            </div>
            <div>
              <h1 className="font-[Barlow_Condensed] font-bold tracking-wider text-xl leading-none uppercase">
                BARBER<span className="text-[#E5283C]">FLOW</span>
              </h1>
              <p className="text-[10px] text-[#F7F1E8]/55 font-bold tracking-widest uppercase">
                OPERATING SYSTEM
              </p>
            </div>
          </div>

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#FAFAF8]/5 border border-[#F7F1E8]/20 text-[#F7F1E8]/80 text-xs font-semibold uppercase tracking-wider">
            <span className="w-2 h-2 rounded-full bg-[#10B981] animate-pulse"></span>
            GESTIÓN INTELIGENTE
          </div>
        </div>

        <div className="relative z-10 space-y-4 my-8">
          {/* Poste de barbería */}
          <div className="bf-poste h-[18px] w-32 rounded-sm" aria-hidden="true" />
          <h2 className="font-[Barlow_Condensed] text-4xl font-bold tracking-wide leading-tight uppercase">
            TU BARBERÍA, <br />
            <span className="text-[#E5283C]">BAJO CONTROL.</span>
          </h2>
          <p className="text-sm text-[#F7F1E8]/70 max-w-md leading-relaxed">
            Agenda, clientes, servicios y crecimiento. Todo lo que tu barbería necesita
            en un solo lugar.
          </p>
        </div>

        <div className="relative z-10 grid grid-cols-2 gap-4 pt-6 border-t border-[#F7F1E8]/15">
          <div>
            <span className="text-2xl font-[Barlow_Condensed] font-bold text-[#F7F1E8] block">
              +1.2K
            </span>
            <span className="text-xs text-[#F7F1E8]/60">Citas gestionadas</span>
          </div>
          <div>
            <span className="text-2xl font-[Barlow_Condensed] font-bold text-[#F7F1E8] block">
              98%
            </span>
            <span className="text-xs text-[#F7F1E8]/60">Clientes satisfechos</span>
          </div>
        </div>

        <div className="relative z-10 mt-8 text-[11px] text-[#F7F1E8]/45">
          © 2026 BarberFlow OS · Popayán, Colombia
        </div>
      </div>

      {/* Columna del formulario: composición simple y accesible en cualquier pantalla */}
      <div className="lg:col-span-7 p-6 sm:p-10 flex flex-col justify-center bg-[#FAFAF8] dark:bg-[#16202B]">
        <div className="max-w-md w-full mx-auto space-y-6">
          {/* VISTAS 1 & 2: LOGIN Y REGISTRO */}
          {(currentStep === 'login' || currentStep === 'register') && (
            <>
              <div className="space-y-1">
                <h2 className="font-[Barlow_Condensed] text-3xl font-bold text-[#101820] dark:text-[#F7F1E8] uppercase tracking-wide">
                  {currentStep === 'login' ? 'BIENVENIDO DE NUEVO' : 'CREA TU CUENTA'}
                </h2>
                <p className="text-sm text-[#101820]/65 dark:text-[#F7F1E8]/65">
                  {currentStep === 'login'
                    ? 'Ingresa tus credenciales para continuar.'
                    : 'Comienza a organizar tu barbería hoy.'}
                </p>
              </div>

              {/* Banner Verde de Éxito al Crear Cuenta */}
              {successMessage && currentStep === 'login' && (
                <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 rounded-2xl text-xs text-emerald-700 dark:text-emerald-300 font-medium flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="w-5 h-5 bg-emerald-500 text-white rounded-full flex items-center justify-center text-[10px] font-bold">
                      ✓
                    </span>
                    <span>{successMessage}</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setSuccessMessage(null)}
                    className="text-emerald-500 hover:text-emerald-700 text-xs font-bold p-1"
                  >
                    ✕
                  </button>
                </div>
              )}

              {/* Tabs Conmutadores */}
              <div className="grid grid-cols-2 p-1 bg-[#101820]/5 dark:bg-[#F7F1E8]/5 rounded-2xl">
                <button
                  type="button"
                  onClick={() => irA('login')}
                  aria-current={currentStep === 'login' ? 'page' : undefined}
                  className={`py-2.5 text-xs font-bold rounded-xl transition-all ${
                    currentStep === 'login'
                      ? 'bg-[#FAFAF8] dark:bg-[#101820] text-[#101820] dark:text-[#F7F1E8] shadow-sm'
                      : 'text-[#101820]/55 hover:text-[#101820] dark:text-[#F7F1E8]/55 dark:hover:text-[#F7F1E8]'
                  }`}
                >
                  Iniciar sesión
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSuccessMessage(null)
                    irA('register')
                  }}
                  aria-current={currentStep === 'register' ? 'page' : undefined}
                  className={`py-2.5 text-xs font-bold rounded-xl transition-all ${
                    currentStep === 'register'
                      ? 'bg-[#FAFAF8] dark:bg-[#101820] text-[#101820] dark:text-[#F7F1E8] shadow-sm'
                      : 'text-[#101820]/55 hover:text-[#101820] dark:text-[#F7F1E8]/55 dark:hover:text-[#F7F1E8]'
                  }`}
                >
                  Registrarme
                </button>
              </div>

              {authError && (
                <div className="p-3 bg-[#FBEEF0] dark:bg-[#E5283C]/10 border border-[#B3263B]/25 dark:border-[#E5283C]/30 rounded-xl text-xs text-[#B3263B] dark:text-[#E5283C] font-medium text-center">
                  {authError}
                </div>
              )}

              {/* Form INICIAR SESIÓN */}
              {currentStep === 'login' && (
                <form
                  onSubmit={loginForm.handleSubmit(onLoginSubmit)}
                  className="space-y-4"
                  noValidate
                >
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75">
                      Correo electrónico
                    </label>
                    <input
                      type="email"
                      placeholder="hola@thiagobarber.co"
                      {...loginForm.register('email')}
                      className={`w-full px-4 py-3 rounded-xl border text-sm transition-all outline-none focus:border-[#B3263B] focus:ring-2 focus:ring-[#B3263B]/25 dark:focus:border-[#E5283C] dark:focus:ring-[#E5283C]/25 ${
                        loginForm.formState.errors.email
                          ? 'border-[#B3263B] bg-[#B3263B]/5'
                          : 'border-[#101820]/15 bg-[#FAFAF8] text-[#101820] dark:border-[#F7F1E8]/15 dark:bg-[#101820]/40 dark:text-[#F7F1E8]'
                      }`}
                    />
                    {loginForm.formState.errors.email && (
                      <span className="text-xs text-[#B3263B] dark:text-[#E5283C] font-medium block">
                        {loginForm.formState.errors.email.message}
                      </span>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75">
                      Contraseña
                    </label>
                    <div className="relative flex items-center">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Mínimo 8 caracteres"
                        {...loginForm.register('password')}
                        className={`bf-sin-ojo-nativo w-full px-4 py-3 pr-12 rounded-xl border text-sm transition-all outline-none focus:border-[#B3263B] focus:ring-2 focus:ring-[#B3263B]/25 dark:focus:border-[#E5283C] dark:focus:ring-[#E5283C]/25 ${
                          loginForm.formState.errors.password
                            ? 'border-[#B3263B] bg-[#B3263B]/5'
                            : 'border-[#101820]/15 bg-[#FAFAF8] text-[#101820] dark:border-[#F7F1E8]/15 dark:bg-[#101820]/40 dark:text-[#F7F1E8]'
                        }`}
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2 p-2 rounded-xl bg-[#101820]/5 hover:bg-[#101820]/10 dark:bg-[#F7F1E8]/5 dark:hover:bg-[#FAFAF8]/10 text-[#101820]/55 hover:text-[#101820] dark:text-[#F7F1E8]/55 dark:hover:text-[#F7F1E8] transition-all"
                      >
                        {showPassword ? (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
                            <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
                            <path d="M6.61 6.61A13.52 13.52 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
                            <line x1="2" x2="22" y1="2" y2="22" />
                          </svg>
                        ) : (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        )}
                      </button>
                    </div>
                    {loginForm.formState.errors.password && (
                      <span className="text-xs text-[#B3263B] dark:text-[#E5283C] font-medium block">
                        {loginForm.formState.errors.password.message}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center justify-between text-xs pt-1">
                    <label className="flex items-center gap-2 text-[#101820]/70 dark:text-[#F7F1E8]/70 cursor-pointer">
                      <input
                        type="checkbox"
                        {...loginForm.register('rememberMe')}
                        className="rounded border-[#101820]/25 text-[#B3263B] dark:border-[#F7F1E8]/25 dark:text-[#E5283C] focus:ring-[#B3263B] dark:focus:ring-[#E5283C]"
                      />
                      Recordarme
                    </label>
                    <button
                      type="button"
                      onClick={() => {
                        setSuccessMessage(null)
                        setAuthError(null)
                        setCurrentStep('forgot')
                      }}
                      className="text-[#B3263B] hover:text-[#8f1e2f] dark:text-[#E5283C] dark:hover:text-[#f0a0ad] font-medium"
                    >
                      ¿Olvidaste tu contraseña?
                    </button>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full py-3.5 px-4 bg-[#B3263B] hover:bg-[#C93A4F] active:scale-95 text-[#F7F1E8] font-bold text-sm rounded-xl shadow-lg shadow-[#B3263B]/25 transition-all flex items-center justify-center gap-2 mt-4 disabled:opacity-60"
                  >
                    <span>{isLoading ? 'Cargando...' : 'Ingresar a BarberFlow'}</span>
                    <span>→</span>
                  </button>
                </form>
              )}

              {/* Form REGISTRARME */}
              {currentStep === 'register' && (
                <form
                  onSubmit={registerForm.handleSubmit(onRegisterSubmit)}
                  className="space-y-4"
                  noValidate
                >
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75">
                      Nombre completo
                    </label>
                    <input
                      type="text"
                      placeholder="Ej. Thiago Angulo"
                      {...registerForm.register('fullName')}
                      className={`w-full px-4 py-3 rounded-xl border text-sm transition-all outline-none focus:border-[#B3263B] focus:ring-2 focus:ring-[#B3263B]/25 dark:focus:border-[#E5283C] dark:focus:ring-[#E5283C]/25 ${
                        registerForm.formState.errors.fullName
                          ? 'border-[#B3263B] bg-[#B3263B]/5'
                          : 'border-[#101820]/15 bg-[#FAFAF8] text-[#101820] dark:border-[#F7F1E8]/15 dark:bg-[#101820]/40 dark:text-[#F7F1E8]'
                      }`}
                    />
                    {registerForm.formState.errors.fullName && (
                      <span className="text-xs text-[#B3263B] dark:text-[#E5283C] font-medium block">
                        {registerForm.formState.errors.fullName.message}
                      </span>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75">
                      Correo electrónico
                    </label>
                    <input
                      type="email"
                      placeholder="hola@thiagobarber.co"
                      {...registerForm.register('email')}
                      className={`w-full px-4 py-3 rounded-xl border text-sm transition-all outline-none focus:border-[#B3263B] focus:ring-2 focus:ring-[#B3263B]/25 dark:focus:border-[#E5283C] dark:focus:ring-[#E5283C]/25 ${
                        registerForm.formState.errors.email
                          ? 'border-[#B3263B] bg-[#B3263B]/5'
                          : 'border-[#101820]/15 bg-[#FAFAF8] text-[#101820] dark:border-[#F7F1E8]/15 dark:bg-[#101820]/40 dark:text-[#F7F1E8]'
                      }`}
                    />
                    {registerForm.formState.errors.email && (
                      <span className="text-xs text-[#B3263B] dark:text-[#E5283C] font-medium block">
                        {registerForm.formState.errors.email.message}
                      </span>
                    )}
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75">
                      Contraseña
                    </label>
                    <div className="relative flex items-center">
                      <input
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Mínimo 8 caracteres"
                        {...registerForm.register('password')}
                        className={`bf-sin-ojo-nativo w-full px-4 py-3 pr-12 rounded-xl border text-sm transition-all outline-none focus:border-[#B3263B] focus:ring-2 focus:ring-[#B3263B]/25 dark:focus:border-[#E5283C] dark:focus:ring-[#E5283C]/25 ${
                          registerForm.formState.errors.password
                            ? 'border-[#B3263B] bg-[#B3263B]/5'
                            : 'border-[#101820]/15 bg-[#FAFAF8] text-[#101820] dark:border-[#F7F1E8]/15 dark:bg-[#101820]/40 dark:text-[#F7F1E8]'
                        }`}
                      />
                      <button
                        type="button"
                        aria-label={
                          showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'
                        }
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-2 p-2 rounded-xl bg-[#101820]/5 hover:bg-[#101820]/10 dark:bg-[#F7F1E8]/5 dark:hover:bg-[#FAFAF8]/10 text-[#101820]/55 hover:text-[#101820] dark:text-[#F7F1E8]/55 dark:hover:text-[#F7F1E8] transition-all"
                      >
                        {showPassword ? (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
                            <path d="M10.73 5.08A10.43 10.43 0 0 1 12 5c7 0 10 7 10 7a13.16 13.16 0 0 1-1.67 2.68" />
                            <path d="M6.61 6.61A13.52 13.52 0 0 0 2 12s3 7 10 7a9.74 9.74 0 0 0 5.39-1.61" />
                            <line x1="2" x2="22" y1="2" y2="22" />
                          </svg>
                        ) : (
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                          >
                            <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
                            <circle cx="12" cy="12" r="3" />
                          </svg>
                        )}
                      </button>
                    </div>
                    {registerForm.formState.errors.password && (
                      <span className="text-xs text-[#B3263B] dark:text-[#E5283C] font-medium block">
                        {registerForm.formState.errors.password.message}
                      </span>
                    )}
                    <RequisitosContrasena contrasena={passwordRegistro ?? ''} />
                  </div>

                  <div className="flex items-center text-xs pt-1">
                    <label className="flex items-center gap-2 text-[#101820]/70 dark:text-[#F7F1E8]/70 cursor-pointer">
                      <input
                        type="checkbox"
                        {...registerForm.register('rememberMe')}
                        className="rounded border-[#101820]/25 text-[#B3263B] dark:border-[#F7F1E8]/25 dark:text-[#E5283C] focus:ring-[#B3263B] dark:focus:ring-[#E5283C]"
                      />
                      Recordarme
                    </label>
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full py-3.5 px-4 bg-[#B3263B] hover:bg-[#C93A4F] active:scale-95 text-[#F7F1E8] font-bold text-sm rounded-xl shadow-lg shadow-[#B3263B]/25 transition-all flex items-center justify-center gap-2 mt-4 disabled:opacity-60"
                  >
                    <span>{isLoading ? 'Creando cuenta...' : 'Crear mi cuenta'}</span>
                    <span>→</span>
                  </button>
                </form>
              )}
            </>
          )}

          {/* VISTA 3: RECUPERA TU CONTRASEÑA */}
          {currentStep === 'forgot' && (
            <div className="space-y-6">
              <button
                type="button"
                onClick={() => {
                  setAuthError(null)
                  irA('login')
                }}
                className="text-xs font-semibold text-[#101820]/70 hover:text-[#101820] dark:text-[#F7F1E8]/70 dark:hover:text-[#F7F1E8] flex items-center gap-1 transition-all"
              >
                <span>‹</span> Volver a iniciar sesión
              </button>

              <div className="space-y-1">
                <h2 className="font-[Barlow_Condensed] text-3xl font-bold text-[#101820] dark:text-[#F7F1E8] uppercase tracking-wide">
                  RECUPERA TU CONTRASEÑA
                </h2>
                <p className="text-xs text-[#101820]/65 dark:text-[#F7F1E8]/65">
                  Ingresa el correo asociado a tu cuenta y te enviaremos instrucciones
                  para restablecerla.
                </p>
              </div>

              <form
                onSubmit={forgotForm.handleSubmit(onForgotSubmit)}
                className="space-y-4"
                noValidate
              >
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75">
                    Correo electrónico
                  </label>
                  <input
                    type="email"
                    placeholder="hola@thiagobarber.co"
                    {...forgotForm.register('email')}
                    className={`w-full px-4 py-3 rounded-xl border text-sm transition-all outline-none focus:border-[#B3263B] focus:ring-2 focus:ring-[#B3263B]/25 dark:focus:border-[#E5283C] dark:focus:ring-[#E5283C]/25 ${
                      forgotForm.formState.errors.email
                        ? 'border-[#B3263B] bg-[#B3263B]/5'
                        : 'border-[#101820]/15 bg-[#FAFAF8] text-[#101820] dark:border-[#F7F1E8]/15 dark:bg-[#101820]/40 dark:text-[#F7F1E8]'
                    }`}
                  />
                  {forgotForm.formState.errors.email && (
                    <span className="text-xs text-[#B3263B] dark:text-[#E5283C] font-medium block">
                      {forgotForm.formState.errors.email.message}
                    </span>
                  )}
                </div>

                {authError && (
                  <div className="p-3 bg-[#FBEEF0] dark:bg-[#E5283C]/10 border border-[#B3263B]/25 dark:border-[#E5283C]/30 rounded-xl text-xs text-[#B3263B] dark:text-[#E5283C] font-medium text-center">
                    {authError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-3.5 px-4 bg-[#B3263B] hover:bg-[#C93A4F] active:scale-95 text-[#F7F1E8] font-bold text-sm rounded-xl shadow-lg shadow-[#B3263B]/25 transition-all flex items-center justify-center gap-2 mt-2 disabled:opacity-60"
                >
                  <span>
                    {isLoading ? 'Enviando...' : 'Enviar enlace de recuperación'}
                  </span>
                  <span>→</span>
                </button>
              </form>

              <div className="p-3 bg-[#101820]/5 dark:bg-[#F7F1E8]/5 rounded-xl text-[11px] text-[#101820]/65 dark:text-[#F7F1E8]/65 flex items-center gap-2 justify-center">
                <span>🛡️</span> Por seguridad, el enlace será válido durante 30 minutos.
              </div>
            </div>
          )}

          {/* VISTA 5: NUEVA CONTRASEÑA (llegas desde el enlace del correo) */}
          {currentStep === 'reset' && (
            <div className="space-y-6">
              <div className="space-y-1">
                <h2 className="font-[Barlow_Condensed] text-3xl font-bold text-[#101820] dark:text-[#F7F1E8] uppercase tracking-wide">
                  NUEVA CONTRASEÑA
                </h2>
                <p className="text-xs text-[#101820]/65 dark:text-[#F7F1E8]/65">
                  Elige una contraseña nueva para tu cuenta.
                </p>
              </div>

              <form
                onSubmit={resetForm.handleSubmit(onResetSubmit)}
                className="space-y-4"
                noValidate
              >
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75">
                    Nueva contraseña
                  </label>
                  <input
                    type="password"
                    autoComplete="new-password"
                    placeholder="Mínimo 8 caracteres"
                    {...resetForm.register('password')}
                    className={`w-full px-4 py-3 rounded-xl border text-sm transition-all outline-none focus:border-[#B3263B] focus:ring-2 focus:ring-[#B3263B]/25 dark:focus:border-[#E5283C] dark:focus:ring-[#E5283C]/25 ${
                      resetForm.formState.errors.password
                        ? 'border-[#B3263B] bg-[#B3263B]/5'
                        : 'border-[#101820]/15 bg-[#FAFAF8] text-[#101820] dark:border-[#F7F1E8]/15 dark:bg-[#101820]/40 dark:text-[#F7F1E8]'
                    }`}
                  />
                  {resetForm.formState.errors.password && (
                    <span className="text-xs text-[#B3263B] dark:text-[#E5283C] font-medium block">
                      {resetForm.formState.errors.password.message}
                    </span>
                  )}
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-[#101820]/75 dark:text-[#F7F1E8]/75">
                    Confirmar contraseña
                  </label>
                  <input
                    type="password"
                    autoComplete="new-password"
                    placeholder="Repite la contraseña"
                    {...resetForm.register('confirm')}
                    className={`w-full px-4 py-3 rounded-xl border text-sm transition-all outline-none focus:border-[#B3263B] focus:ring-2 focus:ring-[#B3263B]/25 dark:focus:border-[#E5283C] dark:focus:ring-[#E5283C]/25 ${
                      resetForm.formState.errors.confirm
                        ? 'border-[#B3263B] bg-[#B3263B]/5'
                        : 'border-[#101820]/15 bg-[#FAFAF8] text-[#101820] dark:border-[#F7F1E8]/15 dark:bg-[#101820]/40 dark:text-[#F7F1E8]'
                    }`}
                  />
                  {resetForm.formState.errors.confirm && (
                    <span className="text-xs text-[#B3263B] dark:text-[#E5283C] font-medium block">
                      {resetForm.formState.errors.confirm.message}
                    </span>
                  )}
                </div>

                {authError && (
                  <div className="p-3 bg-[#FBEEF0] dark:bg-[#E5283C]/10 border border-[#B3263B]/25 dark:border-[#E5283C]/30 rounded-xl text-xs text-[#B3263B] dark:text-[#E5283C] font-medium text-center">
                    {authError}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full py-3.5 px-4 bg-[#B3263B] hover:bg-[#C93A4F] active:scale-95 text-[#F7F1E8] font-bold text-sm rounded-xl shadow-lg shadow-[#B3263B]/25 transition-all flex items-center justify-center gap-2 mt-2 disabled:opacity-60"
                >
                  <span>{isLoading ? 'Guardando...' : 'Cambiar contraseña'}</span>
                  <span>→</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setAuthError(null)
                    setCurrentStep('forgot')
                  }}
                  className="text-xs text-[#B3263B] hover:text-[#8f1e2f] dark:text-[#E5283C] dark:hover:text-[#f0a0ad] font-semibold block mx-auto transition-all"
                >
                  ¿El enlace venció? Pide uno nuevo
                </button>
              </form>
            </div>
          )}

          {/* VISTA 4: REVISA TU CORREO (CONFIRMACIÓN MEJORADA CON TOAST INLINE) */}
          {currentStep === 'forgot-success' && (
            <div className="space-y-6 text-center">
              <div className="w-16 h-16 bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 rounded-full flex items-center justify-center mx-auto text-2xl font-bold">
                ✓
              </div>

              <div className="space-y-2">
                <h2 className="font-[Barlow_Condensed] text-3xl font-bold text-[#101820] dark:text-[#F7F1E8] uppercase tracking-wide">
                  REVISA TU CORREO
                </h2>
                <p className="text-xs text-[#101820]/65 dark:text-[#F7F1E8]/65 max-w-xs mx-auto">
                  Enviamos las instrucciones para restablecer tu contraseña a{' '}
                  <strong className="text-[#101820] dark:text-[#F7F1E8]">
                    {sentEmail || 'tu correo'}
                  </strong>
                  .
                </p>
              </div>

              {/* Mensaje Inline elegante al dar clic en Reenviar (reemplaza el alert feo) */}
              {resendNotification && (
                <div className="p-3 bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 rounded-2xl text-xs text-emerald-700 dark:text-emerald-300 font-medium flex items-center justify-between">
                  <span>{resendNotification}</span>
                  <button
                    type="button"
                    onClick={() => setResendNotification(null)}
                    className="text-emerald-500 hover:text-emerald-700 text-xs font-bold p-1"
                  >
                    ✕
                  </button>
                </div>
              )}

              <button
                type="button"
                onClick={() => irA('login')}
                className="w-full py-3.5 px-4 bg-[#B3263B] hover:bg-[#C93A4F] active:scale-95 text-[#F7F1E8] font-bold text-sm rounded-xl shadow-lg shadow-[#B3263B]/25 transition-all mt-4"
              >
                Volver a iniciar sesión
              </button>

              {/* Enlace de Reenviar Código Estilizado */}
              {authError && (
                <div className="p-3 bg-[#FBEEF0] dark:bg-[#E5283C]/10 border border-[#B3263B]/25 dark:border-[#E5283C]/30 rounded-xl text-xs text-[#B3263B] dark:text-[#E5283C] font-medium">
                  {authError}
                </div>
              )}

              <button
                type="button"
                disabled={isResending}
                onClick={() => void handleResendCode()}
                className="text-xs text-[#B3263B] hover:text-[#8f1e2f] dark:text-[#E5283C] dark:hover:text-[#f0a0ad] font-semibold block mx-auto transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isResending ? 'Reenviando enlace...' : 'No recibí el correo, reenviar'}
              </button>
            </div>
          )}

          <p className="text-[11px] text-center text-[#101820]/50 dark:text-[#F7F1E8]/50 pt-2">
            Al continuar aceptas los{' '}
            <a
              href="#terms"
              className="underline hover:text-[#B3263B] dark:hover:text-[#E5283C]"
            >
              Términos y condiciones
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}
