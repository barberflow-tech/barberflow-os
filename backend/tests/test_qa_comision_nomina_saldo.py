"""SCRUM-85 / HU-12: QA de la comision, la nomina y el saldo del barbero.

Pruebas escritas antes de la implementacion (SUB-12-A y SUB-12-B). El pago se
hace por la API de HU-11 (POST /api/v1/payments) y la comision se lee por los
endpoints de nomina y saldo, con JWT real.

Regla de SUB-12-A: comision = base x porcentaje / 100, redondeada al peso
entero con mitad hacia arriba; el porcentaje se copia al momento del pago, asi
que cambiarlo despues solo afecta pagos futuros.

Las rutas y nombres de campos nuevos viven en CONTRATO.
"""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.barberias.models import Membresia
from apps.barberos.models import Barbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

pytestmark = pytest.mark.django_db

CONTRATO = {
    "pagos": "/api/v1/payments",
    "porcentaje": "/api/v1/barbers/{id}/commission",
    "nomina": "/api/v1/payroll",
    "detalle": "/api/v1/payroll/{id}/commissions",
    "mi_saldo": "/api/v1/barbers/me/balance",
    "campo_porcentaje": "commission_percent",
    "campo_saldo": "pending_balance",
    "campo_total_periodo": "period_total",
    "campo_servicios": "services_count",
    "campo_comisiones": "commissions",
    "filtro_desde": "from",
    "filtro_hasta": "to",
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


def dinero(valor):
    return Decimal(str(valor))


@pytest.fixture
def e(make_user):
    """Admin, dos barberos con cuenta y un cliente, en la barberia del catalogo."""
    barberia = obtener_barberia_catalogo()
    admin = make_user("admin")
    thiago_user = make_user("barbero", email="thiago@barberflow.test")
    mateo_user = make_user("barbero", email="mateo@barberflow.test")
    for usuario in (admin, thiago_user, mateo_user):
        Membresia.objects.create(user=usuario, barberia=barberia)
    return {
        "barberia": barberia,
        "admin": admin,
        "api_admin": api_de(admin),
        "cliente": make_user("cliente"),
        "thiago_user": thiago_user,
        "mateo_user": mateo_user,
        "thiago": Barbero.objects.create(
            barberia=barberia, name="Thiago", user=thiago_user
        ),
        "mateo": Barbero.objects.create(
            barberia=barberia, name="Mateo", user=mateo_user
        ),
    }


def fijar_porcentaje(e, barbero, porcentaje):
    return e["api_admin"].patch(
        CONTRATO["porcentaje"].format(id=barbero.pk),
        {CONTRATO["campo_porcentaje"]: str(porcentaje)},
        format="json",
    )


def pagar(e, barbero, precio, hace=timedelta(hours=1)):
    """Crea una cita Completada con ese precio y la cobra por la API.

    El cobro se hace con el reloj movido a 40 min despues del inicio de la cita,
    para que la fecha del pago (y de su comision) quede `hace` tiempo atras.
    """
    inicio = timezone.now() - hace
    servicio = Servicio.objects.create(
        barberia=e["barberia"],
        name=f"Servicio {precio}",
        price=Decimal(precio),
        duration_minutes=30,
    )
    cita = Cita.objects.create(
        barberia=e["barberia"],
        client=e["cliente"],
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        price=Decimal(precio),
        status="COMPLETED",
    )
    momento_del_cobro = inicio + timedelta(minutes=40)
    with patch("django.utils.timezone.now", return_value=momento_del_cobro):
        respuesta = e["api_admin"].post(
            CONTRATO["pagos"],
            {"appointment": cita.pk, "method": "CASH"},
            format="json",
        )
    assert respuesta.status_code == 201, respuesta.content
    return cita


def mi_saldo(usuario):
    respuesta = api_de(usuario).get(CONTRATO["mi_saldo"])
    assert respuesta.status_code == 200, respuesta.content
    return respuesta.json()


def montos(saldo):
    return [dinero(c["amount"]) for c in saldo[CONTRATO["campo_comisiones"]]]


# --- Calculo de la comision ------------------------------------------------


@pytest.mark.parametrize(
    "porcentaje,precio,esperado",
    [
        ("40", "50000", "20000"),  # ejemplo de la HU-12
        ("0", "50000", "0"),  # barbero sin comision: se crea en $0
        ("100", "35000", "35000"),
        ("33.33", "50000", "16665"),
        ("33.33", "45000", "14999"),  # 14998,5 -> mitad hacia arriba
        ("40", "33333", "13333"),  # 13333,2 -> hacia abajo
        ("50", "30001", "15001"),  # 15000,5 -> mitad hacia arriba
        ("12.5", "1000", "125"),
    ],
)
def test_comision_segun_porcentaje_y_monto(e, porcentaje, precio, esperado):
    # Dado un barbero con su porcentaje asignado
    assert fijar_porcentaje(e, e["thiago"], porcentaje).status_code == 200

    # Cuando se le paga un servicio
    pagar(e, e["thiago"], precio)

    # Entonces se crea una comision con el calculo esperado y suma a su saldo
    saldo = mi_saldo(e["thiago_user"])
    assert montos(saldo) == [Decimal(esperado)]
    assert dinero(saldo[CONTRATO["campo_saldo"]]) == Decimal(esperado)


def test_detalle_de_la_comision_guarda_base_y_porcentaje(e):
    fijar_porcentaje(e, e["thiago"], "40")
    pagar(e, e["thiago"], "50000")

    (comision,) = mi_saldo(e["thiago_user"])[CONTRATO["campo_comisiones"]]

    assert dinero(comision["base"]) == Decimal("50000")
    assert dinero(comision["percent"]) == Decimal("40")
    assert dinero(comision["amount"]) == Decimal("20000")
    assert comision["service"] == "Servicio 50000"


def test_el_saldo_suma_todas_las_comisiones_pendientes(e):
    fijar_porcentaje(e, e["thiago"], "40")
    for precio, horas in (("50000", 5), ("30000", 4), ("25000", 3)):
        pagar(e, e["thiago"], precio, hace=timedelta(hours=horas))

    saldo = mi_saldo(e["thiago_user"])

    assert sorted(montos(saldo)) == [Decimal(v) for v in ("10000", "12000", "20000")]
    assert dinero(saldo[CONTRATO["campo_saldo"]]) == Decimal("42000")


def test_cambiar_el_porcentaje_solo_afecta_pagos_futuros(e):
    # Dado un pago al 40 %
    fijar_porcentaje(e, e["thiago"], "40")
    pagar(e, e["thiago"], "50000", hace=timedelta(hours=3))

    # Cuando el admin sube el porcentaje a 45 y llega otro pago
    assert fijar_porcentaje(e, e["thiago"], "45").status_code == 200
    pagar(e, e["thiago"], "50000", hace=timedelta(hours=2))

    # Entonces la primera comision sigue en 40 % y solo la nueva usa 45 %
    comisiones = mi_saldo(e["thiago_user"])[CONTRATO["campo_comisiones"]]
    pares = sorted((dinero(c["percent"]), dinero(c["amount"])) for c in comisiones)
    assert pares == [
        (Decimal("40"), Decimal("20000")),
        (Decimal("45"), Decimal("22500")),
    ]


def test_un_pago_repetido_no_crea_una_segunda_comision(e):
    fijar_porcentaje(e, e["thiago"], "40")
    cita = pagar(e, e["thiago"], "50000")

    repetido = e["api_admin"].post(
        CONTRATO["pagos"], {"appointment": cita.pk, "method": "CASH"}, format="json"
    )

    assert repetido.status_code == 409
    saldo = mi_saldo(e["thiago_user"])
    assert len(saldo[CONTRATO["campo_comisiones"]]) == 1
    assert dinero(saldo[CONTRATO["campo_saldo"]]) == Decimal("20000")


def test_la_comision_va_al_barbero_que_hizo_el_servicio(e):
    fijar_porcentaje(e, e["thiago"], "40")
    fijar_porcentaje(e, e["mateo"], "50")
    pagar(e, e["mateo"], "30000")

    assert montos(mi_saldo(e["thiago_user"])) == []
    assert dinero(mi_saldo(e["thiago_user"])[CONTRATO["campo_saldo"]]) == 0
    assert montos(mi_saldo(e["mateo_user"])) == [Decimal("15000")]


def test_barbero_nuevo_tiene_cero_por_ciento_por_defecto(e):
    pagar(e, e["thiago"], "50000")

    assert montos(mi_saldo(e["thiago_user"])) == [Decimal("0")]


# --- Validacion del porcentaje -------------------------------------------


@pytest.mark.parametrize("valor", ["101", "-1", "100.01", "abc", "40.123"])
def test_porcentaje_invalido_se_rechaza_con_400(e, valor):
    fijar_porcentaje(e, e["thiago"], "40")

    respuesta = fijar_porcentaje(e, e["thiago"], valor)

    assert respuesta.status_code == 400
    e["thiago"].refresh_from_db()
    assert e["thiago"].commission_percent == Decimal("40")


@pytest.mark.parametrize("valor", ["0", "100", "33.33"])
def test_porcentaje_en_los_bordes_se_acepta(e, valor):
    assert fijar_porcentaje(e, e["thiago"], valor).status_code == 200


# --- Nomina y filtros por fecha --------------------------------------------


def test_nomina_muestra_cada_barbero_con_porcentaje_saldo_y_servicios(e):
    fijar_porcentaje(e, e["thiago"], "40")
    fijar_porcentaje(e, e["mateo"], "50")
    pagar(e, e["thiago"], "50000", hace=timedelta(hours=3))
    pagar(e, e["thiago"], "30000", hace=timedelta(hours=2))
    pagar(e, e["mateo"], "20000")

    respuesta = e["api_admin"].get(CONTRATO["nomina"])

    assert respuesta.status_code == 200
    filas = {fila["barber"]: fila for fila in respuesta.json()}
    assert dinero(filas["Thiago"][CONTRATO["campo_saldo"]]) == Decimal("32000")
    assert filas["Thiago"][CONTRATO["campo_servicios"]] == 2
    assert dinero(filas["Mateo"][CONTRATO["campo_saldo"]]) == Decimal("10000")
    assert dinero(filas["Mateo"][CONTRATO["campo_porcentaje"]]) == Decimal("50")


def test_nomina_con_rango_de_fechas_solo_suma_ese_rango(e):
    # Dado pagos de hace 10 dias, hace 3 dias y de hoy
    fijar_porcentaje(e, e["thiago"], "40")
    pagar(e, e["thiago"], "50000", hace=timedelta(days=10))
    pagar(e, e["thiago"], "30000", hace=timedelta(days=3))
    pagar(e, e["thiago"], "25000", hace=timedelta(hours=1))
    hoy = timezone.localdate()

    # Cuando el admin filtra los ultimos 5 dias sin contar hoy
    respuesta = e["api_admin"].get(
        CONTRATO["nomina"],
        {
            CONTRATO["filtro_desde"]: (hoy - timedelta(days=5)).isoformat(),
            CONTRATO["filtro_hasta"]: (hoy - timedelta(days=1)).isoformat(),
        },
    )

    # Entonces el total del periodo es solo el del pago de hace 3 dias
    (fila,) = [f for f in respuesta.json() if f["barber"] == "Thiago"]
    assert dinero(fila[CONTRATO["campo_total_periodo"]]) == Decimal("12000")
    assert fila[CONTRATO["campo_servicios"]] == 1


def test_detalle_de_un_barbero_suma_lo_mismo_que_su_saldo(e):
    fijar_porcentaje(e, e["thiago"], "33.33")
    for precio, horas in (("50000", 4), ("45000", 3), ("30001", 2)):
        pagar(e, e["thiago"], precio, hace=timedelta(hours=horas))

    detalle = e["api_admin"].get(CONTRATO["detalle"].format(id=e["thiago"].pk))

    assert detalle.status_code == 200
    total = sum(dinero(c["amount"]) for c in detalle.json())
    saldo = dinero(mi_saldo(e["thiago_user"])[CONTRATO["campo_saldo"]])
    assert total == saldo
    for comision in detalle.json():
        for campo in ("date", "service", "client", "base", "percent", "amount"):
            assert campo in comision


# --- Permisos ---------------------------------------------------------------


@pytest.mark.parametrize("quien,esperado", [("cliente", 403), ("thiago_user", 403)])
def test_solo_el_admin_edita_porcentajes(e, quien, esperado):
    respuesta = api_de(e[quien]).patch(
        CONTRATO["porcentaje"].format(id=e["thiago"].pk),
        {CONTRATO["campo_porcentaje"]: "90"},
        format="json",
    )

    assert respuesta.status_code == esperado
    e["thiago"].refresh_from_db()
    assert e["thiago"].commission_percent == Decimal("0")


@pytest.mark.parametrize("ruta", ["nomina", "detalle"])
@pytest.mark.parametrize(
    "quien,esperado", [("cliente", 403), ("thiago_user", 403), (None, 401)]
)
def test_solo_el_admin_ve_la_nomina(e, ruta, quien, esperado):
    usuario = e[quien] if quien else None
    url = CONTRATO[ruta].format(id=e["thiago"].pk)

    assert api_de(usuario).get(url).status_code == esperado


def test_el_barbero_solo_ve_su_propio_saldo(e):
    fijar_porcentaje(e, e["mateo"], "50")
    pagar(e, e["mateo"], "30000")

    saldo_thiago = mi_saldo(e["thiago_user"])

    assert montos(saldo_thiago) == []
    # Y no puede leer el detalle de otro barbero por la ruta del admin
    url = CONTRATO["detalle"].format(id=e["mateo"].pk)
    assert api_de(e["thiago_user"]).get(url).status_code == 403


@pytest.mark.parametrize("quien,esperado", [("cliente", 403), (None, 401)])
def test_cliente_y_visitante_no_tienen_saldo(e, quien, esperado):
    usuario = e[quien] if quien else None

    assert api_de(usuario).get(CONTRATO["mi_saldo"]).status_code == esperado
