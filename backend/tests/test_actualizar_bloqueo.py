"""HU-04: el administrador edita un bloqueo de agenda (PUT /api/v1/blocks/{id}).

Al mover el bloqueo, las citas que ya no caen dentro dejan de estar afectadas y
las que ahora caen dentro quedan marcadas (y avisadas), sin cancelar nada.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Membresia
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.models import BloqueoAgenda, Cita
from apps.citas.services import ZONA_HORARIA_BARBERIA

pytestmark = pytest.mark.django_db

BLOCKS = "/api/v1/blocks"


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


def a_las(inicio, hora):
    return inicio.replace(hour=hora)


def cita(barbero, servicio, inicio, cliente):
    return Cita.objects.create(
        barberia=barbero.barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        status=Cita.Estado.PENDING,
        price=Decimal("25000"),
    )


def bloquear(api, barbero, desde, hasta, motivo="Incapacidad"):
    return api.post(
        BLOCKS,
        {
            "barber": barbero.pk,
            "start_at": desde.isoformat(),
            "end_at": hasta.isoformat(),
            "reason": motivo,
        },
        format="json",
    )


def datos(barbero, desde, hasta, motivo="Incapacidad"):
    return {
        "barber": barbero.pk,
        "start_at": desde.isoformat(),
        "end_at": hasta.isoformat(),
        "reason": motivo,
    }


def test_editar_cambia_el_rango_y_el_motivo(admin_api, agenda):
    barbero, _, inicio = agenda
    creado = bloquear(admin_api, barbero, a_las(inicio, 9), a_las(inicio, 12))

    respuesta = admin_api.put(
        f"{BLOCKS}/{creado.data['id']}",
        datos(barbero, a_las(inicio, 14), a_las(inicio, 16), "Cita médica"),
        format="json",
    )

    assert respuesta.status_code == 200
    assert respuesta.data["id"] == creado.data["id"]
    assert respuesta.data["start_at"] == a_las(inicio, 14).isoformat()
    assert respuesta.data["reason"] == "Cita médica"
    assert BloqueoAgenda.objects.count() == 1


def test_al_mover_el_bloqueo_las_citas_fuera_dejan_de_estar_afectadas(
    admin_api, agenda, django_user_model
):
    barbero, servicio, inicio = agenda
    cliente = django_user_model.objects.create_user(
        username="c1", email="c1@x.test", password="x"
    )
    dentro = cita(barbero, servicio, a_las(inicio, 10), cliente)
    creado = bloquear(admin_api, barbero, a_las(inicio, 9), a_las(inicio, 12))
    dentro.refresh_from_db()
    assert dentro.affected_by_block_id == creado.data["id"]

    admin_api.put(
        f"{BLOCKS}/{creado.data['id']}",
        datos(barbero, a_las(inicio, 14), a_las(inicio, 16)),
        format="json",
    )

    dentro.refresh_from_db()
    assert dentro.affected_by_block_id is None
    assert dentro.status == Cita.Estado.PENDING


def test_al_mover_el_bloqueo_las_citas_nuevas_quedan_marcadas_y_avisadas(
    admin_api, agenda, django_user_model
):
    barbero, servicio, inicio = agenda
    cliente = django_user_model.objects.create_user(
        username="c2", email="c2@x.test", password="x"
    )
    fuera = cita(barbero, servicio, a_las(inicio, 15), cliente)
    creado = bloquear(admin_api, barbero, a_las(inicio, 9), a_las(inicio, 12))
    fuera.refresh_from_db()
    assert fuera.affected_by_block_id is None
    mail.outbox.clear()

    respuesta = admin_api.put(
        f"{BLOCKS}/{creado.data['id']}",
        datos(barbero, a_las(inicio, 14), a_las(inicio, 17)),
        format="json",
    )

    fuera.refresh_from_db()
    assert fuera.affected_by_block_id == creado.data["id"]
    assert fuera.block_notice_sent_at is not None
    assert respuesta.data["affected_appointments"]["total"] == 1
    assert [m.to for m in mail.outbox] == [["c2@x.test"]]


def test_editar_con_intervalo_invalido_retorna_400(admin_api, agenda):
    barbero, _, inicio = agenda
    creado = bloquear(admin_api, barbero, a_las(inicio, 9), a_las(inicio, 12))

    respuesta = admin_api.put(
        f"{BLOCKS}/{creado.data['id']}",
        datos(barbero, a_las(inicio, 12), a_las(inicio, 9)),
        format="json",
    )

    assert respuesta.status_code == 400
    assert "end_at" in respuesta.data


def test_editar_un_bloqueo_inexistente_retorna_404(admin_api, agenda):
    barbero, _, inicio = agenda

    respuesta = admin_api.put(
        f"{BLOCKS}/999999",
        datos(barbero, a_las(inicio, 9), a_las(inicio, 12)),
        format="json",
    )

    assert respuesta.status_code == 404


@pytest.mark.parametrize(
    "rol, codigo", [("cliente", 403), ("barbero", 403), (None, 401)]
)
def test_solo_el_administrador_puede_editar(agenda, make_user, rol, codigo):
    barbero, _, inicio = agenda
    api = APIClient()
    if rol:
        api.force_authenticate(user=make_user(rol))

    respuesta = api.put(
        f"{BLOCKS}/1",
        datos(barbero, a_las(inicio, 9), a_las(inicio, 12)),
        format="json",
    )

    assert respuesta.status_code == codigo


def test_al_editar_no_se_reenvia_el_aviso_a_quien_sigue_afectado(
    admin_api, agenda, django_user_model
):
    barbero, servicio, inicio = agenda
    cliente = django_user_model.objects.create_user(
        username="c3", email="c3@x.test", password="x"
    )
    cita(barbero, servicio, a_las(inicio, 10), cliente)
    creado = bloquear(admin_api, barbero, a_las(inicio, 9), a_las(inicio, 12))
    assert len(mail.outbox) == 1
    mail.outbox.clear()

    admin_api.put(
        f"{BLOCKS}/{creado.data['id']}",
        datos(barbero, a_las(inicio, 9), a_las(inicio, 13), "Cambió el motivo"),
        format="json",
    )

    assert mail.outbox == []


def test_al_reprogramar_la_cita_afectada_deja_de_estar_marcada(
    admin_api, agenda, django_user_model
):
    barbero, servicio, inicio = agenda
    cliente = django_user_model.objects.create_user(
        username="c4", email="c4@x.test", password="x"
    )
    afectada = cita(barbero, servicio, a_las(inicio, 10), cliente)
    creado = bloquear(admin_api, barbero, a_las(inicio, 9), a_las(inicio, 12))
    afectada.refresh_from_db()
    assert afectada.affected_by_block_id == creado.data["id"]
    api = APIClient()
    api.force_authenticate(user=cliente)

    respuesta = api.post(
        f"/api/v1/appointments/{afectada.pk}/reschedule",
        {"start_at": a_las(inicio, 15).isoformat()},
        format="json",
    )

    assert respuesta.status_code == 200
    afectada.refresh_from_db()
    assert afectada.affected_by_block_id is None
    assert api.get("/api/v1/appointments").data[0]["affected_by_block"] is False
