import { createClient } from '@supabase/supabase-js'

// Local: el stack de `supabase start`. Staging: las llaves de la nube van en Vercel, no en el repo.
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL ?? 'http://127.0.0.1:54321'
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY ?? ''

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
