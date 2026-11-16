"""SCRUM-54: la tabla de citas se publica en Supabase Realtime sin datos personales.

El frontend usa el evento solo como senal para volver a pedir las franjas, asi
que basta con exponer que barbero y horario cambiaron. El cliente y su contacto
NO deben viajar por Realtime: la tabla no tiene RLS y la clave anonima es publica.
"""

import importlib

import pytest
from django.db import connection

migracion = importlib.import_module(
    "apps.citas.migrations.0005_publicar_citas_realtime"
)

PUBLICACION = "supabase_realtime"
TABLA = "citas_cita"
COLUMNAS_PERSONALES = {"client_id", "contact_name", "contact_phone", "price"}


def _crear_publicacion():
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE PUBLICATION {PUBLICACION}")


def _columnas_publicadas() -> set[str] | None:
    """None si la tabla no esta publicada."""
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT attnames FROM pg_publication_tables "
            "WHERE pubname = %s AND schemaname = 'public' AND tablename = %s",
            [PUBLICACION, TABLA],
        )
        fila = cursor.fetchone()
    return None if fila is None else set(fila[0])


def _ejecutar(sql: str):
    with connection.cursor() as cursor:
        cursor.execute(sql)


@pytest.mark.django_db
def test_sin_publicacion_de_realtime_la_migracion_no_falla():
    # Dado un Postgres sin Supabase (CI, desarrollo sin `supabase start`)
    # Cuando se aplica la migracion
    _ejecutar(migracion.SQL_PUBLICAR)

    # Entonces no hace nada y no lanza error
    with connection.cursor() as cursor:
        cursor.execute("SELECT 1 FROM pg_publication WHERE pubname = %s", [PUBLICACION])
        assert cursor.fetchone() is None


@pytest.mark.django_db
def test_publica_las_citas_solo_con_las_columnas_no_sensibles():
    # Dado Supabase con su publicacion de Realtime
    _crear_publicacion()

    # Cuando se aplica la migracion
    _ejecutar(migracion.SQL_PUBLICAR)

    # Entonces la tabla queda publicada solo con lo necesario para refrescar franjas
    columnas = _columnas_publicadas()
    assert columnas == {"id", "barber_id", "start_at", "end_at", "status"}
    assert columnas.isdisjoint(COLUMNAS_PERSONALES)


@pytest.mark.django_db
def test_la_migracion_se_puede_aplicar_dos_veces():
    _crear_publicacion()

    _ejecutar(migracion.SQL_PUBLICAR)
    _ejecutar(migracion.SQL_PUBLICAR)

    assert _columnas_publicadas() == {"id", "barber_id", "start_at", "end_at", "status"}


@pytest.mark.django_db
def test_revertir_quita_la_tabla_de_la_publicacion():
    _crear_publicacion()
    _ejecutar(migracion.SQL_PUBLICAR)

    _ejecutar(migracion.SQL_DESPUBLICAR)

    assert _columnas_publicadas() is None


@pytest.mark.django_db
def test_revertir_sin_publicacion_no_falla():
    _ejecutar(migracion.SQL_DESPUBLICAR)
