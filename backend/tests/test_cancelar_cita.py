"""Cancelacion de citas por su propietario (HU-03 / SCRUM-52).

Cubre el servicio `cancelar_cita` y el endpoint
POST /api/v1/appointments/{id}/cancel. La concurrencia vive en
test_concurrencia_cancelar_cita.py porque exige transaction=True.
"""

from datetime import datetime, timedelta
from datetime import timezone as zona_utc
from decimal import Decimal

import pytest
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas import services
from apps.citas.models import Cita

DOCE_HORAS = timedelta(hours=12)


def url_cancelar(cita_id) -> str:
    return f"/api/v1/appointments/{cita_id}/cancel"


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
def inicio():
    # Siempre a mas de 15 h de "ahora": nunca cae en la ventana de 12 h.
    return (timezone.now() + timedelta(days=1)).replace(
        hour=15, minute=0, second=0, microsecond=0
    )


@pytest.fixture
def cita(propietario, barbero, servicio, inicio):
    return crear_cita_en_bd(
        cliente=propietario, barbero=barbero, servicio=servicio, inicio=inicio
    )


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


# --- Regla de las 12 horas (sin base de datos) --------------------------------


def test_tiene_anticipacion_minima_con_mas_de_12_horas():
    ahora = datetime(2026, 11, 20, 8, 0, tzinfo=zona_utc.utc)

    justo_12_horas = ahora + DOCE_HORAS
    mas_de_12_horas = justo_12_horas + timedelta(seconds=1)

    assert services.tiene_anticipacion_minima(justo_12_horas, ahora) is False
    assert services.tiene_anticipacion_minima(mas_de_12_horas, ahora) is True


def test_tiene_anticipacion_minima_rechaza_menos_de_12_horas_y_citas_pasadas():
    ahora = datetime(2026, 11, 20, 8, 0, tzinfo=zona_utc.utc)

    en_seis_horas = ahora + timedelta(hours=6)
    hace_una_hora = ahora - timedelta(hours=1)

    assert services.tiene_anticipacion_minima(en_seis_horas, ahora) is False
    assert services.tiene_anticipacion_minima(hace_una_hora, ahora) is False


# --- Servicio cancelar_cita ---------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("estado", [Cita.Estado.PENDING, Cita.Estado.CONFIRMED])
def test_cancelar_cita_propietario(propietario, barbero, servicio, inicio, estado):
    # Dado una cita activa del cliente con mas de 12 h de antelacion
    cita = crear_cita_en_bd(
        cliente=propietario,
        barbero=barbero,
        servicio=servicio,
        inicio=inicio,
        estado=estado,
    )

    # Cuando su propietario la cancela
    resultado = services.cancelar_cita(cita_id=cita.pk, usuario=propietario)

    # Entonces queda CANCELLED con su fecha, sin marca de cancelacion tardia
    cita.refresh_from_db()
    assert resultado.pk == cita.pk
    assert cita.status == Cita.Estado.CANCELLED
    assert cita.cancelled_at is not None
    assert cita.late_cancellation is False


@pytest.mark.django_db
def test_liberar_franja_al_cancelar_permite_reservarla_de_nuevo(
    propietario, otro_usuario, cita, barbero, servicio, inicio
):
    # Dado que la franja esta ocupada por la cita
    assert Cita.objects.solapadas(barbero, inicio, cita.end_at).exists()

    # Cuando el propietario la cancela
    services.cancelar_cita(cita_id=cita.pk, usuario=propietario)

    # Entonces la franja queda libre y otro cliente puede reservarla (HU-02)
    assert not Cita.objects.solapadas(barbero, inicio, cita.end_at).exists()
    nueva = services.crear_cita(
        cliente=otro_usuario,
        barberia=barbero.barberia,
        barbero_id=barbero.pk,
        servicio_id=servicio.pk,
        inicio=inicio,
    )
    assert nueva.status == Cita.Estado.PENDING


@pytest.mark.django_db
def test_registrar_cancelacion_tardia_con_menos_de_12_horas(propietario, cita):
    # Dado una cita que empieza en 6 horas
    ahora = cita.start_at - timedelta(hours=6)

    # Cuando se cancela
    services.cancelar_cita(cita_id=cita.pk, usuario=propietario, ahora=ahora)

    # Entonces se cancela y queda registrada como tardia, con la hora de decision
    cita.refresh_from_db()
    assert cita.status == Cita.Estado.CANCELLED
    assert cita.late_cancellation is True
    assert cita.cancelled_at == ahora


@pytest.mark.django_db
def test_registrar_cancelacion_tardia_exactamente_a_12_horas(propietario, cita):
    # Dado el borde exacto: faltan 12 h justas (no "mas de 12 h")
    services.cancelar_cita(
        cita_id=cita.pk, usuario=propietario, ahora=cita.start_at - DOCE_HORAS
    )

    cita.refresh_from_db()
    assert cita.late_cancellation is True


@pytest.mark.django_db
def test_no_registrar_cancelacion_tardia_con_mas_de_12_horas(propietario, cita):
    # Dado que faltan 12 h y 1 s
    ahora = cita.start_at - DOCE_HORAS - timedelta(seconds=1)

    services.cancelar_cita(cita_id=cita.pk, usuario=propietario, ahora=ahora)

    cita.refresh_from_db()
    assert cita.status == Cita.Estado.CANCELLED
    assert cita.late_cancellation is False


@pytest.mark.django_db
def test_rechazar_cancelacion_si_no_es_propietario(otro_usuario, cita):
    with pytest.raises(services.NoEsPropietarioError):
        services.cancelar_cita(cita_id=cita.pk, usuario=otro_usuario)

    cita.refresh_from_db()
    assert cita.status == Cita.Estado.PENDING
    assert cita.cancelled_at is None


@pytest.mark.django_db
def test_rechazar_cancelacion_de_cita_de_visitante(
    propietario, barbero, servicio, inicio
):
    # Dado una cita de visitante sin cuenta: no tiene propietario posible
    cita = crear_cita_en_bd(
        cliente=None,
        barbero=barbero,
        servicio=servicio,
        inicio=inicio,
        contact_name="Visitante",
        contact_phone="3001234567",
    )

    with pytest.raises(services.NoEsPropietarioError):
        services.cancelar_cita(cita_id=cita.pk, usuario=propietario)


@pytest.mark.django_db
def test_rechazar_cancelacion_de_cita_inexistente(propietario):
    with pytest.raises(services.CitaNoEncontradaError):
        services.cancelar_cita(cita_id=999_999, usuario=propietario)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "estado",
    [Cita.Estado.CANCELLED, Cita.Estado.COMPLETED, Cita.Estado.NO_SHOW],
)
def test_rechazar_cancelacion_de_cita_en_estado_no_modificable(
    propietario, barbero, servicio, inicio, estado
):
    cita = crear_cita_en_bd(
        cliente=propietario,
        barbero=barbero,
        servicio=servicio,
        inicio=inicio,
        estado=estado,
    )

    with pytest.raises(services.EstadoCitaInvalidoError):
        services.cancelar_cita(cita_id=cita.pk, usuario=propietario)

    cita.refresh_from_db()
    assert cita.status == estado
    assert cita.cancelled_at is None


@pytest.mark.django_db
def test_no_sobrescribir_la_cancelacion_original_al_cancelar_dos_veces(
    propietario, cita
):
    primera = cita.start_at - timedelta(hours=6)
    services.cancelar_cita(cita_id=cita.pk, usuario=propietario, ahora=primera)

    with pytest.raises(services.EstadoCitaInvalidoError):
        services.cancelar_cita(
            cita_id=cita.pk, usuario=propietario, ahora=cita.start_at - DOCE_HORAS * 2
        )

    cita.refresh_from_db()
    assert cita.cancelled_at == primera
    assert cita.late_cancellation is True


@pytest.mark.django_db
def test_rechazar_cancelacion_de_cita_que_ya_inicio(propietario, cita):
    ahora = cita.start_at + timedelta(minutes=5)

    with pytest.raises(services.EstadoCitaInvalidoError):
        services.cancelar_cita(cita_id=cita.pk, usuario=propietario, ahora=ahora)

    cita.refresh_from_db()
    assert cita.status == Cita.Estado.PENDING
    assert cita.late_cancellation is False


@pytest.mark.django_db
def test_bd_rechaza_marca_tardia_en_cita_no_cancelada(cita):
    # Respaldo en BD: la marca de tardia solo existe en citas CANCELLED.
    with pytest.raises(IntegrityError), transaction.atomic():
        Cita.objects.filter(pk=cita.pk).update(late_cancellation=True)


# --- Endpoint POST /appointments/{id}/cancel -----------------------------------


@pytest.mark.django_db
def test_retornar_200_y_cita_cancelada_al_propietario(propietario, cita):
    response = api_de(propietario).post(url_cancelar(cita.pk))

    assert response.status_code == 200
    assert response.data["id"] == cita.pk
    assert response.data["status"] == "CANCELLED"
    assert response.data["late_cancellation"] is False
    assert response.data["cancelled_at"] is not None
    cita.refresh_from_db()
    assert cita.status == Cita.Estado.CANCELLED


@pytest.mark.django_db
def test_acepta_barra_final_al_cancelar(propietario, cita):
    response = api_de(propietario).post(url_cancelar(cita.pk) + "/")

    assert response.status_code == 200


@pytest.mark.django_db
def test_retornar_200_y_marca_tardia_con_menos_de_12_horas(
    propietario, barbero, servicio
):
    # Dado una cita que empieza en 6 horas
    cita = crear_cita_en_bd(
        cliente=propietario,
        barbero=barbero,
        servicio=servicio,
        inicio=timezone.now() + timedelta(hours=6),
    )

    response = api_de(propietario).post(url_cancelar(cita.pk))

    # Entonces se cancela y la respuesta avisa que fue tardia
    assert response.status_code == 200
    assert response.data["late_cancellation"] is True
    cita.refresh_from_db()
    assert cita.late_cancellation is True


@pytest.mark.django_db
def test_retornar_401_si_no_hay_sesion(cita):
    response = APIClient().post(url_cancelar(cita.pk))

    assert response.status_code == 401
    cita.refresh_from_db()
    assert cita.status == Cita.Estado.PENDING


@pytest.mark.django_db
def test_retornar_403_si_no_es_propietario(otro_usuario, cita):
    response = api_de(otro_usuario).post(url_cancelar(cita.pk))

    assert response.status_code == 403
    cita.refresh_from_db()
    assert cita.status == Cita.Estado.PENDING
    assert cita.cancelled_at is None


@pytest.mark.django_db
def test_retornar_403_en_cita_de_visitante(propietario, barbero, servicio, inicio):
    cita = crear_cita_en_bd(
        cliente=None,
        barbero=barbero,
        servicio=servicio,
        inicio=inicio,
        contact_name="Visitante",
        contact_phone="3001234567",
    )

    response = api_de(propietario).post(url_cancelar(cita.pk))

    assert response.status_code == 403


@pytest.mark.django_db
def test_retornar_404_si_la_cita_no_existe(propietario):
    response = api_de(propietario).post(url_cancelar(999_999))

    assert response.status_code == 404


@pytest.mark.django_db
def test_retornar_404_con_id_demasiado_grande(propietario):
    # Mas de 18 digitos no encaja en la ruta: 404, no un error de BD.
    response = api_de(propietario).post(url_cancelar("9" * 25))

    assert response.status_code == 404


@pytest.mark.django_db
def test_retornar_409_si_la_cita_ya_esta_cancelada(propietario, cita):
    api = api_de(propietario)
    assert api.post(url_cancelar(cita.pk)).status_code == 200

    response = api.post(url_cancelar(cita.pk))

    assert response.status_code == 409
    assert response.data["detail"].code == "cita_no_modificable"


@pytest.mark.django_db(transaction=True)
def test_fallo_al_guardar_hace_rollback_y_retorna_500(propietario, cita, monkeypatch):
    # Dado que la BD falla justo despues de ejecutar el UPDATE
    save_original = Cita.save

    def guardar_y_fallar(self, *args, **kwargs):
        save_original(self, *args, **kwargs)
        raise DatabaseError("fallo simulado durante el guardado")

    monkeypatch.setattr(Cita, "save", guardar_y_fallar)

    # Cuando el propietario cancela con menos de 12 h (cambia los tres campos)
    Cita.objects.filter(pk=cita.pk).update(start_at=timezone.now() + timedelta(hours=6))
    response = api_de(propietario).post(url_cancelar(cita.pk))

    # Entonces responde 500 en JSON y el ROLLBACK deja la cita intacta
    assert response.status_code == 500
    assert response.data["detail"].code == "error_al_cancelar_cita"
    cita.refresh_from_db()
    assert cita.status == Cita.Estado.PENDING
    assert cita.cancelled_at is None
    assert cita.late_cancellation is False
