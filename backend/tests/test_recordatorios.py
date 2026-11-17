"""Recordatorios de citas a las 24 h y 2 h (HU-05 / SCRUM-63).

Cubre el servicio `enviar_recordatorios` y el comando `enviar_recordatorios`.
El tiempo se simula inyectando `ahora`; el correo usa el backend `locmem` de
las pruebas, asi que no hay envios reales. La concurrencia vive en
test_concurrencia_recordatorios.py porque exige transaction=True.

Ventanas (margen de gracia de 30 min): el aviso de 24 h sale cuando faltan mas
de 23 h 30 min y hasta 24 h; el de 2 h, cuando faltan mas de 1 h 30 min y
hasta 2 h.
"""

from datetime import datetime, timedelta
from datetime import timezone as zona_utc
from decimal import Decimal
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas import services, services_recordatorios
from apps.citas.models import Cita, RecordatorioCita
from apps.notificaciones.models import EmailDelivery

pytestmark = pytest.mark.django_db

# 15:00 UTC = 10:00 en Bogota (UTC-5, sin horario de verano).
AHORA = datetime(2026, 11, 20, 15, 0, tzinfo=zona_utc.utc)
H24 = RecordatorioCita.Tipo.REMINDER_24H
H2 = RecordatorioCita.Tipo.REMINDER_2H


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def servicio(barberia):
    return Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=Decimal("35000.00"),
        duration_minutes=30,
    )


@pytest.fixture
def cliente(django_user_model):
    return django_user_model.objects.create_user(
        username="cliente", email="cliente@example.com", password="x"
    )


@pytest.fixture
def crear_cita(barberia, servicio, cliente):
    """Fabrica de citas. Cada una usa un barbero nuevo: no se solapan nunca."""

    def _crear(
        *, inicio, estado=Cita.Estado.PENDING, client=cliente, service=servicio, **extra
    ) -> Cita:
        barbero = Barbero.objects.create(
            barberia=barberia, name=f"Barbero {Barbero.objects.count()}"
        )
        return Cita.objects.create(
            barberia=barberia,
            client=client,
            barber=barbero,
            service=service,
            start_at=inicio,
            end_at=inicio + timedelta(minutes=30),
            status=estado,
            price=service.price,
            **extra,
        )

    return _crear


# --- Ventanas ---------------------------------------------------------------


@pytest.mark.parametrize(
    "faltan,se_envia",
    [
        (timedelta(hours=24), True),
        (timedelta(hours=23, minutes=31), True),
        (timedelta(hours=23, minutes=30), False),
        (timedelta(hours=24, seconds=1), False),
    ],
)
def test_enviar_aviso_de_24_horas_solo_dentro_de_la_ventana(
    crear_cita, faltan, se_envia
):
    # Dado una cita pendiente a `faltan` de distancia
    crear_cita(inicio=AHORA + faltan)

    # Cuando corre la tarea programada
    resumen = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    # Entonces recibe el aviso de 24 h solo si cae dentro de la ventana
    assert len(mail.outbox) == (1 if se_envia else 0)
    assert resumen.enviados == (1 if se_envia else 0)
    assert RecordatorioCita.objects.filter(reminder_type=H24).count() == (
        1 if se_envia else 0
    )


@pytest.mark.parametrize(
    "faltan,se_envia",
    [
        (timedelta(hours=2), True),
        (timedelta(hours=1, minutes=31), True),
        (timedelta(hours=1, minutes=30), False),
        (timedelta(hours=2, minutes=1), False),
    ],
)
def test_enviar_aviso_de_2_horas_solo_dentro_de_la_ventana(
    crear_cita, faltan, se_envia
):
    crear_cita(inicio=AHORA + faltan)

    services_recordatorios.enviar_recordatorios(ahora=AHORA)

    assert len(mail.outbox) == (1 if se_envia else 0)
    assert RecordatorioCita.objects.filter(reminder_type=H2).count() == (
        1 if se_envia else 0
    )


def test_omitir_aviso_de_24_horas_en_reserva_tardia(crear_cita):
    # Dado una cita reservada con solo 5 h de antelacion
    crear_cita(inicio=AHORA + timedelta(hours=5))

    # Cuando corre la tarea
    services_recordatorios.enviar_recordatorios(ahora=AHORA)

    # Entonces no recibe un "faltan 24 horas" absurdo
    assert mail.outbox == []
    assert RecordatorioCita.objects.count() == 0


def test_omitir_citas_pasadas_o_con_menos_de_90_minutos(crear_cita):
    crear_cita(inicio=AHORA - timedelta(hours=1))
    crear_cita(inicio=AHORA + timedelta(minutes=45))

    services_recordatorios.enviar_recordatorios(ahora=AHORA)

    assert mail.outbox == []


# --- Estados ----------------------------------------------------------------


@pytest.mark.parametrize(
    "estado,se_envia",
    [
        (Cita.Estado.PENDING, True),
        (Cita.Estado.CONFIRMED, True),
        (Cita.Estado.CANCELLED, False),
        (Cita.Estado.COMPLETED, False),
        (Cita.Estado.NO_SHOW, False),
    ],
)
def test_recordar_solo_citas_activas(crear_cita, estado, se_envia):
    crear_cita(inicio=AHORA + timedelta(hours=24), estado=estado)

    services_recordatorios.enviar_recordatorios(ahora=AHORA)

    assert len(mail.outbox) == (1 if se_envia else 0)


def test_no_enviar_a_cita_cancelada_con_el_servicio_real(crear_cita, cliente):
    # Dado una cita en ventana que su propietario cancela de verdad
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))
    services.cancelar_cita(cita_id=cita.pk, usuario=cliente, ahora=AHORA)

    # Cuando corre la tarea
    services_recordatorios.enviar_recordatorios(ahora=AHORA)

    # Entonces no recibe ningun correo ni queda registro
    assert mail.outbox == []
    assert RecordatorioCita.objects.count() == 0


def test_omitir_cita_cancelada_entre_la_busqueda_y_el_envio(crear_cita):
    # Dado una cita que la busqueda encuentra como candidata
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))
    assert cita in services_recordatorios.buscar_citas_a_recordar(H24, AHORA)

    # Cuando se cancela justo antes de que se procese
    Cita.objects.filter(pk=cita.pk).update(status=Cita.Estado.CANCELLED)
    resultado = services_recordatorios.enviar_recordatorio_de_cita(
        cita_id=cita.pk, tipo=H24, ahora=AHORA
    )

    # Entonces se revalida con la cita bloqueada y no se envia
    assert resultado == services_recordatorios.ResultadoAviso.OMITIDO
    assert mail.outbox == []
    assert RecordatorioCita.objects.count() == 0


def test_omitir_cita_reprogramada_fuera_de_ventana_tras_la_busqueda(crear_cita):
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))
    lejos = AHORA + timedelta(days=3)
    Cita.objects.filter(pk=cita.pk).update(
        start_at=lejos, end_at=lejos + timedelta(minutes=30)
    )

    resultado = services_recordatorios.enviar_recordatorio_de_cita(
        cita_id=cita.pk, tipo=H24, ahora=AHORA
    )

    assert resultado == services_recordatorios.ResultadoAviso.OMITIDO
    assert mail.outbox == []


# --- Canal ------------------------------------------------------------------


def test_contar_visitante_sin_cuenta_como_sin_canal(crear_cita):
    # Dado una cita de visitante: solo nombre y celular, sin correo
    crear_cita(
        inicio=AHORA + timedelta(hours=24),
        client=None,
        contact_name="Visitante",
        contact_phone="3001234567",
    )

    resumen = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    assert resumen.sin_canal == 1
    assert resumen.enviados == 0
    assert mail.outbox == []
    assert RecordatorioCita.objects.count() == 0


def test_contar_cliente_sin_correo_como_sin_canal(crear_cita, django_user_model):
    sin_correo = django_user_model.objects.create_user(
        username="sincorreo", password="x"
    )
    crear_cita(inicio=AHORA + timedelta(hours=24), client=sin_correo)

    resumen = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    assert resumen.sin_canal == 1
    assert mail.outbox == []


# --- Sin duplicados ---------------------------------------------------------


def test_no_repetir_recordatorio_en_la_segunda_ejecucion(crear_cita):
    crear_cita(inicio=AHORA + timedelta(hours=24))

    primera = services_recordatorios.enviar_recordatorios(ahora=AHORA)
    segunda = services_recordatorios.enviar_recordatorios(ahora=AHORA)
    tercera = services_recordatorios.enviar_recordatorios(
        ahora=AHORA + timedelta(minutes=10)
    )

    assert (primera.enviados, segunda.enviados, tercera.enviados) == (1, 0, 0)
    assert len(mail.outbox) == 1
    assert RecordatorioCita.objects.count() == 1


def test_enviar_los_dos_avisos_de_la_misma_cita_una_vez_cada_uno(crear_cita):
    # Dado una cita a 24 h de distancia
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))

    # Cuando corre la tarea a 24 h y otra vez a 2 h de la cita
    services_recordatorios.enviar_recordatorios(ahora=AHORA)
    dos_horas_antes = cita.start_at - timedelta(hours=2)
    services_recordatorios.enviar_recordatorios(ahora=dos_horas_antes)
    services_recordatorios.enviar_recordatorios(ahora=dos_horas_antes)

    # Entonces salen exactamente dos correos, uno por tipo
    assert len(mail.outbox) == 2
    tipos = set(
        RecordatorioCita.objects.filter(appointment=cita).values_list(
            "reminder_type", flat=True
        )
    )
    assert tipos == {H24, H2}


def test_reintentar_si_el_envio_fallo_sin_duplicar(crear_cita):
    # Dado un proveedor que rechaza el primer envio
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))
    with patch(
        "django.core.mail.backends.locmem.EmailBackend.send_messages",
        return_value=0,
    ):
        primera = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    registro = RecordatorioCita.objects.get(appointment=cita)
    assert primera.fallidos == 1
    assert registro.sent_at is None
    assert registro.attempts == 1
    assert registro.delivery.status == EmailDelivery.Status.FAILED

    # Cuando el proveedor se recupera en la siguiente ejecucion
    segunda = services_recordatorios.enviar_recordatorios(
        ahora=AHORA + timedelta(minutes=10)
    )
    tercera = services_recordatorios.enviar_recordatorios(
        ahora=AHORA + timedelta(minutes=20)
    )

    # Entonces se envia una sola vez y deja de reintentarse
    registro.refresh_from_db()
    assert (segunda.enviados, tercera.enviados) == (1, 0)
    assert len(mail.outbox) == 1
    assert registro.attempts == 2
    assert registro.sent_at is not None
    assert registro.delivery.status == EmailDelivery.Status.SENT
    assert RecordatorioCita.objects.count() == 1


def test_cita_reprogramada_recibe_el_recordatorio_de_la_nueva_hora(crear_cita):
    # Dado una cita que ya recibio su aviso de 24 h
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))
    services_recordatorios.enviar_recordatorios(ahora=AHORA)
    assert len(mail.outbox) == 1

    # Cuando se reprograma 3 dias despues y llega la nueva ventana de 24 h
    nueva_hora = AHORA + timedelta(days=4)
    Cita.objects.filter(pk=cita.pk).update(
        start_at=nueva_hora, end_at=nueva_hora + timedelta(minutes=30)
    )
    services_recordatorios.enviar_recordatorios(ahora=nueva_hora - timedelta(hours=24))

    # Entonces recibe un segundo aviso, ligado a la hora nueva
    assert len(mail.outbox) == 2
    horas = set(
        RecordatorioCita.objects.filter(appointment=cita).values_list(
            "appointment_start_at", flat=True
        )
    )
    assert horas == {AHORA + timedelta(hours=24), nueva_hora}


# --- Registro ---------------------------------------------------------------


def test_registrar_el_envio_con_su_entrega(crear_cita):
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))

    services_recordatorios.enviar_recordatorios(ahora=AHORA)

    registro = RecordatorioCita.objects.get(appointment=cita)
    assert registro.reminder_type == H24
    assert registro.appointment_start_at == cita.start_at
    assert registro.attempts == 1
    assert registro.sent_at is not None
    assert registro.delivery.recipient == "cliente@example.com"
    assert registro.delivery.status == EmailDelivery.Status.SENT
    assert registro.delivery.subject == mail.outbox[0].subject


# --- Contenido y zona horaria -----------------------------------------------


def test_correo_muestra_los_detalles_de_la_reserva_en_hora_de_bogota(crear_cita):
    # Dado una cita a las 15:00 UTC, que son las 10:00 en Bogota
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))

    services_recordatorios.enviar_recordatorios(ahora=AHORA)

    correo = mail.outbox[0]
    assert correo.to == ["cliente@example.com"]
    for dato in (
        "Corte Clasico",
        cita.barber.name,
        "21/11/2026",
        "10:00",
        "$35.000",
        "/perfil",
        "24 horas",
    ):
        assert dato in correo.body, dato
    assert "21/11/2026" in correo.subject
    assert correo.alternatives[0][1] == "text/html"


def test_correo_usa_la_fecha_local_cuando_cambia_el_dia_en_utc(crear_cita):
    # Dado una cita a las 03:00 UTC del 21, que en Bogota son las 22:00 del 20
    inicio = datetime(2026, 11, 21, 3, 0, tzinfo=zona_utc.utc)
    crear_cita(inicio=inicio)

    services_recordatorios.enviar_recordatorios(ahora=inicio - timedelta(hours=2))

    cuerpo = mail.outbox[0].body
    assert "20/11/2026" in cuerpo
    assert "22:00" in cuerpo
    assert "2 horas" in cuerpo


def test_correo_html_escapa_los_nombres_del_servicio(barberia, crear_cita):
    peligroso = Servicio.objects.create(
        barberia=barberia,
        name="<b>Corte</b> & barba",
        price=Decimal("20000.00"),
        duration_minutes=30,
    )
    crear_cita(inicio=AHORA + timedelta(hours=24), service=peligroso)

    services_recordatorios.enviar_recordatorios(ahora=AHORA)

    html = mail.outbox[0].alternatives[0][0]
    assert "&lt;b&gt;Corte&lt;/b&gt; &amp; barba" in html
    assert "<b>Corte</b>" not in html


# --- Comando (integracion) --------------------------------------------------


def test_comando_envia_los_recordatorios_y_muestra_el_resumen(crear_cita):
    # Dado una cita a 23 h 45 min de ahora (tiempo real)
    crear_cita(inicio=timezone.now() + timedelta(hours=23, minutes=45))
    salida = StringIO()

    # Cuando corre el comando que programa el cron
    call_command("enviar_recordatorios", stdout=salida)

    # Entonces envia un correo y lo cuenta en el resumen
    assert len(mail.outbox) == 1
    assert "Enviados: 1" in salida.getvalue()


def test_comando_repetido_no_duplica_correos(crear_cita):
    crear_cita(inicio=timezone.now() + timedelta(hours=23, minutes=45))
    salida = StringIO()

    call_command("enviar_recordatorios", stdout=StringIO())
    call_command("enviar_recordatorios", stdout=salida)

    assert len(mail.outbox) == 1
    assert "Enviados: 0" in salida.getvalue()


def test_comando_termina_con_error_si_hubo_fallos_de_base_de_datos():
    resumen = services_recordatorios.ResumenRecordatorios(errores=1)

    with patch(
        "apps.citas.management.commands.enviar_recordatorios.enviar_recordatorios",
        return_value=resumen,
    ):
        with pytest.raises(CommandError):
            call_command("enviar_recordatorios", stdout=StringIO())


# ============================================================================
# Validacion de HU-05: los seis casos de aceptacion (SCRUM-63)
# ============================================================================

CORREO_CLIENTE = "cliente@example.com"


# --- CASO 1: cita confirmada a 24 horas -> se envia el correo ---------------


def test_caso_1_cita_confirmada_a_24_horas_envia_el_correo(crear_cita):
    # Dado una cita CONFIRMED a 24 horas
    crear_cita(inicio=AHORA + timedelta(hours=24), estado=Cita.Estado.CONFIRMED)

    # Cuando corre el job
    resumen = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    # Entonces se envia un correo al cliente con el aviso de 24 horas
    assert resumen.enviados == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [CORREO_CLIENTE]
    assert "24 horas" in mail.outbox[0].body
    assert RecordatorioCita.objects.get().reminder_type == H24


# --- CASO 2: cita confirmada a 2 horas -> se envia el correo ----------------


def test_caso_2_cita_confirmada_a_2_horas_envia_el_correo(crear_cita):
    crear_cita(inicio=AHORA + timedelta(hours=2), estado=Cita.Estado.CONFIRMED)

    resumen = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    assert resumen.enviados == 1
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [CORREO_CLIENTE]
    assert "2 horas" in mail.outbox[0].body
    assert RecordatorioCita.objects.get().reminder_type == H2


# --- CASO 3: correo ya enviado -> no se envia de nuevo ----------------------


def test_caso_3_correo_ya_enviado_no_se_envia_de_nuevo(crear_cita):
    # Dado una cita cuyo aviso de 24 h ya se envio antes
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))
    enviado_antes = RecordatorioCita.objects.create(
        appointment=cita,
        reminder_type=H24,
        appointment_start_at=cita.start_at,
        attempts=1,
        sent_at=AHORA - timedelta(minutes=10),
    )

    # Cuando vuelve a correr el job dentro de la misma ventana
    resumen = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    # Entonces no se envia nada y el registro original no cambia
    assert resumen.enviados == 0
    assert mail.outbox == []
    enviado_antes.refresh_from_db()
    assert enviado_antes.attempts == 1
    assert RecordatorioCita.objects.count() == 1


# --- CASO 4: cita cancelada -> no se envia correo ---------------------------


def test_caso_4_cita_cancelada_no_recibe_ningun_aviso(crear_cita):
    crear_cita(inicio=AHORA + timedelta(hours=24), estado=Cita.Estado.CANCELLED)
    crear_cita(inicio=AHORA + timedelta(hours=2), estado=Cita.Estado.CANCELLED)

    resumen = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    assert resumen.enviados == 0
    assert mail.outbox == []
    assert RecordatorioCita.objects.count() == 0


def test_caso_4_cita_cancelada_despues_del_primer_aviso_no_recibe_el_de_2_horas(
    crear_cita, cliente
):
    # Dado una cita que ya recibio su aviso de 24 h
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))
    services_recordatorios.enviar_recordatorios(ahora=AHORA)
    assert len(mail.outbox) == 1

    # Cuando el cliente la cancela y llega la ventana de 2 h
    services.cancelar_cita(cita_id=cita.pk, usuario=cliente, ahora=AHORA)
    services_recordatorios.enviar_recordatorios(
        ahora=cita.start_at - timedelta(hours=2)
    )

    # Entonces no recibe el segundo correo
    assert len(mail.outbox) == 1
    assert RecordatorioCita.objects.filter(reminder_type=H2).count() == 0


# --- CASO 5: multiples ejecuciones del job -> sin duplicados ----------------


def test_caso_5_job_cada_10_minutos_durante_todo_el_dia_no_duplica(crear_cita):
    # Dado una cita a 24 h y un cron que corre cada 10 minutos hasta la cita
    cita = crear_cita(inicio=AHORA + timedelta(hours=24))

    for minutos in range(0, 24 * 60 + 1, 10):
        services_recordatorios.enviar_recordatorios(
            ahora=AHORA + timedelta(minutes=minutos)
        )

    # Entonces recibe exactamente dos correos: uno de 24 h y uno de 2 h
    assert len(mail.outbox) == 2
    registros = RecordatorioCita.objects.filter(appointment=cita)
    assert {r.reminder_type for r in registros} == {H24, H2}
    assert all(r.attempts == 1 and r.sent_at is not None for r in registros)


def test_caso_5_varias_citas_y_varias_ejecuciones_envian_un_correo_por_cita(
    crear_cita, django_user_model
):
    otro = django_user_model.objects.create_user(
        username="otro", email="otro@example.com", password="x"
    )
    crear_cita(inicio=AHORA + timedelta(hours=24))
    crear_cita(inicio=AHORA + timedelta(hours=24), client=otro)

    for _ in range(5):
        services_recordatorios.enviar_recordatorios(ahora=AHORA)

    assert len(mail.outbox) == 2
    assert {m.to[0] for m in mail.outbox} == {CORREO_CLIENTE, "otro@example.com"}


# --- CASO 6: cambio de zona horaria -> la ventana sigue siendo correcta -----


@pytest.mark.parametrize(
    "zona", ["UTC", "America/Bogota", "Asia/Tokyo", "Pacific/Auckland"]
)
def test_caso_6_la_ventana_no_depende_de_la_zona_de_ahora(crear_cita, zona):
    # Dado una cita a 24 h absolutas y un "ahora" expresado en otra zona
    crear_cita(inicio=AHORA + timedelta(hours=24))
    ahora_en_zona = AHORA.astimezone(ZoneInfo(zona))

    # Cuando corre el job con ese "ahora"
    resumen = services_recordatorios.enviar_recordatorios(ahora=ahora_en_zona)

    # Entonces la cita cae en la ventana de 24 h, igual que en UTC
    assert resumen.enviados == 1


@pytest.mark.parametrize(
    "ahora_local",
    [
        # Nueva York adelanta el reloj el 8-mar-2026: ese dia dura 23 h.
        datetime(2026, 3, 7, 12, 0, tzinfo=ZoneInfo("America/New_York")),
        # Y lo atrasa el 1-nov-2026: ese dia dura 25 h.
        datetime(2026, 10, 31, 12, 0, tzinfo=ZoneInfo("America/New_York")),
    ],
    ids=["adelanta-el-reloj", "atrasa-el-reloj"],
)
def test_caso_6_ventana_correcta_al_cruzar_un_cambio_de_hora(crear_cita, ahora_local):
    # Dado una cita exactamente 24 h absolutas despues, aunque el reloj cambie
    inicio = ahora_local.astimezone(zona_utc.utc) + timedelta(hours=24)
    crear_cita(inicio=inicio)

    resumen = services_recordatorios.enviar_recordatorios(ahora=ahora_local)

    # Entonces se envia: la ventana se mide en tiempo absoluto, no en hora de pared
    assert resumen.enviados == 1


def test_caso_6_ahora_sin_zona_horaria_se_rechaza():
    with pytest.raises(ValueError):
        services_recordatorios.enviar_recordatorios(ahora=datetime(2026, 11, 20, 15, 0))


def test_caso_6_cita_agendada_desde_otra_zona_se_recuerda_igual(crear_cita):
    # Dado una cita cuya hora llega expresada en hora de Tokio
    inicio_tokio = (AHORA + timedelta(hours=24)).astimezone(ZoneInfo("Asia/Tokyo"))
    cita = crear_cita(inicio=inicio_tokio)

    resumen = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    # Entonces es el mismo instante: se envia y se guarda como el mismo momento
    assert resumen.enviados == 1
    assert RecordatorioCita.objects.get().appointment_start_at == cita.start_at


def test_caso_6_zona_activa_distinta_no_cambia_la_hora_del_correo(crear_cita):
    crear_cita(inicio=AHORA + timedelta(hours=24))

    with timezone.override("Asia/Tokyo"):
        services_recordatorios.enviar_recordatorios(ahora=AHORA)

    # La hora del correo es la de la barberia (Bogota), no la zona activa
    cuerpo = mail.outbox[0].body
    assert "10:00" in cuerpo
    assert "21/11/2026" in cuerpo


def test_caso_6_cambiar_time_zone_de_django_no_mueve_la_ventana(crear_cita, settings):
    settings.TIME_ZONE = "America/Bogota"
    crear_cita(inicio=AHORA + timedelta(hours=24))
    crear_cita(inicio=AHORA + timedelta(hours=23, minutes=30))  # borde: fuera

    resumen = services_recordatorios.enviar_recordatorios(ahora=AHORA)

    assert resumen.enviados == 1
    assert "10:00" in mail.outbox[0].body
