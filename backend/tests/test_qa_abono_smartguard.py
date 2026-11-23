"""SCRUM-96 / HU-20: QA del abono del 50 % (SmartGuard, parte 2).

Pruebas escritas antes de la implementacion (SUB-20-A y SUB-20-B). El cliente
reserva por POST /api/v1/appointments con JWT real; su RiskScore sale de un
historial real recalculado con la funcion de HU-19, y la pasarela de pruebas se
simula llamando al webhook con el token del entorno de pruebas.

Regla de SUB-20-A: RiskScore > 30 exige abono del 50 % del precio (redondeado
al peso, mitad hacia arriba); 30 o menos confirma sin abono. La franja queda
retenida 15 minutos; si el abono no llega, la cita se cancela sola, la franja
se libera y eso no cuenta como cancelacion tardia del cliente.

Sobre el umbral: con los pesos de HU-19 un historial real da 30 o 33 (32,5
redondeado), nunca 31. Por eso el borde se prueba con 30 y 33.

Las rutas, rutas de import y nombres de campos nuevos viven en CONTRATO.
"""

from datetime import datetime, timedelta
from datetime import time as hora_del_dia
from decimal import Decimal

import pytest
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.utils.module_loading import import_string
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.models import Cita
from apps.citas.services import ZONA_HORARIA_BARBERIA

pytestmark = pytest.mark.django_db

CITAS = "/api/v1/appointments"

CONTRATO = {
    "webhook": "/api/v1/deposits/webhook",
    "cabecera_token": "HTTP_X_WEBHOOK_TOKEN",
    "ajuste_token": "PASARELA_WEBHOOK_TOKEN",
    "recalcular_cliente": "apps.puntajes.services.recalcular_puntaje_cliente",
    "expirar_abonos": "apps.pagos.services_abono.expirar_abonos",
    "estado_espera": "AWAITING_DEPOSIT",
    "campo_abono": "deposit",
    "aprobado": "APPROVED",
    "rechazado": "REJECTED",
    "minutos_retencion": 15,
}


@pytest.fixture(autouse=True)
def limpiar_throttle():
    cache.clear()
    yield
    cache.clear()


def api_de(usuario):
    api = APIClient()
    if usuario is not None:
        token = AccessToken.for_user(usuario)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api


def hora_local(dias, hora, minuto=0):
    hoy = timezone.now().astimezone(ZONA_HORARIA_BARBERIA).date()
    return datetime.combine(
        hoy + timedelta(days=dias),
        hora_del_dia(hora, minuto),
        tzinfo=ZONA_HORARIA_BARBERIA,
    )


@pytest.fixture
def barbero():
    barbero = Barbero.objects.create(
        barberia=obtener_barberia_catalogo(), name="Thiago"
    )
    for dia in range(7):
        HorarioBarbero.objects.create(
            barbero=barbero,
            weekday=dia,
            open_time=hora_del_dia(0, 0),
            close_time=hora_del_dia(23, 59),
        )
    return barbero


def servicio_de(precio):
    return Servicio.objects.create(
        barberia=obtener_barberia_catalogo(),
        name=f"Servicio {precio}",
        price=Decimal(precio),
        duration_minutes=30,
    )


@pytest.fixture
def servicio():
    return servicio_de("50000")


def cliente_con_puntaje(make_user, barbero, servicio, puntaje, email):
    """Crea un cliente con un historial real que da ese RiskScore."""
    historiales = {
        0: [],
        30: [("CANCELLED", True, 10), ("CANCELLED", True, 20)],
        33: [("NO_SHOW", False, 10), ("CANCELLED", True, 120)],  # 25 + 7,5
        40: [("NO_SHOW", False, 10), ("CANCELLED", True, 20)],
    }
    cliente = make_user("cliente", email=email)
    for i, (estado, tardia, dias) in enumerate(historiales[puntaje]):
        inicio = timezone.now() - timedelta(days=dias, hours=i)
        Cita.objects.create(
            barberia=barbero.barberia,
            client=cliente,
            barber=barbero,
            service=servicio,
            start_at=inicio,
            end_at=inicio + timedelta(minutes=30),
            price=servicio.price,
            status=estado,
            late_cancellation=tardia,
        )
    import_string(CONTRATO["recalcular_cliente"])(cliente)
    return cliente


def reservar(api, barbero, servicio, inicio, **extra):
    return api.post(
        CITAS,
        {
            "barber": barbero.pk,
            "service": servicio.pk,
            "start_at": inicio.isoformat(),
            **extra,
        },
        format="json",
    )


def webhook(referencia, estado, token=None):
    token = token if token is not None else getattr(settings, CONTRATO["ajuste_token"])
    return APIClient().post(
        CONTRATO["webhook"],
        {"reference": referencia, "status": estado},
        format="json",
        **{CONTRATO["cabecera_token"]: token},
    )


def expirar(ahora):
    import_string(CONTRATO["expirar_abonos"])(ahora=ahora)


def visitante_reserva(barbero, servicio, inicio):
    return reservar(
        APIClient(),
        barbero,
        servicio,
        inicio,
        contact_name="Pedro Gomez",
        contact_phone="3001234567",
    )


# --- Umbral y monto -----------------------------------------------------------


@pytest.mark.parametrize(
    "puntaje,exige", [(0, False), (30, False), (33, True), (40, True)]
)
def test_umbral_del_abono(make_user, barbero, servicio, puntaje, exige):
    # Dado un cliente con ese RiskScore
    cliente = cliente_con_puntaje(
        make_user, barbero, servicio, puntaje, f"c{puntaje}@barberflow.test"
    )

    # Cuando confirma una reserva de $50.000
    respuesta = reservar(api_de(cliente), barbero, servicio, hora_local(2, 10))

    # Entonces se exige abono solo si supera 30
    assert respuesta.status_code == 201, respuesta.content
    datos = respuesta.json()
    if exige:
        assert datos["status"] == CONTRATO["estado_espera"]
        assert Decimal(str(datos[CONTRATO["campo_abono"]]["amount"])) == Decimal(
            "25000"
        )
    else:
        assert datos["status"] != CONTRATO["estado_espera"]
        assert not datos.get(CONTRATO["campo_abono"])


@pytest.mark.parametrize(
    "precio,abono",
    [
        ("50000", "25000"),  # ejemplo de la HU
        ("33333", "16667"),  # 16666,5 -> mitad hacia arriba
        ("25001", "12501"),  # 12500,5 -> mitad hacia arriba
        ("30000", "15000"),
    ],
)
def test_monto_del_abono_es_el_50_por_ciento_redondeado(
    make_user, barbero, servicio, precio, abono
):
    cliente = cliente_con_puntaje(make_user, barbero, servicio, 40, "r@barberflow.test")
    otro_servicio = servicio_de(precio)

    respuesta = reservar(api_de(cliente), barbero, otro_servicio, hora_local(2, 10))

    datos = respuesta.json()[CONTRATO["campo_abono"]]
    assert Decimal(str(datos["amount"])) == Decimal(abono)


def test_el_abono_informa_cuando_vence(make_user, barbero, servicio):
    cliente = cliente_con_puntaje(make_user, barbero, servicio, 40, "v@barberflow.test")
    antes = timezone.now()

    datos = reservar(api_de(cliente), barbero, servicio, hora_local(2, 10)).json()

    vence = datetime.fromisoformat(
        datos[CONTRATO["campo_abono"]]["expires_at"].replace("Z", "+00:00")
    )
    retencion = timedelta(minutes=CONTRATO["minutos_retencion"])
    assert antes + retencion <= vence <= timezone.now() + retencion


def test_visitante_sin_cuenta_reserva_sin_abono(barbero, servicio):
    respuesta = visitante_reserva(barbero, servicio, hora_local(2, 10))

    assert respuesta.status_code == 201
    assert respuesta.json()["status"] != CONTRATO["estado_espera"]


# --- Pago aprobado, rechazado y abandonado --------------------------------


@pytest.fixture
def reserva_con_abono(make_user, barbero, servicio):
    cliente = cliente_con_puntaje(make_user, barbero, servicio, 40, "a@barberflow.test")
    inicio = hora_local(2, 10)
    respuesta = reservar(api_de(cliente), barbero, servicio, inicio)
    assert respuesta.status_code == 201, respuesta.content
    datos = respuesta.json()
    return {
        "cliente": cliente,
        "inicio": inicio,
        "cita_id": datos["id"],
        "referencia": datos[CONTRATO["campo_abono"]]["reference"],
    }


def test_mientras_espera_el_abono_la_franja_esta_retenida(
    reserva_con_abono, barbero, servicio
):
    respuesta = visitante_reserva(barbero, servicio, reserva_con_abono["inicio"])

    assert respuesta.status_code == 409


def test_abono_aprobado_confirma_la_cita(reserva_con_abono):
    respuesta = webhook(reserva_con_abono["referencia"], CONTRATO["aprobado"])

    assert respuesta.status_code == 200
    cita = Cita.objects.get(pk=reserva_con_abono["cita_id"])
    assert cita.status == "CONFIRMED"


def test_la_cita_confirmada_se_ve_en_mis_citas(reserva_con_abono):
    webhook(reserva_con_abono["referencia"], CONTRATO["aprobado"])

    mis_citas = api_de(reserva_con_abono["cliente"]).get(CITAS).json()

    (cita,) = [c for c in mis_citas if c["id"] == reserva_con_abono["cita_id"]]
    assert cita["status"] == "CONFIRMED"


def test_abono_aprobado_dos_veces_no_cambia_nada(reserva_con_abono):
    # La pasarela puede reintentar el webhook
    assert webhook(reserva_con_abono["referencia"], "APPROVED").status_code == 200
    assert webhook(reserva_con_abono["referencia"], "APPROVED").status_code == 200

    assert Cita.objects.get(pk=reserva_con_abono["cita_id"]).status == "CONFIRMED"


def test_abono_rechazado_no_confirma_y_libera_la_franja(
    reserva_con_abono, barbero, servicio
):
    respuesta = webhook(reserva_con_abono["referencia"], CONTRATO["rechazado"])

    assert respuesta.status_code == 200
    cita = Cita.objects.get(pk=reserva_con_abono["cita_id"])
    assert cita.status != "CONFIRMED"
    assert (
        visitante_reserva(barbero, servicio, reserva_con_abono["inicio"]).status_code
        == 201
    )


@pytest.mark.parametrize("token", ["", "token-falso"])
def test_webhook_sin_token_valido_se_rechaza(reserva_con_abono, token):
    respuesta = webhook(reserva_con_abono["referencia"], "APPROVED", token=token)

    assert respuesta.status_code in (401, 403)
    cita = Cita.objects.get(pk=reserva_con_abono["cita_id"])
    assert cita.status == CONTRATO["estado_espera"]


def test_webhook_con_referencia_desconocida_no_confirma_nada(reserva_con_abono):
    respuesta = webhook("REF-QUE-NO-EXISTE", "APPROVED")

    assert respuesta.status_code in (400, 404)
    cita = Cita.objects.get(pk=reserva_con_abono["cita_id"])
    assert cita.status == CONTRATO["estado_espera"]


# --- Expiracion a los 15 minutos ------------------------------------------


def test_antes_de_15_minutos_la_cita_sigue_esperando(reserva_con_abono):
    expirar(ahora=timezone.now() + timedelta(minutes=14))

    cita = Cita.objects.get(pk=reserva_con_abono["cita_id"])
    assert cita.status == CONTRATO["estado_espera"]


def test_abono_abandonado_expira_y_libera_la_franja(
    reserva_con_abono, barbero, servicio
):
    # Dado un cliente que nunca paga el abono
    # Cuando pasan mas de 15 minutos y corre la expiracion
    expirar(ahora=timezone.now() + timedelta(minutes=16))

    # Entonces la cita se cancela sola y otra persona puede tomar la franja
    cita = Cita.objects.get(pk=reserva_con_abono["cita_id"])
    assert cita.status == "CANCELLED"
    assert cita.late_cancellation is False
    assert (
        visitante_reserva(barbero, servicio, reserva_con_abono["inicio"]).status_code
        == 201
    )


def test_la_expiracion_no_sube_el_puntaje_del_cliente(reserva_con_abono):
    cliente = reserva_con_abono["cliente"]
    antes = api_de(cliente).get("/api/v1/scores/me").json()["score"]

    expirar(ahora=timezone.now() + timedelta(minutes=16))
    import_string(CONTRATO["recalcular_cliente"])(cliente)

    despues = api_de(cliente).get("/api/v1/scores/me").json()["score"]
    assert despues == antes == 40


def test_aprobacion_que_llega_despues_de_expirar_no_revive_la_cita(
    reserva_con_abono, barbero, servicio
):
    # Dado un abono expirado y la franja tomada por otra persona
    expirar(ahora=timezone.now() + timedelta(minutes=16))
    assert (
        visitante_reserva(barbero, servicio, reserva_con_abono["inicio"]).status_code
        == 201
    )

    # Cuando la pasarela confirma tarde
    webhook(reserva_con_abono["referencia"], CONTRATO["aprobado"])

    # Entonces la cita vieja no vuelve a Confirmada ni se cruza con la nueva
    cita = Cita.objects.get(pk=reserva_con_abono["cita_id"])
    assert cita.status == "CANCELLED"
    activas = Cita.objects.filter(
        start_at=reserva_con_abono["inicio"], status__in=["PENDING", "CONFIRMED"]
    )
    assert activas.count() == 1


def test_expirar_dos_veces_no_falla_ni_cambia_nada(reserva_con_abono):
    momento = timezone.now() + timedelta(minutes=16)
    expirar(ahora=momento)
    expirar(ahora=momento)

    assert Cita.objects.get(pk=reserva_con_abono["cita_id"]).status == "CANCELLED"
