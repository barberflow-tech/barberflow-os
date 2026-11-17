// Clases compartidas del wizard (y de las pantallas que lo usan).
// Paleta BarberFlow OS: grafito #101820 · marfil #F7F1E8 · rojo #B3263B ·
// azul #174A7E · oro #C9A227 (solo acentos en oscuro).

export const titulo =
  'font-[Barlow_Condensed] font-bold uppercase tracking-wide text-[#101820] dark:text-[#F7F1E8]'

export const tarjeta =
  'rounded-[14px] border border-[#101820]/10 bg-[#F7F1E8] text-left transition-all duration-200 hover:-translate-y-0.5 hover:border-[#B3263B]/35 hover:shadow-[0_10px_26px_-20px_rgb(16_24_32_/_45%)] dark:border-[#F7F1E8]/12 dark:bg-[#16202B] dark:hover:border-[#E5283C]/45'

export const tarjetaActiva =
  'border-[#B3263B] bg-[#FBEEF0] shadow-[0_10px_26px_-20px_rgb(179_38_59_/_60%)] hover:border-[#B3263B] dark:border-[#E5283C] dark:bg-[#E5283C]/10 dark:hover:border-[#E5283C]'

export const botonPrimario =
  'inline-flex h-11 items-center justify-center gap-2 rounded-xl bg-[#B3263B] px-4 sm:px-5 text-sm font-semibold text-[#F7F1E8] shadow-md shadow-[#B3263B]/25 transition-colors hover:bg-[#C93A4F] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B3263B] disabled:cursor-not-allowed disabled:bg-slate-300 dark:bg-[#B3263B] dark:text-[#F7F1E8] dark:shadow-[#B3263B]/20 dark:hover:bg-[#C93A4F] dark:disabled:bg-white/20 dark:disabled:shadow-none disabled:shadow-none'

export const botonSecundario =
  'inline-flex h-11 items-center justify-center rounded-xl border border-[#101820]/15 bg-[#F7F1E8] px-4 sm:px-5 text-sm font-medium text-[#101820] transition-colors hover:bg-[#101820]/5 disabled:cursor-not-allowed disabled:text-[#101820]/40 dark:border-[#F7F1E8]/15 dark:bg-[#16202B] dark:text-[#F7F1E8] dark:hover:bg-[#F7F1E8]/5 dark:disabled:text-white/40'

export const campo =
  'h-12 w-full rounded-xl border border-[#101820]/15 bg-[#F7F1E8] px-4 text-sm font-semibold text-[#101820] outline-none transition-colors placeholder:font-normal placeholder:text-[#101820]/40 focus:border-[#B3263B] focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#B3263B] aria-invalid:border-[#B3263B] dark:border-[#F7F1E8]/15 dark:bg-[#16202B] dark:text-[#F7F1E8] dark:placeholder:text-[#F7F1E8]/40 dark:focus:border-[#E5283C] dark:aria-invalid:border-[#E5283C]'
