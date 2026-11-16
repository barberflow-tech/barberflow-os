"""Concurrencia real de la edicion de horarios contra PostgreSQL (SCRUM-72).

Usan django_db(transaction=True): cada hilo abre su propia conexion y sus
transacciones hacen COMMIT de verdad (ver test_concurrencia_reprogramar_cita.py).
Editar un horario bloquea la fila del barbero, el mismo recurso que bloquean la
reserva y la reprogramacion, asi que se ejecutan de una en una.
"""

import threading
from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.db import connection
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.barberos import services_horarios as horarios
from apps.barberos.jornada import ZONA_HORARIA_BARBERIA
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.models import Servicio
from apps.citas import services
from apps.citas.models import Cita

ESPERA_MAXIMA = 15


def hora_local(dias: int, hora: int, minuto: int = 0) -> datetime:
    hoy = timezone.now().astimezone(ZONA_HORARIA_BARBERIA)
    dia = (hoy + timedelta(days=dias)).date()
    return datetime.combine(dia, time(hora, minuto), tzinfo=ZONA_HORARIA_BARBERIA)


def ejecutar_a_la_vez(*operaciones) -> list[object]:
    """Corre cada operacion en su hilo, soltadas a la vez; devuelve resultados.

    Las excepciones de negocio (de citas o de horarios) se devuelven como
    resultado para inspeccionarlas; cualquier otra deja el resultado en None y
    los assert de cada prueba la delatan.
    """
    barrera = threading.Barrier(len(operaciones))
    resultados: list[object] = [None] * len(operaciones)

    def correr(indice, operacion):
        try:
            barrera.wait()
            resultados[indice] = operacion()
        except (services.CitaError, horarios.HorarioError) as exc:
            resultados[indice] = exc
        finally:
            connection.close()

    hilos = [
        threading.Thread(target=correr, args=(i, op))
        for i, op in enumerate(operaciones)
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(ESPERA_MAXIMA)
    return resultados


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def barbero(barberia):
    barbero = Barbero.objects.create(barberia=barberia, name="Juan")
    for dia in range(7):
        HorarioBarbero.objects.create(
            barbero=barbero, weekday=dia, open_time=time(9), close_time=time(17)
        )
    return barbero


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=Decimal("25000.00"),
        duration_minutes=30,
    )


@pytest.fixture
def propietario(django_user_model):
    return django_user_model.objects.create_user(username="propietario", password="x")


def dia_semana(barbero, abre=(9, 0), cierra=(17, 0)) -> dict:
    return {"open_time": time(*abre), "close_time": time(*cierra)}


@pytest.mark.django_db(transaction=True)
def test_reprogramar_y_acortar_el_cierre_nunca_dejan_la_cita_fuera_de_jornada(
    barberia, barbero, servicio, propietario
):
    # Dado una cita a las 10:00 que el cliente mueve a las 16:30, y a la vez el
    # administrador adelanta el cierre de ese dia a las 16:00
    original = hora_local(5, 10)
    cita = Cita.objects.create(
        barberia=barberia,
        client=propietario,
        barber=barbero,
        service=servicio,
        start_at=original,
        end_at=original + timedelta(minutes=30),
        price=servicio.price,
    )
    weekday = original.weekday()

    resultados = ejecutar_a_la_vez(
        lambda: services.reprogramar_cita(
            cita_id=cita.pk, usuario=propietario, nuevo_inicio=hora_local(5, 16, 30)
        ),
        lambda: horarios.definir_horario_dia(
            barbero_id=barbero.pk,
            barberia=barberia,
            weekday=weekday,
            datos=dia_semana(barbero, cierra=(16, 0)),
        ),
    )

    # Entonces se aplica solo una de las dos, en cualquier orden
    reprogramo = isinstance(resultados[0], Cita)
    acorto = isinstance(resultados[1], tuple)
    assert reprogramo != acorto
    if reprogramo:
        assert isinstance(resultados[1], horarios.CitasAfectadasError)
    else:
        assert isinstance(resultados[0], services.HorarioInvalidoError)
    # ...y la cita nunca queda fuera de la jornada vigente
    cita.refresh_from_db()
    cierre = HorarioBarbero.objects.get(barbero=barbero, weekday=weekday).close_time
    assert cita.end_at.astimezone(ZONA_HORARIA_BARBERIA).time() <= cierre


@pytest.mark.django_db(transaction=True)
def test_dos_administradores_editando_la_semana_dejan_un_horario_completo(
    barberia, barbero
):
    # Dado dos administradores que reemplazan la semana a la vez
    semana_a = [
        {"weekday": d, **dia_semana(barbero, (9, 0), (17, 0))} for d in range(5)
    ]
    semana_b = [
        {"weekday": d, **dia_semana(barbero, (10, 0), (18, 0))} for d in range(5)
    ]

    resultados = ejecutar_a_la_vez(
        lambda: horarios.reemplazar_horario_semanal(
            barbero_id=barbero.pk, barberia=barberia, dias=semana_a
        ),
        lambda: horarios.reemplazar_horario_semanal(
            barbero_id=barbero.pk, barberia=barberia, dias=semana_b
        ),
    )

    # Entonces ninguna fallo y el resultado es una de las dos semanas, sin mezclar
    assert all(isinstance(r, tuple) for r in resultados)
    guardados = HorarioBarbero.objects.filter(barbero=barbero)
    assert sorted(guardados.values_list("weekday", flat=True)) == [0, 1, 2, 3, 4]
    assert len({(h.open_time, h.close_time) for h in guardados}) == 1
