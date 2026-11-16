"""Servicios de horarios del barbero (HU-08 / SCRUM-72).

Cubre las validaciones V1-V5 y V9-V10 del diseno: formato del turno y del
descanso, atomicidad, aislamiento por barberia y proteccion de citas futuras.
La concurrencia vive en test_concurrencia_horarios.py (exige transaction=True).
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.barberos import services_horarios as horarios
from apps.barberos.jornada import ZONA_HORARIA_BARBERIA
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.models import Servicio
from apps.citas.models import Cita
from apps.citas.services import obtener_slots_libres

LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO = range(6)


def dia(weekday, abre=(9, 0), cierra=(17, 0), descanso=None) -> dict:
    """Un dia del payload; `descanso` es ((hora, minuto), duracion) o None."""
    datos = {
        "weekday": weekday,
        "open_time": time(*abre),
        "close_time": time(*cierra),
    }
    if descanso is not None:
        (hora, minuto), duracion = descanso
        datos["break_start"] = time(hora, minuto)
        datos["break_duration_minutes"] = duracion
    return datos


def sin_weekday(datos: dict) -> dict:
    return {campo: valor for campo, valor in datos.items() if campo != "weekday"}


def semana_lunes_a_viernes() -> list[dict]:
    return [dia(weekday) for weekday in range(5)]


def proxima_fecha(weekday: int, desde_dias: int = 3):
    """Primer dia local con ese `weekday` a `desde_dias` o mas de hoy."""
    fecha = timezone.now().astimezone(ZONA_HORARIA_BARBERIA).date()
    fecha += timedelta(days=desde_dias)
    while fecha.weekday() != weekday:
        fecha += timedelta(days=1)
    return fecha


def inicio_local(fecha, hora: int, minuto: int = 0) -> datetime:
    return datetime.combine(fecha, time(hora, minuto), tzinfo=ZONA_HORARIA_BARBERIA)


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def otra_barberia():
    return Barberia.objects.create(name="Barberia Norte")


@pytest.fixture
def barbero(barberia):
    return Barbero.objects.create(barberia=barberia, name="Thiago")


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte clasico",
        price=Decimal("25000.00"),
        duration_minutes=30,
    )


@pytest.fixture
def cliente(django_user_model):
    return django_user_model.objects.create_user(username="cliente", password="x")


def crear_cita(barbero, servicio, inicio, cliente=None, **extra) -> Cita:
    if cliente is None:
        extra.setdefault("contact_name", "Visitante")
        extra.setdefault("contact_phone", "3001234567")
    return Cita.objects.create(
        barberia=barbero.barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=servicio.duration_minutes),
        price=servicio.price,
        **extra,
    )


def configurar(barbero, *dias) -> None:
    """Deja el horario del barbero con exactamente `dias` (sin validar)."""
    for datos in dias:
        HorarioBarbero.objects.create(barbero=barbero, **datos)


def guardar_semana(barbero, barberia, dias) -> None:
    horarios.reemplazar_horario_semanal(
        barbero_id=barbero.pk, barberia=barberia, dias=dias
    )


# --------------------------------------------------------------------------- #
# Validacion de un dia (V1-V4)                                                #
# --------------------------------------------------------------------------- #


def test_validar_horario_valido_no_tiene_errores():
    errores = horarios.validar_horario_dia(
        **sin_weekday(dia(LUNES, descanso=((13, 0), 60)))
    )
    assert errores == {}


def test_rechazar_cierre_anterior_a_apertura():
    errores = horarios.validar_horario_dia(**sin_weekday(dia(LUNES, (17, 0), (9, 0))))
    assert errores == {"close_time": ["El cierre debe ser posterior a la apertura."]}


def test_rechazar_cierre_igual_a_apertura():
    errores = horarios.validar_horario_dia(**sin_weekday(dia(LUNES, (9, 0), (9, 0))))
    assert "close_time" in errores


def test_rechazar_descanso_sin_duracion():
    errores = horarios.validar_horario_dia(
        open_time=time(9), close_time=time(17), break_start=time(13)
    )
    assert "break_duration_minutes" in errores


def test_rechazar_duracion_de_descanso_sin_hora_de_inicio():
    errores = horarios.validar_horario_dia(
        open_time=time(9), close_time=time(17), break_duration_minutes=60
    )
    assert "break_start" in errores


@pytest.mark.parametrize("duracion", [15, 45, 90])
def test_rechazar_descanso_que_no_dura_30_o_60_minutos(duracion):
    errores = horarios.validar_horario_dia(
        open_time=time(9),
        close_time=time(17),
        break_start=time(13),
        break_duration_minutes=duracion,
    )
    assert errores == {
        "break_duration_minutes": ["El descanso debe durar 30 o 60 minutos."]
    }


def test_rechazar_descanso_que_termina_despues_del_cierre():
    errores = horarios.validar_horario_dia(
        open_time=time(9),
        close_time=time(17),
        break_start=time(16, 30),
        break_duration_minutes=60,
    )
    assert errores == {
        "break_start": ["El descanso debe estar dentro del horario laboral."]
    }


def test_rechazar_descanso_que_empieza_antes_de_la_apertura():
    errores = horarios.validar_horario_dia(
        open_time=time(9),
        close_time=time(17),
        break_start=time(8, 30),
        break_duration_minutes=30,
    )
    assert "break_start" in errores


def test_rechazar_descanso_que_da_la_vuelta_a_medianoche():
    errores = horarios.validar_horario_dia(
        open_time=time(0, 0),
        close_time=time(23, 30),
        break_start=time(23, 30),
        break_duration_minutes=60,
    )
    assert "break_start" in errores


@pytest.mark.parametrize(
    "abre, cierra, inicio_descanso, duracion",
    [
        ((9, 0), (17, 0), (9, 0), 30),  # el descanso empieza justo en la apertura
        ((9, 0), (13, 30), (13, 0), 30),  # termina justo en el cierre
        ((9, 0), (10, 0), (9, 0), 60),  # ocupa todo el turno
    ],
)
def test_aceptar_descanso_pegado_a_los_bordes_del_turno(
    abre, cierra, inicio_descanso, duracion
):
    errores = horarios.validar_horario_dia(
        open_time=time(*abre),
        close_time=time(*cierra),
        break_start=time(*inicio_descanso),
        break_duration_minutes=duracion,
    )
    assert errores == {}


def test_aceptar_turno_minimo_de_30_minutos():
    errores = horarios.validar_horario_dia(open_time=time(9), close_time=time(9, 30))
    assert errores == {}


# --------------------------------------------------------------------------- #
# Semana completa                                                             #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_definir_semana_lunes_a_viernes_guarda_cinco_dias(barbero, barberia):
    resultado, guardados = horarios.reemplazar_horario_semanal(
        barbero_id=barbero.pk, barberia=barberia, dias=semana_lunes_a_viernes()
    )

    assert resultado == barbero
    assert [h.weekday for h in guardados] == [0, 1, 2, 3, 4]
    assert HorarioBarbero.objects.filter(barbero=barbero).count() == 5
    lunes = HorarioBarbero.objects.get(barbero=barbero, weekday=LUNES)
    assert (lunes.open_time, lunes.close_time) == (time(9), time(17))


@pytest.mark.django_db
def test_reemplazar_semana_quita_los_dias_omitidos(barbero, barberia):
    guardar_semana(barbero, barberia, semana_lunes_a_viernes() + [dia(SABADO)])

    guardar_semana(barbero, barberia, [dia(LUNES), dia(MARTES)])

    dias = set(
        HorarioBarbero.objects.filter(barbero=barbero).values_list("weekday", flat=True)
    )
    assert dias == {LUNES, MARTES}


@pytest.mark.django_db
def test_reemplazar_semana_con_el_mismo_contenido_es_idempotente(barbero, barberia):
    semana = [dia(LUNES, descanso=((13, 0), 60)), dia(MARTES)]
    guardar_semana(barbero, barberia, semana)
    antes = list(
        HorarioBarbero.objects.filter(barbero=barbero).values_list("pk", "weekday")
    )

    guardar_semana(barbero, barberia, semana)

    despues = list(
        HorarioBarbero.objects.filter(barbero=barbero).values_list("pk", "weekday")
    )
    assert despues == antes


@pytest.mark.django_db
def test_reemplazar_semana_reactiva_un_dia_inactivo(barbero, barberia):
    configurar(barbero, {**dia(LUNES), "is_active": False})

    guardar_semana(barbero, barberia, [dia(LUNES)])

    assert HorarioBarbero.objects.get(barbero=barbero, weekday=LUNES).is_active


@pytest.mark.django_db
def test_semana_con_un_dia_invalido_no_guarda_nada(barbero, barberia):
    guardar_semana(barbero, barberia, [dia(LUNES), dia(MARTES)])

    with pytest.raises(horarios.SemanaInvalidaError) as error:
        guardar_semana(
            barbero,
            barberia,
            [dia(LUNES, (10, 0), (18, 0)), dia(MARTES, (17, 0), (9, 0))],
        )

    assert error.value.errores[0] == {}
    assert "close_time" in error.value.errores[1]
    lunes = HorarioBarbero.objects.get(barbero=barbero, weekday=LUNES)
    assert lunes.open_time == time(9)  # el dia valido tampoco se aplico
    assert HorarioBarbero.objects.filter(barbero=barbero).count() == 2


@pytest.mark.django_db
def test_rechazar_dia_repetido_en_la_semana(barbero, barberia):
    with pytest.raises(horarios.SemanaInvalidaError) as error:
        guardar_semana(barbero, barberia, [dia(LUNES), dia(LUNES)])

    assert error.value.errores[0] == {}
    assert "weekday" in error.value.errores[1]
    assert not HorarioBarbero.objects.filter(barbero=barbero).exists()


@pytest.mark.django_db
def test_rechazar_barbero_de_otra_barberia(barbero, otra_barberia):
    with pytest.raises(horarios.BarberoNoEncontradoError):
        guardar_semana(barbero, otra_barberia, [dia(LUNES)])
    assert not HorarioBarbero.objects.filter(barbero=barbero).exists()


@pytest.mark.django_db
def test_rechazar_barbero_inexistente(barberia):
    with pytest.raises(horarios.BarberoNoEncontradoError):
        horarios.reemplazar_horario_semanal(
            barbero_id=999999, barberia=barberia, dias=[dia(LUNES)]
        )


@pytest.mark.django_db
def test_rechazar_editar_horario_de_barbero_inactivo(barbero, barberia):
    barbero.is_active = False
    barbero.save()

    with pytest.raises(horarios.BarberoInactivoError):
        guardar_semana(barbero, barberia, [dia(LUNES)])


@pytest.mark.django_db
def test_obtener_horario_semanal_devuelve_los_dias_ordenados(barbero, barberia):
    guardar_semana(barbero, barberia, [dia(VIERNES), dia(LUNES)])

    resultado, dias = horarios.obtener_horario_semanal(
        barbero_id=barbero.pk, barberia=barberia
    )

    assert resultado == barbero
    assert [h.weekday for h in dias] == [LUNES, VIERNES]


@pytest.mark.django_db
def test_obtener_horario_semanal_no_muestra_dias_inactivos(barbero, barberia):
    configurar(barbero, dia(LUNES), {**dia(MARTES), "is_active": False})

    _, dias = horarios.obtener_horario_semanal(barbero_id=barbero.pk, barberia=barberia)

    assert [h.weekday for h in dias] == [LUNES]


@pytest.mark.django_db
def test_obtener_horario_semanal_de_otra_barberia_no_existe(barbero, otra_barberia):
    with pytest.raises(horarios.BarberoNoEncontradoError):
        horarios.obtener_horario_semanal(barbero_id=barbero.pk, barberia=otra_barberia)


@pytest.mark.django_db
def test_disponibilidad_refleja_el_horario_nuevo(barbero, barberia):
    guardar_semana(barbero, barberia, [dia(LUNES, descanso=((13, 0), 60))])
    lunes = proxima_fecha(LUNES)

    slots_30 = obtener_slots_libres(barbero=barbero, fecha=lunes, duracion_minutos=30)
    slots_60 = obtener_slots_libres(barbero=barbero, fecha=lunes, duracion_minutos=60)

    assert len(slots_30) == 14  # 16 de 30 min menos las 2 del descanso
    assert len(slots_60) == 7  # 8 de 60 min menos la del descanso
    assert (
        obtener_slots_libres(
            barbero=barbero, fecha=proxima_fecha(MARTES), duracion_minutos=30
        )
        == []
    )


# --------------------------------------------------------------------------- #
# Proteccion de citas futuras (V10)                                           #
# --------------------------------------------------------------------------- #


@pytest.fixture
def semana_base(barbero, barberia):
    guardar_semana(
        barbero,
        barberia,
        [dia(LUNES, descanso=((13, 0), 60)), dia(VIERNES, descanso=((13, 0), 60))],
    )


def conflictos_al_guardar(barbero, barberia, dias) -> list[dict]:
    with pytest.raises(horarios.CitasAfectadasError) as error:
        guardar_semana(barbero, barberia, dias)
    return error.value.conflictos


@pytest.mark.django_db
def test_quitar_un_dia_con_cita_futura_se_rechaza(
    barbero, barberia, servicio, semana_base
):
    cita = crear_cita(barbero, servicio, inicio_local(proxima_fecha(VIERNES), 10))

    conflictos = conflictos_al_guardar(barbero, barberia, [dia(LUNES)])

    assert conflictos == [
        {"cita_id": cita.pk, "inicio": cita.start_at, "motivo": "dia_no_laborable"}
    ]
    assert HorarioBarbero.objects.filter(barbero=barbero, weekday=VIERNES).exists()


@pytest.mark.django_db
def test_acortar_el_cierre_dejando_una_cita_fuera_se_rechaza(
    barbero, barberia, servicio, semana_base
):
    cita = crear_cita(barbero, servicio, inicio_local(proxima_fecha(LUNES), 16, 30))

    conflictos = conflictos_al_guardar(
        barbero, barberia, [dia(LUNES, cierra=(16, 0)), dia(VIERNES)]
    )

    assert [(c["cita_id"], c["motivo"]) for c in conflictos] == [
        (cita.pk, "fuera_de_jornada")
    ]
    assert HorarioBarbero.objects.get(
        barbero=barbero, weekday=LUNES
    ).close_time == time(17)


@pytest.mark.django_db
def test_cita_que_termina_justo_en_el_nuevo_cierre_no_es_conflicto(
    barbero, barberia, servicio, semana_base
):
    crear_cita(barbero, servicio, inicio_local(proxima_fecha(LUNES), 16, 0))

    guardar_semana(barbero, barberia, [dia(LUNES, cierra=(16, 30)), dia(VIERNES)])

    assert HorarioBarbero.objects.get(
        barbero=barbero, weekday=LUNES
    ).close_time == time(16, 30)


@pytest.mark.django_db
def test_cita_que_termina_un_minuto_despues_del_nuevo_cierre_es_conflicto(
    barbero, barberia, servicio, semana_base
):
    inicio = inicio_local(proxima_fecha(LUNES), 16, 0)
    cita = crear_cita(barbero, servicio, inicio)
    cita.end_at = inicio + timedelta(minutes=31)
    cita.save()

    conflictos = conflictos_al_guardar(
        barbero, barberia, [dia(LUNES, cierra=(16, 30)), dia(VIERNES)]
    )

    assert [c["motivo"] for c in conflictos] == ["fuera_de_jornada"]


@pytest.mark.django_db
def test_mover_el_descanso_sobre_una_cita_se_rechaza(
    barbero, barberia, servicio, semana_base
):
    cita = crear_cita(barbero, servicio, inicio_local(proxima_fecha(LUNES), 15, 0))

    conflictos = conflictos_al_guardar(
        barbero,
        barberia,
        [dia(LUNES, descanso=((15, 0), 60)), dia(VIERNES)],
    )

    assert [(c["cita_id"], c["motivo"]) for c in conflictos] == [
        (cita.pk, "en_descanso")
    ]


@pytest.mark.django_db
def test_cambio_que_no_afecta_ninguna_cita_se_guarda(
    barbero, barberia, servicio, semana_base
):
    crear_cita(barbero, servicio, inicio_local(proxima_fecha(LUNES), 10))

    guardar_semana(
        barbero, barberia, [dia(LUNES, (8, 0), (18, 0), ((13, 0), 60)), dia(VIERNES)]
    )

    assert HorarioBarbero.objects.get(barbero=barbero, weekday=LUNES).open_time == time(
        8
    )


@pytest.mark.django_db
def test_cita_cancelada_no_bloquea_el_cambio(barbero, barberia, servicio, semana_base):
    crear_cita(
        barbero,
        servicio,
        inicio_local(proxima_fecha(VIERNES), 10),
        status=Cita.Estado.CANCELLED,
    )

    guardar_semana(barbero, barberia, [dia(LUNES)])

    assert not HorarioBarbero.objects.filter(barbero=barbero, weekday=VIERNES).exists()


@pytest.mark.django_db
def test_cita_pasada_no_bloquea_el_cambio(barbero, barberia, servicio, semana_base):
    pasada = timezone.now() - timedelta(days=2)
    crear_cita(barbero, servicio, pasada, status=Cita.Estado.COMPLETED)

    guardar_semana(barbero, barberia, [dia(LUNES, cierra=(10, 0), descanso=None)])

    assert HorarioBarbero.objects.get(
        barbero=barbero, weekday=LUNES
    ).close_time == time(10)


@pytest.mark.django_db
def test_cita_de_otro_barbero_no_bloquea_el_cambio(
    barbero, barberia, servicio, semana_base
):
    otro = Barbero.objects.create(barberia=barberia, name="Andres")
    crear_cita(otro, servicio, inicio_local(proxima_fecha(VIERNES), 10))

    guardar_semana(barbero, barberia, [dia(LUNES)])

    assert not HorarioBarbero.objects.filter(barbero=barbero, weekday=VIERNES).exists()


@pytest.mark.django_db
def test_cita_de_un_cliente_con_cuenta_tambien_bloquea(
    barbero, barberia, servicio, semana_base, cliente
):
    crear_cita(barbero, servicio, inicio_local(proxima_fecha(VIERNES), 10), cliente)

    conflictos_al_guardar(barbero, barberia, [dia(LUNES)])


@pytest.mark.django_db
def test_el_dia_de_la_cita_se_mide_en_hora_de_la_barberia_no_en_utc(
    barbero, barberia, servicio, semana_base
):
    # 22:00 en Bogota ya es el dia siguiente en UTC: el dia que cuenta es el local.
    viernes = proxima_fecha(VIERNES)
    configurar(barbero, dia(SABADO, cierra=(23, 0)))
    crear_cita(barbero, servicio, inicio_local(viernes, 22, 0))
    HorarioBarbero.objects.filter(barbero=barbero, weekday=VIERNES).update(
        close_time=time(23, 0)
    )

    # Quitar el sabado (el dia UTC de la cita) no la afecta...
    guardar_semana(
        barbero,
        barberia,
        [dia(LUNES, descanso=((13, 0), 60)), dia(VIERNES, cierra=(23, 0))],
    )
    # ...pero quitar el viernes local si.
    conflictos = conflictos_al_guardar(barbero, barberia, [dia(LUNES)])
    assert [c["motivo"] for c in conflictos] == ["dia_no_laborable"]


# --------------------------------------------------------------------------- #
# Un solo dia                                                                 #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_definir_un_dia_nuevo_lo_crea(barbero, barberia):
    horario, creado = horarios.definir_horario_dia(
        barbero_id=barbero.pk,
        barberia=barberia,
        weekday=MARTES,
        datos=sin_weekday(dia(MARTES, descanso=((14, 0), 30))),
    )

    assert creado is True
    assert (horario.weekday, horario.break_start) == (MARTES, time(14))


@pytest.mark.django_db
def test_definir_un_dia_existente_lo_actualiza_sin_tocar_los_demas(barbero, barberia):
    guardar_semana(barbero, barberia, [dia(LUNES), dia(MARTES)])

    horario, creado = horarios.definir_horario_dia(
        barbero_id=barbero.pk,
        barberia=barberia,
        weekday=LUNES,
        datos=sin_weekday(dia(LUNES, (10, 0), (18, 0))),
    )

    assert creado is False
    assert horario.open_time == time(10)
    assert HorarioBarbero.objects.get(
        barbero=barbero, weekday=MARTES
    ).open_time == time(9)


@pytest.mark.django_db
def test_definir_un_dia_invalido_lo_rechaza_con_errores_por_campo(barbero, barberia):
    with pytest.raises(horarios.HorarioInvalidoError) as error:
        horarios.definir_horario_dia(
            barbero_id=barbero.pk,
            barberia=barberia,
            weekday=LUNES,
            datos=sin_weekday(dia(LUNES, (17, 0), (9, 0))),
        )

    assert "close_time" in error.value.errores
    assert not HorarioBarbero.objects.filter(barbero=barbero).exists()


@pytest.mark.django_db
def test_definir_un_dia_que_deja_una_cita_fuera_se_rechaza(
    barbero, barberia, servicio, semana_base
):
    crear_cita(barbero, servicio, inicio_local(proxima_fecha(LUNES), 16, 30))

    with pytest.raises(horarios.CitasAfectadasError):
        horarios.definir_horario_dia(
            barbero_id=barbero.pk,
            barberia=barberia,
            weekday=LUNES,
            datos=sin_weekday(dia(LUNES, cierra=(16, 0))),
        )


@pytest.mark.django_db
def test_definir_un_dia_de_otra_barberia_no_existe(barbero, otra_barberia):
    with pytest.raises(horarios.BarberoNoEncontradoError):
        horarios.definir_horario_dia(
            barbero_id=barbero.pk,
            barberia=otra_barberia,
            weekday=LUNES,
            datos=sin_weekday(dia(LUNES)),
        )


# --------------------------------------------------------------------------- #
# Eliminar un dia                                                             #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_eliminar_un_dia_sin_citas_lo_quita(barbero, barberia, semana_base):
    horarios.eliminar_horario_dia(
        barbero_id=barbero.pk, barberia=barberia, weekday=VIERNES
    )

    assert not HorarioBarbero.objects.filter(barbero=barbero, weekday=VIERNES).exists()
    assert HorarioBarbero.objects.filter(barbero=barbero, weekday=LUNES).exists()


@pytest.mark.django_db
def test_eliminar_un_dia_sin_horario_no_existe(barbero, barberia, semana_base):
    with pytest.raises(horarios.HorarioNoEncontradoError):
        horarios.eliminar_horario_dia(
            barbero_id=barbero.pk, barberia=barberia, weekday=MARTES
        )


@pytest.mark.django_db
def test_eliminar_un_dia_con_cita_futura_se_rechaza(
    barbero, barberia, servicio, semana_base
):
    crear_cita(barbero, servicio, inicio_local(proxima_fecha(VIERNES), 10))

    with pytest.raises(horarios.CitasAfectadasError):
        horarios.eliminar_horario_dia(
            barbero_id=barbero.pk, barberia=barberia, weekday=VIERNES
        )
    assert HorarioBarbero.objects.filter(barbero=barbero, weekday=VIERNES).exists()


@pytest.mark.django_db
def test_eliminar_un_dia_cuya_unica_cita_esta_cancelada_se_permite(
    barbero, barberia, servicio, semana_base
):
    crear_cita(
        barbero,
        servicio,
        inicio_local(proxima_fecha(VIERNES), 10),
        status=Cita.Estado.CANCELLED,
    )

    horarios.eliminar_horario_dia(
        barbero_id=barbero.pk, barberia=barberia, weekday=VIERNES
    )

    assert not HorarioBarbero.objects.filter(barbero=barbero, weekday=VIERNES).exists()


# --------------------------------------------------------------------------- #
# Restricciones de la base (ultima defensa)                                   #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db(transaction=True)
def test_la_base_rechaza_un_descanso_fuera_del_turno(barbero):
    with pytest.raises(IntegrityError), transaction.atomic():
        HorarioBarbero.objects.create(
            barbero=barbero,
            weekday=LUNES,
            open_time=time(9),
            close_time=time(17),
            break_start=time(16, 30),
            break_duration_minutes=60,
        )


@pytest.mark.django_db(transaction=True)
def test_la_base_rechaza_un_descanso_que_da_la_vuelta_a_medianoche(barbero):
    with pytest.raises(IntegrityError), transaction.atomic():
        HorarioBarbero.objects.create(
            barbero=barbero,
            weekday=LUNES,
            open_time=time(0),
            close_time=time(23, 30),
            break_start=time(23, 30),
            break_duration_minutes=60,
        )


@pytest.mark.django_db
def test_la_base_acepta_un_descanso_pegado_al_cierre(barbero):
    horario = HorarioBarbero.objects.create(
        barbero=barbero,
        weekday=LUNES,
        open_time=time(9),
        close_time=time(10),
        break_start=time(9),
        break_duration_minutes=60,
    )
    assert horario.updated_at is not None
