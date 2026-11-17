"""SCRUM-66 / HU-05: QA de los recordatorios con tiempo simulado.

Complementa test_recordatorios.py y test_concurrencia_recordatorios.py (SCRUM-63)
desde el lado del cliente: las citas se reservan, cancelan y reprograman por
HTTP con JWT real, y luego se simula la tarea programada corriendo cada 10
minutos. El correo usa el buzon de prueba (locmem): no sale ningun envio real.

Nota: la tarea recuerda las citas activas, PENDING y CONFIRMED. Hoy la reserva
crea las citas como PENDING, asi que "confirmada" en el ticket equivale a
"activa"; las canceladas nunca reciben aviso.
"""

from datetime import datetime, timedelta
from datetime import time as hora_del_dia
from decimal import Decimal
from io import StringIO
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas import services_recordatorios
from apps.citas.models import Cita, RecordatorioCita
from apps.citas.services import ZONA_HORARIA_BARBERIA
from apps.citas.services_recordatorios import enviar_recordatorios

pytestmark = pytest.mark.django_db

CITAS = "/api/v1/appointments"
CADA_10_MIN = timedelta(minutes=10)


def hora_local(dias, hora, minuto=0):
    """Hora de pared en la barberia, `dias` despues de hoy."""
    hoy = timezone.now().astimezone(ZONA_HORARIA_BARBERIA).date()
    return datetime.combine(
        hoy + timedelta(days=dias),
        hora_del_dia(hora, minuto),
        tzinfo=ZONA_HORARIA_BARBERIA,
    )


def api_de(usuario):
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(usuario)}")
    return api


def correr_tarea(desde, hasta, al_correr=None):
    """Simula el cron cada 10 min entre `desde` y `hasta` (inclusive).

    Devuelve [(momento, correo)] de cada correo nuevo, en orden de salida.
    `al_correr(momento)` permite que el cliente haga algo entre ejecuciones.
    """
    enviados = []
    momento = desde
    while momento <= hasta:
        if al_correr:
            al_correr(momento)
        antes = len(mail.outbox)
        enviar_recordatorios(ahora=momento)
        enviados += [(momento, correo) for correo in mail.outbox[antes:]]
        momento += CADA_10_MIN
    return enviados


@pytest.fixture(autouse=True)
def limpiar_throttle():
    cache.clear()
    yield
    cache.clear()


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


@pytest.fixture
def servicio():
    return Servicio.objects.create(
        barberia=obtener_barberia_catalogo(),
        name="Corte Clasico",
        price=Decimal("30000.00"),
        duration_minutes=30,
    )


def reservar(api, barbero, servicio, inicio, **extra):
    respuesta = api.post(
        CITAS,
        {
            "barber": barbero.pk,
            "service": servicio.pk,
            "start_at": inicio.isoformat(),
            **extra,
        },
        format="json",
    )
    assert respuesta.status_code == 201, respuesta.content
    return respuesta.json()["id"]


def test_las_pruebas_no_envian_correos_reales():
    # DoD: sin envios reales; todo cae en el buzon de memoria de Django
    assert settings.EMAIL_BACKEND == "django.core.mail.backends.locmem.EmailBackend"


# --- Criterio: activas reciben aviso, canceladas no, nunca dos veces --------


def test_dia_simulado_con_citas_activas_canceladas_y_de_visitante(
    make_user, barbero, servicio
):
    # Dado cuatro reservas hechas por la API para pasado manana:
    ana = make_user("cliente", email="ana@barberflow.test")
    luis = make_user("cliente", email="luis@barberflow.test")
    marta = make_user("cliente", email="marta@barberflow.test")
    api_ana, api_luis, api_marta = api_de(ana), api_de(luis), api_de(marta)
    # Ana mantiene su cita de las 10:00
    cita_ana = hora_local(2, 10)
    reservar(api_ana, barbero, servicio, cita_ana)
    # Luis reserva a las 11:00 y cancela despues del aviso de 24 h
    cita_luis = hora_local(2, 11)
    id_luis = reservar(api_luis, barbero, servicio, cita_luis)
    # Marta reserva a las 12:30 y cancela de una vez
    id_marta = reservar(api_marta, barbero, servicio, hora_local(2, 12, 30))
    assert api_marta.post(f"{CITAS}/{id_marta}/cancel").status_code == 200
    # Y un visitante reserva a las 12:00 sin cuenta (solo deja celular)
    reservar(
        APIClient(),
        barbero,
        servicio,
        hora_local(2, 12),
        contact_name="Pedro Gomez",
        contact_phone="3001234567",
    )

    def luis_cancela(momento):
        if momento == cita_luis - timedelta(hours=10):
            assert api_luis.post(f"{CITAS}/{id_luis}/cancel").status_code == 200

    # Cuando la tarea corre cada 10 min durante mas de un dia
    enviados = correr_tarea(
        cita_ana - timedelta(hours=25),
        hora_local(2, 12, 30),
        al_correr=luis_cancela,
    )

    # Entonces Ana recibe exactamente dos avisos, el de 24 h y luego el de 2 h,
    # cada uno dentro de su ventana; Luis solo el de 24 h; Marta y el visitante
    # ninguno
    destinatarios = [correo.to for _, correo in enviados]
    assert sorted(destinatarios) == sorted([[ana.email], [ana.email], [luis.email]])
    de_ana = [(m, c) for m, c in enviados if c.to == [ana.email]]
    (momento_24h, aviso_24h), (momento_2h, aviso_2h) = de_ana
    assert "Faltan 24 horas" in aviso_24h.body
    assert "Faltan 2 horas" in aviso_2h.body
    assert (
        timedelta(hours=23, minutes=30) < cita_ana - momento_24h <= timedelta(hours=24)
    )
    assert timedelta(hours=1, minutes=30) < cita_ana - momento_2h <= timedelta(hours=2)
    ((_, aviso_luis),) = [(m, c) for m, c in enviados if c.to == [luis.email]]
    assert "Faltan 24 horas" in aviso_luis.body

    # Y quedan registrados tres avisos enviados, ninguno pendiente
    assert RecordatorioCita.objects.filter(sent_at__isnull=False).count() == 3
    assert not RecordatorioCita.objects.filter(sent_at__isnull=True).exists()


def test_correr_la_tarea_muchas_veces_en_el_mismo_minuto_no_duplica(
    make_user, barbero, servicio
):
    cliente = make_user("cliente")
    inicio = hora_local(2, 10)
    reservar(api_de(cliente), barbero, servicio, inicio)
    momento = inicio - timedelta(hours=24)

    for _ in range(5):
        enviar_recordatorios(ahora=momento)

    assert len(mail.outbox) == 1


# --- Contenido del correo -----------------------------------------------


def test_contenido_del_aviso_con_los_datos_de_la_reserva(make_user, barbero, servicio):
    # Dado un cliente que reservo por la API a las 15:30 hora de Bogota
    cliente = make_user("cliente", email="sofia@barberflow.test")
    inicio = hora_local(2, 15, 30)
    reservar(api_de(cliente), barbero, servicio, inicio)

    # Cuando sale el aviso de 2 h
    enviar_recordatorios(ahora=inicio - timedelta(hours=2))

    # Entonces va solo a su correo, con la hora local y los datos de la cita
    (correo,) = mail.outbox
    assert correo.to == [cliente.email]
    assert correo.subject == (
        f"Recordatorio: tu cita del {inicio:%d/%m/%Y} a las 15:30"
    )
    for dato in ("Corte Clasico", "Thiago", "15:30", "$30.000", "/perfil"):
        assert dato in correo.body
    ((html, tipo),) = correo.alternatives
    assert tipo == "text/html"
    assert "Faltan 2 horas" in html


# --- Reprogramar por la API mueve los avisos ------------------------------


def test_reprogramar_por_la_api_manda_los_avisos_de_la_hora_nueva(
    make_user, barbero, servicio
):
    # Dado una cita que ya recibio su aviso de 24 h
    cliente = make_user("cliente")
    api = api_de(cliente)
    original = hora_local(2, 10)
    cita_id = reservar(api, barbero, servicio, original)
    enviar_recordatorios(ahora=original - timedelta(hours=24))
    assert len(mail.outbox) == 1

    # Cuando el cliente la reprograma al dia siguiente
    nueva = hora_local(3, 15)
    respuesta = api.post(
        f"{CITAS}/{cita_id}/reschedule",
        {"start_at": nueva.isoformat()},
        format="json",
    )
    assert respuesta.status_code == 200

    # Entonces la hora vieja no dispara el aviso de 2 h, y la nueva recibe
    # sus dos avisos con la hora nueva en el asunto
    enviar_recordatorios(ahora=original - timedelta(hours=2))
    assert len(mail.outbox) == 1
    enviados = correr_tarea(nueva - timedelta(hours=25), nueva)
    assert len(enviados) == 2
    assert all("a las 15:00" in correo.subject for _, correo in enviados)
    assert Cita.objects.get(pk=cita_id).recordatorios.count() == 3


# --- El comando del cron ------------------------------------------------


def test_comando_con_reloj_simulado_envia_una_vez_y_luego_nada(
    make_user, barbero, servicio
):
    cliente = make_user("cliente")
    inicio = hora_local(2, 10)
    reservar(api_de(cliente), barbero, servicio, inicio)

    def correr_comando(momento):
        salida = StringIO()
        with patch.object(services_recordatorios.timezone, "now", return_value=momento):
            call_command("enviar_recordatorios", stdout=salida)
        return salida.getvalue()

    assert "Enviados: 0" in correr_comando(inicio - timedelta(hours=25))
    assert "Enviados: 1" in correr_comando(inicio - timedelta(hours=24))
    assert "Enviados: 0" in correr_comando(inicio - timedelta(hours=23, minutes=50))
    assert len(mail.outbox) == 1
