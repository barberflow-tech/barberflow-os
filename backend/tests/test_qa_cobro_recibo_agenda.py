"""SCRUM-79 / HU-11: QA del cobro en caja, del recibo y de la agenda del barbero.

Pruebas escritas antes de la implementacion (SUB-11-A y SUB-11-E). Todo va por
HTTP con un JWT real, como lo usa el frontend. Las citas de partida se crean
con el ORM en el estado que haga falta (Completada, Pendiente, etc.).

Las rutas y los nombres de campos que todavia no existen viven en CONTRATO:
si Cristhian (SUB-11-A) o Brandon (SUB-11-E) eligen otros, se cambian solo ahi.

La revision visual del recibo impreso (vista de impresion) es manual y queda
en el LEEME de esta carpeta.
"""

import re
import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.db import connection
from django.utils import timezone
from django.utils.module_loading import import_string
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
    "recibo": "/api/v1/payments/{id}/receipt",
    "agenda": "/api/v1/appointments/mine",
    "completar": "/api/v1/appointments/{id}/complete",
    # Cuerpo del POST de pago
    "campo_cita": "appointment",
    "campo_metodo": "method",
    "campo_referencia": "reference",
    "efectivo": "CASH",
    "tarjeta": "CARD",
    # Respuesta del pago y del recibo
    "campo_numero": "receipt_number",
    "formato_numero": r"^R-\d{6}$",
    # Modelo de SUB-11-A, solo para contar pagos en la base de datos
    "modelo_pago": "apps.pagos.models.Pago",
}

PRECIO = Decimal("30000.00")


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


@pytest.fixture
def barberia():
    return obtener_barberia_catalogo()


@pytest.fixture
def escenario(make_user, barberia):
    """Admin y dos barberos con cuenta, de la barberia del catalogo."""
    admin = make_user("admin")
    thiago_user = make_user("barbero", email="thiago@barberflow.test")
    mateo_user = make_user("barbero", email="mateo@barberflow.test")
    for usuario in (admin, thiago_user, mateo_user):
        Membresia.objects.create(user=usuario, barberia=barberia)
    servicio = Servicio.objects.create(
        barberia=barberia, name="Corte Clasico", price=PRECIO, duration_minutes=30
    )
    return {
        "admin": admin,
        "cliente": make_user("cliente", email="sofia@barberflow.test"),
        "thiago_user": thiago_user,
        "mateo_user": mateo_user,
        "thiago": Barbero.objects.create(
            barberia=barberia, name="Thiago", user=thiago_user
        ),
        "mateo": Barbero.objects.create(
            barberia=barberia, name="Mateo", user=mateo_user
        ),
        "servicio": servicio,
    }


def nueva_cita(e, estado="COMPLETED", barbero=None, cliente="cliente", inicio=None):
    """Cita en el estado pedido. cliente=None crea la de un visitante sin cuenta."""
    barbero = barbero or e["thiago"]
    inicio = inicio or timezone.now() - timedelta(hours=1)
    datos = {}
    if cliente is None:
        datos = {"contact_name": "Pedro Gomez", "contact_phone": "3001234567"}
    else:
        datos = {"client": e[cliente]}
    return Cita.objects.create(
        barberia=barbero.barberia,
        barber=barbero,
        service=e["servicio"],
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        price=PRECIO,
        status=estado,
        **datos,
    )


def cobrar(api, cita, metodo="efectivo", referencia=None):
    cuerpo = {
        CONTRATO["campo_cita"]: cita.pk,
        CONTRATO["campo_metodo"]: CONTRATO[metodo],
    }
    if referencia is not None:
        cuerpo[CONTRATO["campo_referencia"]] = referencia
    return api.post(CONTRATO["pagos"], cuerpo, format="json")


def recibo(api, pago_id):
    return api.get(CONTRATO["recibo"].format(id=pago_id))


def contar_pagos():
    return import_string(CONTRATO["modelo_pago"]).objects.count()


def numero(respuesta):
    return respuesta.json()[CONTRATO["campo_numero"]]


# --- Cobro en efectivo y con tarjeta ------------------------------------


def test_cobro_en_efectivo_deja_la_cita_pagada_y_devuelve_el_recibo(escenario):
    # Dado una cita Completada
    cita = nueva_cita(escenario)

    # Cuando el administrador la cobra en efectivo
    respuesta = cobrar(api_de(escenario["admin"]), cita, "efectivo")

    # Entonces la cita queda Pagada y la respuesta trae el numero del recibo
    assert respuesta.status_code == 201, respuesta.content
    assert re.match(CONTRATO["formato_numero"], numero(respuesta))
    cita.refresh_from_db()
    assert cita.status == "PAID"


def test_cobro_con_tarjeta_guarda_la_referencia_y_el_monto_de_la_cita(escenario):
    cita = nueva_cita(escenario)
    admin = api_de(escenario["admin"])

    respuesta = cobrar(admin, cita, "tarjeta", referencia="VOUCHER-4589")

    assert respuesta.status_code == 201, respuesta.content
    datos = recibo(admin, respuesta.json()["id"]).json()
    assert datos[CONTRATO["campo_metodo"]] == CONTRATO["tarjeta"]
    assert Decimal(str(datos["amount"])) == PRECIO


def test_el_monto_es_el_precio_guardado_en_la_cita_no_el_del_catalogo(escenario):
    # Dado una cita completada y luego una subida de precio en el catalogo
    cita = nueva_cita(escenario)
    escenario["servicio"].price = Decimal("45000.00")
    escenario["servicio"].save()
    admin = api_de(escenario["admin"])

    # Cuando se cobra, se cobra lo que se acordo al reservar
    respuesta = cobrar(admin, cita)

    assert respuesta.status_code == 201
    datos = recibo(admin, respuesta.json()["id"]).json()
    assert Decimal(str(datos["amount"])) == PRECIO


def test_el_cliente_no_puede_fijar_el_monto_del_pago(escenario):
    cita = nueva_cita(escenario)
    admin = api_de(escenario["admin"])
    cuerpo = {
        CONTRATO["campo_cita"]: cita.pk,
        CONTRATO["campo_metodo"]: CONTRATO["efectivo"],
        "amount": "1.00",
    }

    respuesta = admin.post(CONTRATO["pagos"], cuerpo, format="json")

    assert respuesta.status_code == 201
    datos = recibo(admin, respuesta.json()["id"]).json()
    assert Decimal(str(datos["amount"])) == PRECIO


def test_metodo_desconocido_responde_400(escenario):
    cita = nueva_cita(escenario)
    cuerpo = {CONTRATO["campo_cita"]: cita.pk, CONTRATO["campo_metodo"]: "BITCOIN"}

    respuesta = api_de(escenario["admin"]).post(
        CONTRATO["pagos"], cuerpo, format="json"
    )

    assert respuesta.status_code == 400
    cita.refresh_from_db()
    assert cita.status == "COMPLETED"


# --- Doble cobro y citas no finalizadas -----------------------------------


def test_doble_cobro_responde_409_y_no_duplica_el_recibo(escenario):
    # Dado un cobro ya registrado
    cita = nueva_cita(escenario)
    admin = api_de(escenario["admin"])
    primero = cobrar(admin, cita)
    assert primero.status_code == 201

    # Cuando se intenta cobrar de nuevo, incluso con otro metodo
    segundo = cobrar(admin, cita, "tarjeta", referencia="X")

    # Entonces se rechaza y el recibo sigue siendo uno solo
    assert segundo.status_code == 409
    assert contar_pagos() == 1


@pytest.mark.parametrize("estado", ["PENDING", "CONFIRMED", "CANCELLED", "NO_SHOW"])
def test_cita_no_finalizada_no_se_puede_cobrar(escenario, estado):
    cita = nueva_cita(escenario, estado=estado)

    respuesta = cobrar(api_de(escenario["admin"]), cita)

    assert respuesta.status_code == 409
    cita.refresh_from_db()
    assert cita.status == estado


def test_cita_inexistente_responde_404(escenario):
    cuerpo = {CONTRATO["campo_cita"]: 999999, CONTRATO["campo_metodo"]: "CASH"}

    respuesta = api_de(escenario["admin"]).post(
        CONTRATO["pagos"], cuerpo, format="json"
    )

    assert respuesta.status_code in (400, 404)


@pytest.mark.django_db(transaction=True)
def test_doble_cobro_concurrente_solo_uno_gana(escenario):
    # Dado dos cajeros (el mismo admin en dos pestanas) que cobran a la vez
    cita = nueva_cita(escenario)
    admin = escenario["admin"]
    barrera = threading.Barrier(2)
    codigos = [None, None]

    def cobrar_en_hilo(indice, metodo):
        try:
            barrera.wait()
            codigos[indice] = cobrar(api_de(admin), cita, metodo).status_code
        finally:
            connection.close()

    hilos = [
        threading.Thread(target=cobrar_en_hilo, args=(0, "efectivo")),
        threading.Thread(target=cobrar_en_hilo, args=(1, "tarjeta")),
    ]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(20)

    # Entonces exactamente uno cobra y el otro recibe 409
    assert sorted(codigos) == [201, 409]
    assert contar_pagos() == 1


# --- Numeracion del recibo -------------------------------------------------


def test_numeracion_consecutiva_sin_saltos(escenario):
    admin = api_de(escenario["admin"])
    citas = [
        nueva_cita(escenario, inicio=timezone.now() - timedelta(hours=h))
        for h in (5, 4, 3)
    ]

    numeros = [numero(cobrar(admin, cita)) for cita in citas]

    enteros = [int(n.split("-")[1]) for n in numeros]
    assert enteros == list(range(enteros[0], enteros[0] + 3))


def test_un_cobro_rechazado_no_consume_numero(escenario):
    # Un 409 en medio no debe dejar un hueco en la numeracion
    admin = api_de(escenario["admin"])
    pagada = nueva_cita(escenario, inicio=timezone.now() - timedelta(hours=3))
    pendiente = nueva_cita(escenario, estado="PENDING")
    otra = nueva_cita(escenario, inicio=timezone.now() - timedelta(hours=2))

    n1 = numero(cobrar(admin, pagada))
    assert cobrar(admin, pagada).status_code == 409
    assert cobrar(admin, pendiente).status_code == 409
    n2 = numero(cobrar(admin, otra))

    assert int(n2.split("-")[1]) == int(n1.split("-")[1]) + 1


# --- Contenido del recibo ---------------------------------------------------


def test_recibo_trae_todos_los_datos_del_diseno(escenario):
    cita = nueva_cita(escenario)
    admin = api_de(escenario["admin"])
    pago = cobrar(admin, cita).json()

    datos = recibo(admin, pago["id"]).json()

    for campo in (
        "barberia",
        CONTRATO["campo_numero"],
        "date",
        "client",
        "service",
        "barber",
        "amount",
        CONTRATO["campo_metodo"],
    ):
        assert campo in datos, f"falta {campo} en el recibo"
    assert datos["service"] == "Corte Clasico"
    assert datos["barber"] == "Thiago"


def test_recibo_de_visitante_sin_cuenta_usa_el_nombre_de_contacto(escenario):
    cita = nueva_cita(escenario, cliente=None)
    admin = api_de(escenario["admin"])
    pago = cobrar(admin, cita)
    assert pago.status_code == 201

    datos = recibo(admin, pago.json()["id"]).json()

    assert datos["client"] == "Pedro Gomez"


def test_el_cliente_ve_su_recibo_pero_no_el_de_otro(escenario, make_user):
    cita = nueva_cita(escenario)
    pago_id = cobrar(api_de(escenario["admin"]), cita).json()["id"]
    otro = make_user("cliente", email="otro@barberflow.test")

    assert recibo(api_de(escenario["cliente"]), pago_id).status_code == 200
    assert recibo(api_de(otro), pago_id).status_code in (403, 404)
    assert recibo(api_de(None), pago_id).status_code == 401


# --- Permisos del cobro -----------------------------------------------------


@pytest.mark.parametrize(
    "quien,esperado",
    [("cliente", 403), ("thiago_user", 403), (None, 401)],
)
def test_solo_el_administrador_cobra(escenario, quien, esperado):
    cita = nueva_cita(escenario)
    usuario = escenario[quien] if quien else None

    respuesta = cobrar(api_de(usuario), cita)

    assert respuesta.status_code == esperado
    cita.refresh_from_db()
    assert cita.status == "COMPLETED"


# --- Agenda del barbero (SUB-11-E) -----------------------------------------


def test_el_barbero_ve_solo_sus_citas_de_hoy_y_proximas_ordenadas(escenario):
    ahora = timezone.now()
    tarde = nueva_cita(escenario, "CONFIRMED", inicio=ahora + timedelta(hours=5))
    temprano = nueva_cita(escenario, "CONFIRMED", inicio=ahora + timedelta(hours=2))
    nueva_cita(escenario, "CONFIRMED", inicio=ahora - timedelta(days=3))  # pasada
    nueva_cita(escenario, "CONFIRMED", barbero=escenario["mateo"])  # ajena

    respuesta = api_de(escenario["thiago_user"]).get(CONTRATO["agenda"])

    assert respuesta.status_code == 200
    ids = [c["id"] for c in respuesta.json()]
    assert ids == [temprano.pk, tarde.pk]


def test_la_agenda_muestra_hora_cliente_celular_servicio_y_precio(escenario):
    nueva_cita(escenario, "CONFIRMED", inicio=timezone.now() + timedelta(hours=2))

    (cita,) = api_de(escenario["thiago_user"]).get(CONTRATO["agenda"]).json()

    for campo in ("start_at", "client", "phone", "service", "price"):
        assert campo in cita, f"falta {campo} en la agenda"


def test_agenda_vacia_responde_lista_vacia(escenario):
    respuesta = api_de(escenario["thiago_user"]).get(CONTRATO["agenda"])

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_el_barbero_completa_su_cita_y_queda_lista_para_cobrar(escenario):
    # Dado una cita confirmada del barbero que ya empezo
    cita = nueva_cita(escenario, "CONFIRMED")

    # Cuando la marca como completada
    respuesta = api_de(escenario["thiago_user"]).post(
        CONTRATO["completar"].format(id=cita.pk)
    )

    # Entonces queda Completada y el admin ya la puede cobrar
    assert respuesta.status_code == 200
    cita.refresh_from_db()
    assert cita.status == "COMPLETED"
    assert cobrar(api_de(escenario["admin"]), cita).status_code == 201


def test_no_se_completa_una_cita_que_no_ha_empezado(escenario):
    cita = nueva_cita(
        escenario, "CONFIRMED", inicio=timezone.now() + timedelta(hours=3)
    )

    respuesta = api_de(escenario["thiago_user"]).post(
        CONTRATO["completar"].format(id=cita.pk)
    )

    assert respuesta.status_code in (400, 409)
    cita.refresh_from_db()
    assert cita.status == "CONFIRMED"


def test_el_barbero_no_completa_la_cita_de_otro_barbero(escenario):
    ajena = nueva_cita(escenario, "CONFIRMED", barbero=escenario["mateo"])

    respuesta = api_de(escenario["thiago_user"]).post(
        CONTRATO["completar"].format(id=ajena.pk)
    )

    assert respuesta.status_code in (403, 404)
    assert "Mateo" not in respuesta.content.decode()
    ajena.refresh_from_db()
    assert ajena.status == "CONFIRMED"


@pytest.mark.parametrize("quien,esperado", [("cliente", 403), (None, 401)])
def test_cliente_y_visitante_no_ven_la_agenda_del_barbero(escenario, quien, esperado):
    usuario = escenario[quien] if quien else None

    assert api_de(usuario).get(CONTRATO["agenda"]).status_code == esperado
