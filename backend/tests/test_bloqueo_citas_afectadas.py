"""SCRUM-60 (HU-04): al bloquear la agenda se marcan y avisan las citas afectadas.

Criterio: dado un barbero con incapacidad y citas ese dia, cuando el
administrador bloquea su agenda, las citas afectadas se marcan y cada cliente
recibe el aviso. DoD: sin citas afectadas pendientes de aviso tras el bloqueo.

El aviso usa el servicio de HU-05 (`send_notification_email`). Los visitantes
sin cuenta no tienen correo: quedan marcados y se devuelven al admin para que
los llame, pero no cuentan como pendientes porque el sistema no puede avisarles.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal
from smtplib import SMTPException
from unittest import mock

import pytest
from django.core import mail
from django.utils import timezone

from apps.barberias.models import Membresia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas import services
from apps.citas.models import BloqueoAgenda, Cita
from apps.citas.services import ZONA_HORARIA_BARBERIA
from apps.notificaciones.models import EmailDelivery

pytestmark = pytest.mark.django_db

BLOCKS = "/api/v1/blocks"
MOTIVO = "Incapacidad medica"


@pytest.fixture
def agenda(admin_user):
    barberia = obtener_barberia_catalogo()
    Membresia.objects.create(user=admin_user, barberia=barberia)
    barbero = Barbero.objects.create(barberia=barberia, name="Ana")
    servicio = Servicio.objects.create(
        barberia=barberia, name="Corte", duration_minutes=30, price=25000
    )
    dia = timezone.localdate(timezone=ZONA_HORARIA_BARBERIA) + timedelta(days=2)
    HorarioBarbero.objects.create(
        barbero=barbero, weekday=dia.weekday(), open_time=time(9), close_time=time(18)
    )
    inicio = datetime.combine(dia, time.min, tzinfo=ZONA_HORARIA_BARBERIA)
    return barbero, servicio, inicio


@pytest.fixture
def admin_api(admin_user, login, api_client):
    respuesta = login(admin_user.email)
    assert respuesta.status_code == 200
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.data['access']}")
    return api_client


def a_las(inicio, hora, minuto=0):
    return inicio.replace(hour=hora, minute=minuto)


def cita(barbero, servicio, inicio, *, cliente=None, estado=Cita.Estado.PENDING, **kw):
    datos = dict(
        barberia=barbero.barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        status=estado,
        price=Decimal("25000"),
    )
    if cliente is None and "contact_name" not in kw:
        kw.update(contact_name="Visitante", contact_phone="3001234567")
    datos.update(kw)
    return Cita.objects.create(**datos)


def bloquear_dia(api, barbero, inicio, fin=None):
    return api.post(
        BLOCKS,
        {
            "barber": barbero.pk,
            "start_at": inicio.isoformat(),
            "end_at": (fin or inicio + timedelta(days=1)).isoformat(),
            "reason": MOTIVO,
        },
        format="json",
    )


def clientes(make_user, cantidad):
    return [make_user(email=f"cliente{i}@barberflow.test") for i in range(cantidad)]


def test_bloquear_el_dia_marca_las_citas_y_avisa_a_cada_cliente(
    admin_api, agenda, make_user
):
    # Dado un barbero con incapacidad y citas ese dia
    barbero, servicio, inicio = agenda
    ana, beto = clientes(make_user, 2)
    c1 = cita(barbero, servicio, a_las(inicio, 10), cliente=ana)
    c2 = cita(barbero, servicio, a_las(inicio, 15), cliente=beto)

    # Cuando el administrador bloquea su agenda
    respuesta = bloquear_dia(admin_api, barbero, inicio)

    # Entonces las citas afectadas se marcan y cada cliente recibe el aviso
    assert respuesta.status_code == 201
    bloqueo = BloqueoAgenda.objects.get()
    for c in (c1, c2):
        c.refresh_from_db()
        assert c.affected_by_block == bloqueo
        assert c.block_notice_sent_at is not None
    assert sorted(m.to[0] for m in mail.outbox) == [ana.email, beto.email]
    assert len(mail.outbox) == 2
    assert respuesta.data["affected_appointments"] == {
        "total": 2,
        "notified": 2,
        "pending": 0,
        "without_channel": [],
    }


def test_dod_sin_citas_afectadas_pendientes_de_aviso(admin_api, agenda, make_user):
    barbero, servicio, inicio = agenda
    for i, usuario in enumerate(clientes(make_user, 3)):
        cita(barbero, servicio, a_las(inicio, 9 + i), cliente=usuario)

    bloquear_dia(admin_api, barbero, inicio)

    pendientes = Cita.objects.filter(
        affected_by_block__isnull=False,
        client__isnull=False,
        block_notice_sent_at__isnull=True,
    )
    assert not pendientes.exists()


def test_el_aviso_se_registra_con_el_servicio_de_notificaciones(
    admin_api, agenda, make_user
):
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    cita(barbero, servicio, a_las(inicio, 10), cliente=ana)

    bloquear_dia(admin_api, barbero, inicio)

    entrega = EmailDelivery.objects.get()
    assert entrega.recipient == ana.email
    assert entrega.status == EmailDelivery.Status.SENT


def test_el_aviso_no_revela_el_motivo_del_bloqueo(admin_api, agenda, make_user):
    # El motivo es interno (p. ej. una incapacidad medica): no es del cliente.
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    cita(barbero, servicio, a_las(inicio, 10), cliente=ana)

    bloquear_dia(admin_api, barbero, inicio)

    correo = mail.outbox[0]
    assert MOTIVO.lower() not in (correo.subject + correo.body).lower()
    assert "Corte" in correo.body
    assert "Ana" in correo.body  # nombre del barbero


def test_no_marca_citas_fuera_del_bloqueo_ni_de_otros_barberos(
    admin_api, agenda, make_user
):
    barbero, servicio, inicio = agenda
    otro = Barbero.objects.create(barberia=barbero.barberia, name="Beto")
    (ana,) = clientes(make_user, 1)
    fuera = cita(barbero, servicio, a_las(inicio, 10), cliente=ana)
    de_otro = cita(otro, servicio, a_las(inicio, 10), cliente=ana)

    # Bloqueo de la tarde del barbero 1: la cita de las 10:00 queda fuera
    respuesta = bloquear_dia(admin_api, barbero, a_las(inicio, 13), a_las(inicio, 18))

    assert respuesta.data["affected_appointments"]["total"] == 0
    for c in (fuera, de_otro):
        c.refresh_from_db()
        assert c.affected_by_block is None
    assert mail.outbox == []


def test_solo_marca_las_citas_que_se_cruzan_con_el_intervalo(
    admin_api, agenda, make_user
):
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    termina_justo = cita(
        barbero, servicio, a_las(inicio, 9), cliente=ana
    )  # 09:00-09:30
    se_cruza = cita(barbero, servicio, a_las(inicio, 9, 30), cliente=ana)  # 09:30-10:00

    # Bloqueo desde las 09:30: la primera termina justo cuando empieza
    bloquear_dia(admin_api, barbero, a_las(inicio, 9, 30), a_las(inicio, 11))

    termina_justo.refresh_from_db()
    se_cruza.refresh_from_db()
    assert termina_justo.affected_by_block is None
    assert se_cruza.affected_by_block is not None


@pytest.mark.parametrize(
    "estado", [Cita.Estado.CANCELLED, Cita.Estado.COMPLETED, Cita.Estado.NO_SHOW]
)
def test_no_marca_citas_que_ya_no_estan_vigentes(admin_api, agenda, make_user, estado):
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    c = cita(barbero, servicio, a_las(inicio, 10), cliente=ana, estado=estado)

    bloquear_dia(admin_api, barbero, inicio)

    c.refresh_from_db()
    assert c.affected_by_block is None
    assert mail.outbox == []


def test_no_marca_citas_que_ya_pasaron(admin_api, agenda, make_user):
    barbero, servicio, _ = agenda
    (ana,) = clientes(make_user, 1)
    ahora = timezone.now()
    pasada = cita(barbero, servicio, ahora - timedelta(hours=1), cliente=ana)

    bloquear_dia(
        admin_api, barbero, ahora - timedelta(hours=3), ahora + timedelta(hours=8)
    )

    pasada.refresh_from_db()
    assert pasada.affected_by_block is None
    assert mail.outbox == []


def test_visitante_sin_cuenta_se_marca_y_se_devuelve_sin_canal_de_aviso(
    admin_api, agenda, make_user
):
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    cita(barbero, servicio, a_las(inicio, 10), cliente=ana)
    visitante = cita(
        barbero,
        servicio,
        a_las(inicio, 11),
        contact_name="Luis Perez",
        contact_phone="3001112233",
    )

    respuesta = bloquear_dia(admin_api, barbero, inicio)

    visitante.refresh_from_db()
    assert visitante.affected_by_block is not None
    assert visitante.block_notice_sent_at is None
    assert len(mail.outbox) == 1  # solo la cuenta registrada
    resumen = respuesta.data["affected_appointments"]
    assert resumen["total"] == 2
    assert resumen["notified"] == 1
    assert resumen["pending"] == 0  # no hay forma de avisarle: no es "pendiente"
    assert resumen["without_channel"] == [
        {
            "id": visitante.pk,
            "contact_name": "Luis Perez",
            "contact_phone": "3001112233",
            "start_at": visitante.start_at.astimezone(
                ZONA_HORARIA_BARBERIA
            ).isoformat(),
        }
    ]


def test_si_el_envio_falla_el_bloqueo_se_crea_y_la_cita_queda_pendiente(
    admin_api, agenda, make_user
):
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    c = cita(barbero, servicio, a_las(inicio, 10), cliente=ana)

    with mock.patch(
        "django.core.mail.EmailMultiAlternatives.send", side_effect=SMTPException
    ):
        respuesta = bloquear_dia(admin_api, barbero, inicio)

    assert respuesta.status_code == 201
    assert BloqueoAgenda.objects.count() == 1
    c.refresh_from_db()
    assert c.affected_by_block is not None
    assert c.block_notice_sent_at is None
    assert respuesta.data["affected_appointments"]["pending"] == 1
    assert EmailDelivery.objects.get().status == EmailDelivery.Status.FAILED


def test_reintentar_avisa_solo_a_los_pendientes_sin_duplicar(
    admin_api, agenda, make_user
):
    barbero, servicio, inicio = agenda
    ana, beto = clientes(make_user, 2)
    cita(barbero, servicio, a_las(inicio, 10), cliente=ana)
    pendiente = cita(barbero, servicio, a_las(inicio, 11), cliente=beto)

    # El primer envio sale bien y el segundo falla
    with mock.patch(
        "django.core.mail.EmailMultiAlternatives.send", side_effect=[1, SMTPException]
    ):
        bloquear_dia(admin_api, barbero, inicio)
    pendiente.refresh_from_db()
    assert pendiente.block_notice_sent_at is None

    resumen = services.notificar_citas_afectadas(BloqueoAgenda.objects.get())

    pendiente.refresh_from_db()
    assert pendiente.block_notice_sent_at is not None
    assert resumen["pending"] == 0
    assert resumen["notified"] == 2


def test_un_segundo_bloqueo_no_vuelve_a_avisar_citas_ya_avisadas(
    admin_api, agenda, make_user
):
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    c = cita(barbero, servicio, a_las(inicio, 10), cliente=ana)
    bloquear_dia(admin_api, barbero, inicio)
    primer_bloqueo = BloqueoAgenda.objects.get()
    mail.outbox.clear()

    bloquear_dia(admin_api, barbero, a_las(inicio, 9), a_las(inicio, 12))

    assert mail.outbox == []
    c.refresh_from_db()
    assert c.affected_by_block == primer_bloqueo


def test_borrar_el_bloqueo_no_borra_la_cita(admin_api, agenda, make_user):
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    c = cita(barbero, servicio, a_las(inicio, 10), cliente=ana)
    respuesta = bloquear_dia(admin_api, barbero, inicio)

    borrado = admin_api.delete(f"{BLOCKS}/{respuesta.data['id']}")

    assert borrado.status_code == 204
    c.refresh_from_db()
    assert c.affected_by_block is None
    assert c.status == Cita.Estado.PENDING


def test_la_cita_afectada_sigue_activa(admin_api, agenda, make_user):
    # El cliente decide: la cita no se cancela ni se mueve sola.
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    c = cita(barbero, servicio, a_las(inicio, 10), cliente=ana)

    bloquear_dia(admin_api, barbero, inicio)

    c.refresh_from_db()
    assert c.status == Cita.Estado.PENDING
    assert c.start_at == a_las(inicio, 10)


def test_sin_citas_en_el_periodo_el_bloqueo_responde_con_cero_afectadas(
    admin_api, agenda
):
    barbero, _, inicio = agenda

    respuesta = bloquear_dia(admin_api, barbero, inicio)

    assert respuesta.status_code == 201
    assert respuesta.data["affected_appointments"] == {
        "total": 0,
        "notified": 0,
        "pending": 0,
        "without_channel": [],
    }
    assert mail.outbox == []


def test_el_listado_muestra_el_estado_de_aviso_de_cada_bloqueo(
    admin_api, agenda, make_user
):
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    cita(barbero, servicio, a_las(inicio, 10), cliente=ana)
    creado = bloquear_dia(admin_api, barbero, inicio)

    listado = admin_api.get(BLOCKS)

    assert listado.data == [creado.data]
    assert listado.data[0]["affected_appointments"]["notified"] == 1


def test_el_listado_no_hace_una_consulta_por_bloqueo(
    admin_api, agenda, make_user, django_assert_max_num_queries
):
    barbero, servicio, inicio = agenda
    (ana,) = clientes(make_user, 1)
    for i in range(4):
        dia = inicio + timedelta(days=7 * (i + 1))
        cita(barbero, servicio, a_las(dia, 10), cliente=ana)
        bloquear_dia(admin_api, barbero, dia)

    with django_assert_max_num_queries(8):
        respuesta = admin_api.get(BLOCKS)

    assert len(respuesta.data) == 4
