# Escrita a mano (SCRUM-54). No cambia el esquema de Django: `makemigrations
# --check --dry-run` no debe detectar cambios.
#
# Publica la tabla de citas en Supabase Realtime para que el frontend sepa, sin
# recargar, cuando una franja se libera (reprogramar o cancelar) o se ocupa.
#
# Solo viajan las columnas necesarias para esa senal. El cliente, su contacto y
# el precio NO se publican: la tabla no tiene RLS y la clave anonima de Supabase
# es publica, asi que cualquiera podria leer lo que se publique.
#
# Segura fuera de Supabase: si la publicacion `supabase_realtime` no existe
# (CI, Postgres sin `supabase start`) no hace nada. Idempotente y reversible.
# Requiere PostgreSQL 15+ para las listas de columnas (CI y Supabase usan 17).

from django.db import migrations

SQL_PUBLICAR = """
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'supabase_realtime') THEN
        -- Se quita y se vuelve a agregar para que la lista de columnas quede
        -- siempre igual, incluso si alguien la publico antes con todas.
        IF EXISTS (
            SELECT 1 FROM pg_publication_tables
            WHERE pubname = 'supabase_realtime'
              AND schemaname = 'public' AND tablename = 'citas_cita'
        ) THEN
            ALTER PUBLICATION supabase_realtime DROP TABLE public.citas_cita;
        END IF;
        ALTER PUBLICATION supabase_realtime
            ADD TABLE public.citas_cita (id, barber_id, start_at, end_at, status);
    END IF;
END
$$;
"""

SQL_DESPUBLICAR = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'public' AND tablename = 'citas_cita'
    ) THEN
        ALTER PUBLICATION supabase_realtime DROP TABLE public.citas_cita;
    END IF;
END
$$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("citas", "0004_cancelacion_cita"),
    ]

    operations = [
        migrations.RunSQL(sql=SQL_PUBLICAR, reverse_sql=SQL_DESPUBLICAR),
    ]
