import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas.models import Cita
from apps.citas.services import (
    FranjaNoDisponibleError,
    HorarioInvalidoError,
    RecursoInactivoError,
    crear_cita,
)


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def otra_barberia():
    return Barberia.objects.create(name="Barberia Norte")


@pytest.fixture
def cliente(django_user_model):
    return django_user_model.objects.create_user(username="cliente", password="x")


@pytest.fixture
def barbero(barberia):
    return Barbero.objects.create(barberia=barberia, name="Juan")


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=Decimal("25000.00"),
        duration_minutes=30,
    )


@pytest.fixture
def inicio():
    return (timezone.now() + timedelta(days=1)).replace(
        hour=15, minute=0, second=0, microsecond=0
    )


def reservar(cliente, barbero, servicio, inicio, barberia=None):
    return crear_cita(
        cliente=cliente,
        barberia=barberia or barbero.barberia,
        barbero_id=barbero.pk,
        servicio_id=servicio.pk,
        inicio=inicio,
    )


@pytest.mark.django_db
def test_reserva_valida_crea_cita_pending(cliente, barbero, servicio, inicio):
    # Dado un payload de reserva valido
    # Cuando se crea la cita dentro de la transaccion
    cita = reservar(cliente, barbero, servicio, inicio)

    # Entonces queda guardada en estado PENDING con su ID
    guardada = Cita.objects.get(pk=cita.pk)
    assert guardada.status == Cita.Estado.PENDING
    assert guardada.end_at == inicio + timedelta(minutes=30)
    assert guardada.price == Decimal("25000.00")
    assert guardada.client == cliente
    assert guardada.barberia == barbero.barberia


@pytest.mark.django_db
def test_barbero_de_otra_barberia_es_rechazado(
    cliente, barbero, servicio, otra_barberia, inicio
):
    # Dado un usuario de otra barberia que conoce el ID del barbero
    # Cuando intenta reservar con su propia barberia
    # Entonces se rechaza como recurso no disponible y no se crea la cita
    with pytest.raises(RecursoInactivoError):
        reservar(cliente, barbero, servicio, inicio, barberia=otra_barberia)
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_servicio_de_otra_barberia_es_rechazado(
    cliente, barbero, otra_barberia, inicio
):
    # Dado un servicio que pertenece a otra barberia
    ajeno = Servicio.objects.create(
        barberia=otra_barberia, name="Barba", price=1, duration_minutes=30
    )

    # Cuando se intenta combinar con un barbero propio
    # Entonces se rechaza y no se crea la cita
    with pytest.raises(RecursoInactivoError):
        reservar(cliente, barbero, ajeno, inicio)
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_bloquea_la_fila_del_barbero(cliente, barbero, servicio, inicio):
    # Dado un barbero, Cuando se reserva, Entonces se emite SELECT ... FOR UPDATE
    with CaptureQueriesContext(connection) as ctx:
        reservar(cliente, barbero, servicio, inicio)

    bloqueos = [q["sql"] for q in ctx.captured_queries if "FOR UPDATE" in q["sql"]]
    assert len(bloqueos) == 1
    assert '"barberos_barbero"' in bloqueos[0]


@pytest.mark.django_db
def test_franja_solapada_es_rechazada(cliente, barbero, servicio, inicio):
    # Dado una cita PENDING existente
    reservar(cliente, barbero, servicio, inicio)

    # Cuando se intenta reservar una franja que se cruza
    # Entonces se rechaza y no se crea una segunda cita
    with pytest.raises(FranjaNoDisponibleError):
        reservar(cliente, barbero, servicio, inicio + timedelta(minutes=15))
    assert Cita.objects.count() == 1


@pytest.mark.django_db
def test_franjas_contiguas_son_validas(cliente, barbero, servicio, inicio):
    reservar(cliente, barbero, servicio, inicio)

    reservar(cliente, barbero, servicio, inicio + timedelta(minutes=30))

    assert Cita.objects.count() == 2


@pytest.mark.django_db
def test_cita_cancelada_libera_la_franja(cliente, barbero, servicio, inicio):
    primera = reservar(cliente, barbero, servicio, inicio)
    Cita.objects.filter(pk=primera.pk).update(status=Cita.Estado.CANCELLED)

    reservar(cliente, barbero, servicio, inicio)

    assert Cita.objects.activas().count() == 1


@pytest.mark.django_db
def test_otro_barbero_no_bloquea(cliente, barbero, servicio, inicio):
    otro = Barbero.objects.create(barberia=barbero.barberia, name="Pedro")
    reservar(cliente, barbero, servicio, inicio)

    reservar(cliente, otro, servicio, inicio)

    assert Cita.objects.count() == 2


@pytest.mark.django_db
def test_fecha_pasada_es_rechazada(cliente, barbero, servicio):
    with pytest.raises(HorarioInvalidoError):
        reservar(cliente, barbero, servicio, timezone.now() - timedelta(hours=1))


@pytest.mark.django_db
def test_fecha_sin_zona_horaria_es_rechazada(cliente, barbero, servicio, inicio):
    with pytest.raises(HorarioInvalidoError):
        reservar(cliente, barbero, servicio, timezone.make_naive(inicio))


@pytest.mark.django_db
def test_barbero_inactivo_es_rechazado(cliente, barbero, servicio, inicio):
    Barbero.objects.filter(pk=barbero.pk).update(is_active=False)

    with pytest.raises(RecursoInactivoError):
        reservar(cliente, barbero, servicio, inicio)
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_servicio_inactivo_es_rechazado(cliente, barbero, servicio, inicio):
    Servicio.objects.filter(pk=servicio.pk).update(is_active=False)

    with pytest.raises(RecursoInactivoError):
        reservar(cliente, barbero, servicio, inicio)
    assert Cita.objects.count() == 0


@pytest.mark.django_db(transaction=True)
def test_fallo_tras_insertar_hace_rollback(
    cliente, barbero, servicio, inicio, monkeypatch
):
    # Dado que el guardado falla despues de ejecutar el INSERT
    save_original = Cita.save

    def guardar_y_fallar(self, *args, **kwargs):
        save_original(self, *args, **kwargs)
        raise RuntimeError("fallo simulado durante el guardado")

    monkeypatch.setattr(Cita, "save", guardar_y_fallar)

    # Cuando se intenta crear la cita
    with pytest.raises(RuntimeError):
        reservar(cliente, barbero, servicio, inicio)

    # Entonces la transaccion hace ROLLBACK y no queda ninguna cita
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_restriccion_impide_solapes_aunque_se_salte_el_servicio(
    cliente, barbero, servicio, inicio
):
    campos = dict(
        barberia=barbero.barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        price=1,
    )
    Cita.objects.create(
        start_at=inicio, end_at=inicio + timedelta(minutes=30), **campos
    )

    with pytest.raises(IntegrityError):
        Cita.objects.create(
            start_at=inicio + timedelta(minutes=10),
            end_at=inicio + timedelta(minutes=40),
            **campos,
        )


@pytest.mark.django_db(transaction=True)
def test_reservas_concurrentes_solo_una_gana(cliente, barbero, servicio, inicio):
    # Dado varios clientes que reservan la misma franja al mismo tiempo
    intentos = 5
    barrera = threading.Barrier(intentos)
    resultados: list[str] = []

    def reservar_en_paralelo():
        try:
            barrera.wait()
            reservar(cliente, barbero, servicio, inicio)
            resultados.append("ok")
        except FranjaNoDisponibleError:
            resultados.append("conflicto")
        finally:
            connection.close()

    hilos = [threading.Thread(target=reservar_en_paralelo) for _ in range(intentos)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join()

    # Entonces exactamente una reserva se crea y el resto recibe conflicto
    assert sorted(resultados) == ["conflicto"] * (intentos - 1) + ["ok"]
    assert Cita.objects.count() == 1
