"""SCRUM-91 / HU-19: QA del puntaje de riesgo del cliente y de la reputacion
del barbero (SmartGuard, parte 1).

Pruebas escritas antes de la implementacion (SUB-19-A, SUB-19-B y SUB-19-H).
Los historiales se arman con el ORM, se pide el recalculo con la funcion de
servicio y el resultado se lee por la API con JWT real, como lo ve cada rol.

Formula de SUB-19-A (citas de los ultimos 180 dias):
    cancelacion tardia +15, no asistio +25, finalizada o pagada -5;
    lo de hace mas de 90 dias pesa la mitad; se limita a 0..100 y se redondea.
    Niveles: 0-30 Bajo, 31-60 Medio, 61-100 Alto.
Reputacion: p = (n x promedio + 5 x 3,5) / (n + 5); puntaje = (p - 1) / 4 x 100.
    Con menos de 5 calificaciones: "Sin suficientes calificaciones".
    Niveles: 0-49 En revision, 50-74 Bueno, 75-100 Excelente.

Hallazgos al preparar los casos (ver LEEME):
- Con esos pesos el puntaje siempre es multiplo de 2,5 antes de redondear, asi
  que 31 y 61 no se pueden alcanzar con un historial real. Los bordes 30/31 y
  60/61 se prueban sobre la funcion de nivel.
- "Se redondea" no dice como se tratan los ,5 (12,5 -> 12 o 13). Aqui se asume
  mitad hacia arriba, igual que la comision de HU-12. Si el equipo decide otra
  cosa, se cambia REDONDEO_MITAD_ARRIBA.

Las rutas, rutas de import y nombres de campos nuevos viven en CONTRATO.
"""

from datetime import time, timedelta
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.utils import timezone
from django.utils.module_loading import import_string
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.barberias.models import Membresia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

pytestmark = pytest.mark.django_db

CONTRATO = {
    "mi_puntaje": "/api/v1/scores/me",
    "puntajes_clientes": "/api/v1/scores/clients",
    "puntajes_barberos": "/api/v1/scores/barbers",
    "mi_reputacion": "/api/v1/barbers/me/score",
    "calificar": "/api/v1/appointments/{id}/rating",
    "bloqueos": "/api/v1/blocks",
    # Funciones de SUB-19-A / SUB-19-B
    "recalcular_cliente": "apps.puntajes.services.recalcular_puntaje_cliente",
    "nivel_cliente": "apps.puntajes.scoring.nivel_cliente",
    "nivel_barbero": "apps.puntajes.scoring.nivel_barbero",
    # Campos de respuesta
    "campo_puntaje": "score",
    "campo_nivel": "level",
    "campo_eventos": "events",
    "campo_estrellas": "stars",
    "campo_comentario": "comment",
    "filtro_nivel": "level",
    "sin_suficientes": "Sin suficientes calificaciones",
}

REDONDEO_MITAD_ARRIBA = True
EN_REVISION = "En revisi\u00f3n"  # escrito asi para que el .ps1 quede en ASCII

_contador = {"minutos": 0}


@pytest.fixture(autouse=True)
def limpiar_throttle():
    cache.clear()
    _contador["minutos"] = 0
    yield
    cache.clear()


def api_de(usuario):
    api = APIClient()
    if usuario is not None:
        token = AccessToken.for_user(usuario)
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
    return api


@pytest.fixture
def e(make_user):
    barberia = obtener_barberia_catalogo()
    admin = make_user("admin")
    thiago_user = make_user("barbero", email="thiago@barberflow.test")
    for usuario in (admin, thiago_user):
        Membresia.objects.create(user=usuario, barberia=barberia)
    thiago = Barbero.objects.create(barberia=barberia, name="Thiago", user=thiago_user)
    for dia in range(7):
        HorarioBarbero.objects.create(
            barbero=thiago,
            weekday=dia,
            open_time=time(0, 0),
            close_time=time(23, 59),
        )
    return {
        "admin": admin,
        "thiago_user": thiago_user,
        "thiago": thiago,
        "sofia": make_user("cliente", email="sofia@barberflow.test"),
        "luis": make_user("cliente", email="luis@barberflow.test"),
        "servicio": Servicio.objects.create(
            barberia=barberia,
            name="Corte",
            price=Decimal("30000.00"),
            duration_minutes=30,
        ),
    }


def cita(e, estado, dias, cliente="sofia", tardia=False):
    """Cita de `cliente` con inicio hace `dias` dias (negativo = en el futuro)."""
    _contador["minutos"] += 30  # para que no choquen entre si
    inicio = timezone.now() - timedelta(days=dias, minutes=_contador["minutos"])
    return Cita.objects.create(
        barberia=e["thiago"].barberia,
        client=e[cliente],
        barber=e["thiago"],
        service=e["servicio"],
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        price=e["servicio"].price,
        status=estado,
        late_cancellation=tardia,
    )


def historial(e, cliente="sofia", **eventos):
    """eventos: nombre=lista de dias atras. Ej: no_show=[10, 100]."""
    for dias in eventos.get("no_show", []):
        cita(e, "NO_SHOW", dias, cliente)
    for dias in eventos.get("tardia", []):
        cita(e, "CANCELLED", dias, cliente, tardia=True)
    for dias in eventos.get("a_tiempo", []):
        cita(e, "CANCELLED", dias, cliente, tardia=False)
    for dias in eventos.get("finalizada", []):
        cita(e, "COMPLETED", dias, cliente)
    for dias in eventos.get("pagada", []):
        cita(e, "PAID", dias, cliente)


def puntaje_de(e, cliente="sofia"):
    import_string(CONTRATO["recalcular_cliente"])(e[cliente])
    respuesta = api_de(e[cliente]).get(CONTRATO["mi_puntaje"])
    assert respuesta.status_code == 200, respuesta.content
    datos = respuesta.json()
    return datos[CONTRATO["campo_puntaje"]], datos[CONTRATO["campo_nivel"]]


# --- Formula del RiskScore con los ejemplos del documento ------------------


@pytest.mark.parametrize(
    "eventos,valor,nivel",
    [
        pytest.param({}, 0, "Bajo", id="sin historial"),
        pytest.param({"tardia": [10, 20]}, 30, "Bajo", id="2 tardias: no supera 30"),
        pytest.param(
            {"no_show": [10], "tardia": [20]}, 40, "Medio", id="ejemplo de la HU"
        ),
        pytest.param({"no_show": [5]}, 25, "Bajo", id="solo un no-show"),
        pytest.param({"no_show": [5, 15, 25]}, 75, "Alto", id="tres no-shows"),
        pytest.param({"no_show": [5, 15], "tardia": [25]}, 65, "Alto", id="mixto alto"),
        pytest.param(
            {"no_show": [5], "finalizada": [6]}, 20, "Bajo", id="la finalizada resta"
        ),
        pytest.param(
            {"no_show": [5], "pagada": [6]}, 20, "Bajo", id="la pagada tambien resta"
        ),
        pytest.param({"no_show": [1, 2, 3, 4, 5]}, 100, "Alto", id="tope en 100"),
        pytest.param({"finalizada": [1, 2, 3]}, 0, "Bajo", id="piso en 0"),
        pytest.param({"a_tiempo": [3, 4, 5]}, 0, "Bajo", id="a tiempo no cuenta"),
    ],
)
def test_riskscore_reciente(e, eventos, valor, nivel):
    historial(e, **eventos)

    assert puntaje_de(e) == (valor, nivel)


@pytest.mark.parametrize(
    "eventos,valor",
    [
        pytest.param({"no_show": [89]}, 25, id="89 dias: peso completo"),
        pytest.param({"no_show": [91, 100]}, 25, id="mas de 90 dias: mitad"),
        pytest.param({"tardia": [120, 150]}, 15, id="tardias viejas: mitad"),
        pytest.param({"no_show": [179, 179]}, 25, id="179 dias: aun cuenta"),
        pytest.param({"no_show": [181, 200]}, 0, id="mas de 180 dias: no cuenta"),
        pytest.param(
            {"no_show": [10, 120], "tardia": [200]}, 38, id="mezcla de ventanas"
        ),
    ],
)
def test_riskscore_por_antiguedad(e, eventos, valor):
    # 10 + 120 dias = 25 + 12,5 = 37,5 -> 38 con mitad hacia arriba
    if valor == 38 and not REDONDEO_MITAD_ARRIBA:
        valor = 37
    historial(e, **eventos)

    assert puntaje_de(e)[0] == valor


def test_cancelacion_tardia_por_bloqueo_de_agenda_no_cuenta(e):
    # Dado una cita futura que el admin bloquea (incapacidad del barbero)
    futura = cita(e, "CONFIRMED", dias=-2)
    bloqueo = api_de(e["admin"]).post(
        CONTRATO["bloqueos"],
        {
            "barber": e["thiago"].pk,
            "start_at": futura.start_at.isoformat(),
            "end_at": futura.end_at.isoformat(),
            "reason": "Incapacidad",
        },
        format="json",
    )
    assert bloqueo.status_code == 201, bloqueo.content
    futura.refresh_from_db()
    assert futura.affected_by_block is not None

    # Cuando la cita termina cancelada como tardia
    Cita.objects.filter(pk=futura.pk).update(status="CANCELLED", late_cancellation=True)

    # Entonces no le suma al cliente
    assert puntaje_de(e)[0] == 0


def test_los_puntajes_son_por_cliente(e):
    historial(e, "sofia", no_show=[5, 6])
    historial(e, "luis", finalizada=[5])

    assert puntaje_de(e, "sofia")[0] == 50
    assert puntaje_de(e, "luis")[0] == 0


def test_mi_puntaje_lista_los_eventos_que_cuentan(e):
    historial(e, no_show=[5], tardia=[6], finalizada=[7], a_tiempo=[8])
    puntaje_de(e)

    eventos = (
        api_de(e["sofia"]).get(CONTRATO["mi_puntaje"]).json()[CONTRATO["campo_eventos"]]
    )

    # La cancelacion a tiempo no aparece porque no cuenta
    assert len(eventos) == 3


# --- Niveles en los bordes (sobre la funcion pura) -------------------------


@pytest.mark.parametrize(
    "valor,nivel",
    [
        (0, "Bajo"),
        (30, "Bajo"),
        (31, "Medio"),
        (60, "Medio"),
        (61, "Alto"),
        (100, "Alto"),
    ],
)
def test_nivel_del_cliente_en_los_bordes(valor, nivel):
    assert import_string(CONTRATO["nivel_cliente"])(valor) == nivel


@pytest.mark.parametrize(
    "valor,nivel",
    [
        (0, EN_REVISION),
        (49, EN_REVISION),
        (50, "Bueno"),
        (74, "Bueno"),
        (75, "Excelente"),
        (100, "Excelente"),
    ],
)
def test_nivel_del_barbero_en_los_bordes(valor, nivel):
    assert import_string(CONTRATO["nivel_barbero"])(valor) == nivel


# --- Calificaciones ---------------------------------------------------------


def calificar(e, la_cita, estrellas, cliente="sofia", comentario=None):
    cuerpo = {CONTRATO["campo_estrellas"]: estrellas}
    if comentario is not None:
        cuerpo[CONTRATO["campo_comentario"]] = comentario
    return api_de(e[cliente]).post(
        CONTRATO["calificar"].format(id=la_cita.pk), cuerpo, format="json"
    )


@pytest.mark.parametrize("estado", ["COMPLETED", "PAID"])
def test_se_califica_una_cita_finalizada_propia(e, estado):
    la_cita = cita(e, estado, dias=1)

    assert calificar(e, la_cita, 5, comentario="Excelente corte").status_code == 201


@pytest.mark.parametrize("estado", ["PENDING", "CONFIRMED", "CANCELLED", "NO_SHOW"])
def test_no_se_califica_una_cita_no_finalizada(e, estado):
    la_cita = cita(e, estado, dias=1)

    assert calificar(e, la_cita, 5).status_code in (400, 409)


def test_una_sola_calificacion_por_cita(e):
    la_cita = cita(e, "COMPLETED", dias=1)
    assert calificar(e, la_cita, 5).status_code == 201

    assert calificar(e, la_cita, 1).status_code in (400, 409)


def test_no_se_califica_la_cita_de_otro_cliente(e):
    la_cita = cita(e, "COMPLETED", dias=1, cliente="sofia")

    assert calificar(e, la_cita, 1, cliente="luis").status_code in (403, 404)


@pytest.mark.parametrize("estrellas", [0, 6, -1, "cinco", 4.5])
def test_estrellas_fuera_de_1_a_5_se_rechazan(e, estrellas):
    la_cita = cita(e, "COMPLETED", dias=1)

    assert calificar(e, la_cita, estrellas).status_code == 400


def test_comentario_de_mas_de_300_caracteres_se_rechaza(e):
    la_cita = cita(e, "COMPLETED", dias=1)

    assert calificar(e, la_cita, 4, comentario="a" * 301).status_code == 400
    assert calificar(e, la_cita, 4, comentario="a" * 300).status_code == 201


def test_sin_sesion_no_se_califica(e):
    la_cita = cita(e, "COMPLETED", dias=1)
    respuesta = APIClient().post(
        CONTRATO["calificar"].format(id=la_cita.pk),
        {CONTRATO["campo_estrellas"]: 5},
        format="json",
    )

    assert respuesta.status_code == 401


# --- Reputacion del barbero ---------------------------------------------------


def reputacion_tras(e, estrellas):
    for i, valor in enumerate(estrellas):
        assert calificar(e, cita(e, "COMPLETED", dias=i + 1), valor).status_code == 201
    respuesta = api_de(e["thiago_user"]).get(CONTRATO["mi_reputacion"])
    assert respuesta.status_code == 200, respuesta.content
    return respuesta.json()


def test_con_4_calificaciones_no_hay_puntaje(e):
    datos = reputacion_tras(e, [5, 5, 5, 5])

    assert datos[CONTRATO["campo_puntaje"]] is None
    assert datos[CONTRATO["campo_nivel"]] == CONTRATO["sin_suficientes"]


@pytest.mark.parametrize(
    "estrellas,valor,nivel",
    [
        # (5x5 + 17,5) / 10 = 4,25 -> 81,25
        pytest.param([5] * 5, 81, "Excelente", id="5 de cinco"),
        # (5x1 + 17,5) / 10 = 2,25 -> 31,25
        pytest.param([1] * 5, 31, EN_REVISION, id="5 de uno"),
        # (5x4 + 17,5) / 10 = 3,75 -> 68,75
        pytest.param([4] * 5, 69, "Bueno", id="5 de cuatro"),
        # (35 + 17,5) / 13 = 4,038 -> 75,96
        pytest.param([5, 5, 5, 5, 4, 4, 4, 3], 76, "Excelente", id="8 mixtas"),
    ],
)
def test_reputacion_con_5_o_mas_calificaciones(e, estrellas, valor, nivel):
    datos = reputacion_tras(e, estrellas)

    assert datos[CONTRATO["campo_puntaje"]] == valor
    assert datos[CONTRATO["campo_nivel"]] == nivel


def test_el_barbero_no_ve_quien_lo_califico(e):
    calificar(e, cita(e, "COMPLETED", dias=1), 5, comentario="Muy bien")

    cuerpo = api_de(e["thiago_user"]).get(CONTRATO["mi_reputacion"]).content.decode()

    # Ve el comentario, pero ni el correo ni el nombre de quien lo dejo
    assert "Muy bien" in cuerpo
    assert "sofia" not in cuerpo.lower()


# --- Permisos ---------------------------------------------------------------


def test_el_admin_ve_el_puntaje_y_nivel_de_todos_los_clientes(e):
    historial(e, "sofia", no_show=[5], tardia=[6])
    historial(e, "luis", finalizada=[5])
    for nombre in ("sofia", "luis"):
        import_string(CONTRATO["recalcular_cliente"])(e[nombre])

    respuesta = api_de(e["admin"]).get(CONTRATO["puntajes_clientes"])

    assert respuesta.status_code == 200
    por_correo = {f["email"]: f for f in respuesta.json()}
    assert por_correo["sofia@barberflow.test"][CONTRATO["campo_puntaje"]] == 40
    assert por_correo["sofia@barberflow.test"][CONTRATO["campo_nivel"]] == "Medio"
    assert por_correo["luis@barberflow.test"][CONTRATO["campo_puntaje"]] == 0


def test_el_admin_filtra_clientes_por_nivel(e):
    historial(e, "sofia", no_show=[5], tardia=[6])
    for nombre in ("sofia", "luis"):
        import_string(CONTRATO["recalcular_cliente"])(e[nombre])

    respuesta = api_de(e["admin"]).get(
        CONTRATO["puntajes_clientes"], {CONTRATO["filtro_nivel"]: "Medio"}
    )

    assert [f["email"] for f in respuesta.json()] == ["sofia@barberflow.test"]


def test_los_visitantes_sin_cuenta_no_tienen_puntaje(e):
    Cita.objects.create(
        barberia=e["thiago"].barberia,
        barber=e["thiago"],
        service=e["servicio"],
        start_at=timezone.now() - timedelta(days=3),
        end_at=timezone.now() - timedelta(days=3) + timedelta(minutes=30),
        price=e["servicio"].price,
        status="NO_SHOW",
        contact_name="Pedro Gomez",
        contact_phone="3001234567",
    )

    filas = api_de(e["admin"]).get(CONTRATO["puntajes_clientes"]).json()

    assert all("Pedro" not in str(f) for f in filas)


@pytest.mark.parametrize(
    "ruta,quien,esperado",
    [
        ("puntajes_clientes", "sofia", 403),
        ("puntajes_clientes", "thiago_user", 403),
        ("puntajes_clientes", None, 401),
        ("puntajes_barberos", "sofia", 403),
        ("puntajes_barberos", "thiago_user", 403),
        ("puntajes_barberos", "admin", 200),
        ("mi_puntaje", None, 401),
        ("mi_reputacion", "sofia", 403),
        ("mi_reputacion", None, 401),
    ],
)
def test_cada_quien_ve_solo_lo_suyo(e, ruta, quien, esperado):
    usuario = e[quien] if quien else None

    assert api_de(usuario).get(CONTRATO[ruta]).status_code == esperado


def test_mi_puntaje_solo_muestra_el_propio(e):
    historial(e, "sofia", no_show=[5, 6])
    for nombre in ("sofia", "luis"):
        import_string(CONTRATO["recalcular_cliente"])(e[nombre])

    datos = api_de(e["luis"]).get(CONTRATO["mi_puntaje"]).json()

    assert datos[CONTRATO["campo_puntaje"]] == 0
