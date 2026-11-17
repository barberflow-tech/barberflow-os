import { createClient } from '@supabase/supabase-js'

// Local: el stack de `supabase start`. Staging: las llaves de la nube van en Vercel, no en el repo.
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL ?? 'http://127.0.0.1:54321'
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY ?? ''

/**
 * Cliente de Supabase, o `null` si no hay llave configurada. Sin llave
 * `createClient` lanza al importarse y rompería toda página que lo use: Realtime
 * es una mejora, así que sin él la app funciona igual (las franjas se piden al
 * cambiar de día) y quien lo usa debe comprobar el `null`.
 */
export const supabase = SUPABASE_ANON_KEY
  ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
  : null
