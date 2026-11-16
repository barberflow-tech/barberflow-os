"""Reprogramacion de citas por su propietario (HU-03 / SCRUM-52).

Cubre el servicio `reprogramar_cita` y el endpoint
POST /api/v1/appointments/{id}/reschedule. La concurrencia vive en
test_concurrencia_reprogramar_cita.py porque exige transaction=True.

Las horas se construyen en la hora local de la barberia (America/Bogota) con
dias de margen, para que la regla de 12 h no dependa de la hora en que corre
la prueba. Los bordes exactos de 12 h se prueban inyectando `ahora`.
"""

from datetime import datetime, time, timedelta
from datetime import timezone as zona_utc
from decimal import Decimal

import pytest
from django.db import DatabaseError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.models import Servicio
from apps.citas import services
from apps.citas.models import BloqueoAgenda, Cita

DOCE_HORAS = timedelta(hours=12)


def url_reprogramar(cita_id) -> str:
    return f"/api/v1/appointments/{cita_id}/reschedule"


def hora_local(dias: int, hora: int, minuto: int = 0) -> datetime:
    """Hora de pared en la barberia, `dias` despues de hoy (siempre con zona)."""
    hoy = timezone.now().astimezone(services.ZONA_HORARIA_BARBERIA)
    dia = (hoy + timedelta(days=dias)).date()
    return datetime.combine(
        dia, time(hora, minuto), tzinfo=services.ZONA_HORARIA_BARBERIA
    )


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def propietario(django_user_model):
    return django_user_model.objects.create_user(username="propietario", password="x")


@pytest.fixture
def otro_usuario(django_user_model):
    return django_user_model.objects.create_user(username="otro", password="x")


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
def horarios(barbero):
    """Jornada de 09:00 a 17:00 con descanso de 13:00 a 14:00, todos los dias."""
    for dia in range(7):
        HorarioBarbero.objects.create(
            barbero=barbero,
            weekday=dia,
            open_time=time(9, 0),
            close_time=time(17, 0),
            break_start=time(13, 0),
            break_duration_minutes=60,
        )


@pytest.fixture
def cita(propietario, barbero, servicio, horarios):
    """Cita PENDING del propietario, en 2 dias a las 10:00 (hora de Bogota)."""
    return crear_cita_en_bd(
        cliente=propietario,
        barbero=barbero,
        servicio=servicio,
        inicio=hora_local(2, 10),
    )


@pytest.fixture
def nuevo_inicio():
    """Franja libre y valida: en 3 dias a las 11:00 (hora de Bogota)."""
    return hora_local(3, 11)


def crear_cita_en_bd(
    *, cliente, barbero, servicio, inicio, estado=Cita.Estado.PENDING, **extra
) -> Cita:
    """Inserta una cita directo en BD, sin pasar por las reglas de reserva."""
    return Cita.objects.create(
        barberia=barbero.barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=servicio.duration_minutes),
        status=estado,
        price=servicio.price,
        **extra,
    )


def api_de(usuario) -> APIClient:
    api = APIClient()
    api.force_authenticate(user=usuario)
    return api


def reprogramar(cita, usuario, nuevo_inicio, **extra) -> Cita:
    return services.reprogramar_cita(
        cita_id=cita.pk, usuario=usuario, nuevo_inicio=nuevo_inicio, **extra
    )


# --- Regla de las 12 horas (sin base de datos) --------------------------------


def test_validar_anticipacion_minima_rechaza_exactamente_12_horas():
    ahora = datetime(2026, 11, 20, 8, 0, tzinfo=zona_utc.utc)

    with pytest.raises(services.ReprogramacionTardiaError):
        services.validar_anticipacion_minima(ahora + DOCE_HORAS, ahora)


def test_validar_anticipacion_minima_acepta_mas_de_12_horas():
    ahora = datetime(2026, 11, 20, 8, 0, tzinfo=zona_utc.utc)
    inicio = ahora + DOCE_HORAS + timedelta(seconds=1)

    services.validar_anticipacion_minima(inicio, ahora)  # no lanza


# --- Servicio reprogramar_cita: caso exitoso -------------------------------------


@pytest.mark.django_db
def test_reprogramar_cita_propietario(propietario, cita, nuevo_inicio):
    # Dado una cita activa con mas de 12 h de antelacion
    duracion = cita.end_at - cita.start_at

    # Cuando su propietario la mueve a otra hora
    resultado = reprogramar(cita, propietario, nuevo_inicio)

    # Entonces la misma cita queda en la nueva franja, con la misma duracion
    cita.refresh_from_db()
    assert resultado.pk == cita.pk
    assert cita.start_at == nuevo_inicio
    assert cita.end_at == nuevo_inicio + duracion


@pytest.mark.django_db
@pytest.mark.parametrize("estado", [Cita.Estado.PENDING, Cita.Estado.CONFIRMED])
def test_reprogramar_cita_conserva_estado_barbero_servicio_y_precio(
    propietario, barbero, servicio, horarios, nuevo_inicio, estado
):
    cita = crear_cita_en_bd(
        cliente=propietario,
        barbero=barbero,
        servicio=servicio,
        inicio=hora_local(2, 10),
        estado=estado,
    )

    reprogramar(cita, propietario, nuevo_inicio)

    cita.refresh_from_db()
    assert cita.status == estado
    assert cita.barber_id == barbero.pk
    assert cita.service_id == servicio.pk
    assert cita.price == servicio.price
    assert cita.cancelled_at is None
    assert cita.late_cancellation is False


@pytest.mark.django_db
def test_permitir_mover_la_cita_sobre_su_propia_franja(propietario, cita):
    # Dado una cita de 10:00 a 10:30
    # Cuando se mueve 15 min (10:15 a 10:45, cruzando su franja anterior)
    nuevo = cita.start_at + timedelta(minutes=15)
    reprogramar(cita, propietario, nuevo)

    # Entonces no choca consigo misma
    cita.refresh_from_db()
    assert cita.start_at == nuevo


@pytest.mark.django_db
def test_liberar_franja_anterior_al_reprogramar(
    propietario, otro_usuario, cita, barbero, servicio, nuevo_inicio
):
    inicio_anterior, fin_anterior = cita.start_at, cita.end_at
    assert Cita.objects.solapadas(barbero, inicio_anterior, fin_anterior).exists()

    # Cuando el propietario reprograma
    reprogramar(cita, propietario, nuevo_inicio)

    # Entonces la franja anterior queda libre y otro cliente puede reservarla
    assert not Cita.objects.solapadas(barbero, inicio_anterior, fin_anterior).exists()
    reservada = services.crear_cita(
        cliente=otro_usuario,
        barberia=barbero.barberia,
        barbero_id=barbero.pk,
        servicio_id=servicio.pk,
        inicio=inicio_anterior,
    )
    assert reservada.status == Cita.Estado.PENDING


@pytest.mark.django_db
def test_reservar_nueva_franja_la_deja_ocupada(
    propietario, otro_usuario, cita, barbero, servicio, nuevo_inicio
):
    reprogramar(cita, propietario, nuevo_inicio)

    # La franja nueva ya no se puede reservar (HU-02)
    with pytest.raises(services.FranjaNoDisponibleError):
        services.crear_cita(
            cliente=otro_usuario,
            barberia=barbero.barberia,
            barbero_id=barbero.pk,
            servicio_id=servicio.pk,
            inicio=nuevo_inicio,
        )


# Los bordes que SI caben: pegados a la apertura, al cierre y al descanso.
@pytest.mark.django_db
@pytest.mark.parametrize("hora,minuto", [(9, 0), (16, 30), (12, 30), (14, 0)])
def test_permitir_franja_pegada_a_los_bordes_de_la_jornada(
    propietario, cita, hora, minuto
):
    nuevo = hora_local(3, hora, minuto)

    reprogramar(cita, propietario, nuevo)

    cita.refresh_from_db()
    assert cita.start_at == nuevo


# --- Servicio reprogramar_cita: regla de las 12 horas ----------------------------


@pytest.mark.django_db
def test_rechazar_reprogramacion_menos_de_12_horas(propietario, cita, nuevo_inicio):
    # Dado una cita que empieza en 6 horas, aunque la nueva hora sea lejana
    # (la regla se mide contra la hora ORIGINAL)
    ahora = cita.start_at - timedelta(hours=6)
    original = (cita.start_at, cita.end_at)

    with pytest.raises(services.ReprogramacionTardiaError):
        reprogramar(cita, propietario, nuevo_inicio, ahora=ahora)

    # Entonces la cita no cambia
    cita.refresh_from_db()
    assert (cita.start_at, cita.end_at) == original


@pytest.mark.django_db
def test_rechazar_reprogramacion_exactamente_a_12_horas(
    propietario, cita, nuevo_inicio
):
    with pytest.raises(services.ReprogramacionTardiaError):
        reprogramar(cita, propietario, nuevo_inicio, ahora=cita.start_at - DOCE_HORAS)


@pytest.mark.django_db
def test_permitir_reprogramacion_con_mas_de_12_horas(propietario, cita, nuevo_inicio):
    ahora = cita.start_at - DOCE_HORAS - timedelta(seconds=1)

    reprogramar(cita, propietario, nuevo_inicio, ahora=ahora)

    cita.refresh_from_db()
    assert cita.start_at == nuevo_inicio


# --- Servicio reprogramar_cita: propietario --------------------------------------


@pytest.mark.django_db
def test_rechazar_reprogramacion_si_no_es_propietario(otro_usuario, cita, nuevo_inicio):
    original = (cita.start_at, cita.end_at)

    with pytest.raises(services.NoEsPropietarioError):
        reprogramar(cita, otro_usuario, nuevo_inicio)

    cita.refresh_from_db()
    assert (cita.start_at, cita.end_at) == original


@pytest.mark.django_db
def test_rechazar_reprogramacion_de_cita_de_visitante(
    propietario, barbero, servicio, horarios, nuevo_inicio
):
    cita = crear_cita_en_bd(
        cliente=None,
        barbero=barbero,
        servicio=servicio,
        inicio=hora_local(2, 10),
        contact_name="Visitante",
        contact_phone="3001234567",
    )

    with pytest.raises(services.NoEsPropietarioError):
        reprogramar(cita, propietario, nuevo_inicio)


@pytest.mark.django_db
def test_rechazar_reprogramacion_de_cita_inexistente(propietario, nuevo_inicio):
    with pytest.raises(services.CitaNoEncontradaError):
        services.reprogramar_cita(
            cita_id=999_999, usuario=propietario, nuevo_inicio=nuevo_inicio
        )


# --- Servicio reprogramar_cita: disponibilidad -----------------------------------


@pytest.mark.django_db
def test_rechazar_reprogramacion_a_franja_ocupada(
    propietario, otro_usuario, cita, barbero, servicio, nuevo_inicio
):
    # Dado que otro cliente ya tiene esa franja
    crear_cita_en_bd(
        cliente=otro_usuario, barbero=barbero, servicio=servicio, inicio=nuevo_inicio
    )
    original = (cita.start_at, cita.end_at)

    # Cuando el propietario intenta moverse ahi
    with pytest.raises(services.FranjaNoDisponibleError):
        reprogramar(cita, propietario, nuevo_inicio)

    # Entonces conserva su franja actual
    cita.refresh_from_db()
    assert (cita.start_at, cita.end_at) == original


@pytest.mark.django_db
def test_rechazar_reprogramacion_a_franja_parcialmente_ocupada(
    propietario, otro_usuario, cita, barbero, servicio, nuevo_inicio
):
    crear_cita_en_bd(
        cliente=otro_usuario, barbero=barbero, servicio=servicio, inicio=nuevo_inicio
    )

    with pytest.raises(services.FranjaNoDisponibleError):
        reprogramar(cita, propietario, nuevo_inicio + timedelta(minutes=15))


@pytest.mark.django_db
def test_ignorar_citas_canceladas_al_validar_disponibilidad(
    propietario, otro_usuario, cita, barbero, servicio, nuevo_inicio
):
    crear_cita_en_bd(
        cliente=otro_usuario,
        barbero=barbero,
        servicio=servicio,
        inicio=nuevo_inicio,
        estado=Cita.Estado.CANCELLED,
    )

    reprogramar(cita, propietario, nuevo_inicio)

    cita.refresh_from_db()
    assert cita.start_at == nuevo_inicio


@pytest.mark.django_db
@pytest.mark.parametrize(
    "hora,minuto",
    [
        (8, 30),  # empieza antes de abrir
        (16, 45),  # termina despues del cierre
        (13, 0),  # dentro del descanso
        (12, 45),  # cruza el inicio del descanso
        (13, 45),  # cruza el fin del descanso
    ],
)
def test_rechazar_reprogramacion_fuera_de_jornada_o_en_descanso(
    propietario, cita, hora, minuto
):
    original = cita.start_at

    with pytest.raises(services.HorarioInvalidoError):
        reprogramar(cita, propietario, hora_local(3, hora, minuto))

    cita.refresh_from_db()
    assert cita.start_at == original


@pytest.mark.django_db
def test_rechazar_reprogramacion_en_dia_sin_horario(
    propietario, cita, barbero, nuevo_inicio
):
    HorarioBarbero.objects.filter(
        barbero=barbero, weekday=nuevo_inicio.weekday()
    ).delete()

    with pytest.raises(services.HorarioInvalidoError):
        reprogramar(cita, propietario, nuevo_inicio)


@pytest.mark.django_db
def test_rechazar_reprogramacion_si_el_barbero_esta_inactivo(
    propietario, cita, barbero, nuevo_inicio
):
    Barbero.objects.filter(pk=barbero.pk).update(is_active=False)

    with pytest.raises(services.RecursoInactivoError):
        reprogramar(cita, propietario, nuevo_inicio)


# --- Servicio reprogramar_cita: hora pedida y estado -----------------------------


@pytest.mark.django_db
def test_rechazar_reprogramacion_a_hora_pasada(propietario, cita):
    with pytest.raises(services.HorarioInvalidoError):
        reprogramar(cita, propietario, timezone.now() - timedelta(hours=1))


@pytest.mark.django_db
def test_rechazar_reprogramacion_a_la_misma_hora(propietario, cita):
    with pytest.raises(services.HorarioInvalidoError):
        reprogramar(cita, propietario, cita.start_at)


@pytest.mark.django_db
def test_rechazar_reprogramacion_sin_zona_horaria(propietario, cita):
    sin_zona = datetime(2030, 1, 1, 11, 0)

    with pytest.raises(services.HorarioInvalidoError):
        reprogramar(cita, propietario, sin_zona)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "estado",
    [Cita.Estado.CANCELLED, Cita.Estado.COMPLETED, Cita.Estado.NO_SHOW],
)
def test_rechazar_reprogramacion_de_cita_en_estado_no_modificable(
    propietario, barbero, servicio, horarios, nuevo_inicio, estado
):
    cita = crear_cita_en_bd(
        cliente=propietario,
        barbero=barbero,
        servicio=servicio,
        inicio=hora_local(2, 10),
        estado=estado,
    )

    with pytest.raises(services.EstadoCitaInvalidoError):
        reprogramar(cita, propietario, nuevo_inicio)

    cita.refresh_from_db()
    assert cita.start_at == hora_local(2, 10)


# --- Endpoint POST /appointments/{id}/reschedule ---------------------------------


@pytest.mark.django_db
def test_retornar_200_y_cita_reprogramada_al_propietario(
    propietario, cita, nuevo_inicio
):
    response = api_de(propietario).post(
        url_reprogramar(cita.pk), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    assert response.status_code == 200
    assert response.data["id"] == cita.pk
    assert response.data["status"] == "PENDING"
    cita.refresh_from_db()
    assert cita.start_at == nuevo_inicio


@pytest.mark.django_db
def test_acepta_barra_final_al_reprogramar(propietario, cita, nuevo_inicio):
    response = api_de(propietario).post(
        url_reprogramar(cita.pk) + "/",
        {"start_at": nuevo_inicio.isoformat()},
        format="json",
    )

    assert response.status_code == 200


@pytest.mark.django_db
def test_retornar_400_si_faltan_menos_de_12_horas(
    propietario, barbero, servicio, horarios, nuevo_inicio
):
    # Dado una cita que empieza en 6 horas
    en_seis_horas = timezone.now() + timedelta(hours=6)
    cita = crear_cita_en_bd(
        cliente=propietario, barbero=barbero, servicio=servicio, inicio=en_seis_horas
    )

    response = api_de(propietario).post(
        url_reprogramar(cita.pk), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    # Entonces se rechaza con el codigo propio y la cita no cambia
    assert response.status_code == 400
    assert response.data["detail"].code == "reprogramacion_tardia"
    cita.refresh_from_db()
    assert cita.start_at == en_seis_horas


@pytest.mark.django_db
def test_retornar_401_si_no_hay_sesion(cita, nuevo_inicio):
    response = APIClient().post(
        url_reprogramar(cita.pk), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_retornar_403_si_no_es_propietario(otro_usuario, cita, nuevo_inicio):
    original = cita.start_at

    response = api_de(otro_usuario).post(
        url_reprogramar(cita.pk), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    assert response.status_code == 403
    cita.refresh_from_db()
    assert cita.start_at == original


@pytest.mark.django_db
def test_retornar_403_en_cita_de_visitante(
    propietario, barbero, servicio, horarios, nuevo_inicio
):
    cita = crear_cita_en_bd(
        cliente=None,
        barbero=barbero,
        servicio=servicio,
        inicio=hora_local(2, 10),
        contact_name="Visitante",
        contact_phone="3001234567",
    )

    response = api_de(propietario).post(
        url_reprogramar(cita.pk), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    assert response.status_code == 403


@pytest.mark.django_db
def test_retornar_404_si_la_cita_no_existe(propietario, nuevo_inicio):
    response = api_de(propietario).post(
        url_reprogramar(999_999), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_retornar_404_con_id_demasiado_grande(propietario, nuevo_inicio):
    response = api_de(propietario).post(
        url_reprogramar("9" * 25),
        {"start_at": nuevo_inicio.isoformat()},
        format="json",
    )

    assert response.status_code == 404


@pytest.mark.django_db
@pytest.mark.parametrize(
    "cuerpo",
    [{}, {"start_at": "no-es-fecha"}, {"new_slot_id": 123}],
    ids=["vacio", "fecha_invalida", "campo_desconocido"],
)
def test_retornar_400_si_el_body_no_trae_un_start_at_valido(propietario, cita, cuerpo):
    original = cita.start_at

    response = api_de(propietario).post(url_reprogramar(cita.pk), cuerpo, format="json")

    assert response.status_code == 400
    assert "start_at" in response.data
    cita.refresh_from_db()
    assert cita.start_at == original


@pytest.mark.django_db
def test_retornar_409_si_la_franja_esta_ocupada(
    propietario, otro_usuario, cita, barbero, servicio, nuevo_inicio
):
    crear_cita_en_bd(
        cliente=otro_usuario, barbero=barbero, servicio=servicio, inicio=nuevo_inicio
    )
    original = cita.start_at

    response = api_de(propietario).post(
        url_reprogramar(cita.pk), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    assert response.status_code == 409
    assert response.data["detail"].code == "franja_no_disponible"
    cita.refresh_from_db()
    assert cita.start_at == original


@pytest.mark.django_db
def test_retornar_409_si_la_cita_esta_cancelada(propietario, cita, nuevo_inicio):
    Cita.objects.filter(pk=cita.pk).update(status=Cita.Estado.CANCELLED)

    response = api_de(propietario).post(
        url_reprogramar(cita.pk), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    assert response.status_code == 409
    assert response.data["detail"].code == "cita_no_modificable"


@pytest.mark.django_db
def test_retornar_400_si_la_hora_esta_fuera_de_jornada(propietario, cita):
    fuera_de_jornada = hora_local(3, 20)

    response = api_de(propietario).post(
        url_reprogramar(cita.pk),
        {"start_at": fuera_de_jornada.isoformat()},
        format="json",
    )

    assert response.status_code == 400
    assert "detail" in response.data


@pytest.mark.django_db(transaction=True)
def test_fallo_al_guardar_hace_rollback_y_retorna_500(
    propietario, cita, nuevo_inicio, monkeypatch
):
    # Dado que la BD falla justo despues de ejecutar el UPDATE
    original = (cita.start_at, cita.end_at)
    save_original = Cita.save

    def guardar_y_fallar(self, *args, **kwargs):
        save_original(self, *args, **kwargs)
        raise DatabaseError("fallo simulado durante el guardado")

    monkeypatch.setattr(Cita, "save", guardar_y_fallar)

    # Cuando el propietario reprograma
    response = api_de(propietario).post(
        url_reprogramar(cita.pk), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    # Entonces responde 500 en JSON y el ROLLBACK deja la cita en su franja
    assert response.status_code == 500
    assert response.data["detail"].code == "error_al_reprogramar_cita"
    cita.refresh_from_db()
    assert (cita.start_at, cita.end_at) == original


@pytest.mark.django_db
def test_rechazar_reprogramacion_a_franja_con_bloqueo_de_agenda(
    propietario, cita, barbero, nuevo_inicio
):
    # Dado que el administrador bloqueó esa franja (HU-04)
    BloqueoAgenda.objects.create(
        barber=barbero,
        start_at=nuevo_inicio,
        end_at=nuevo_inicio + timedelta(hours=1),
        reason="Capacitación",
    )
    original = (cita.start_at, cita.end_at)

    # Cuando el propietario intenta moverse ahí
    with pytest.raises(services.FranjaNoDisponibleError):
        reprogramar(cita, propietario, nuevo_inicio)

    # Entonces conserva su franja actual
    cita.refresh_from_db()
    assert (cita.start_at, cita.end_at) == original


@pytest.mark.django_db
def test_rechazar_reprogramacion_a_franja_que_toca_un_bloqueo_parcialmente(
    propietario, cita, barbero, nuevo_inicio
):
    BloqueoAgenda.objects.create(
        barber=barbero,
        start_at=nuevo_inicio + timedelta(minutes=15),
        end_at=nuevo_inicio + timedelta(hours=1),
        reason="Almuerzo",
    )

    with pytest.raises(services.FranjaNoDisponibleError):
        reprogramar(cita, propietario, nuevo_inicio)


@pytest.mark.django_db
def test_retornar_409_si_la_franja_esta_bloqueada(
    propietario, cita, barbero, nuevo_inicio
):
    BloqueoAgenda.objects.create(
        barber=barbero,
        start_at=nuevo_inicio,
        end_at=nuevo_inicio + timedelta(hours=1),
        reason="Capacitación",
    )
    original = cita.start_at

    response = api_de(propietario).post(
        url_reprogramar(cita.pk), {"start_at": nuevo_inicio.isoformat()}, format="json"
    )

    assert response.status_code == 409
    assert response.data["detail"].code == "franja_no_disponible"
    cita.refresh_from_db()
    assert cita.start_at == original
