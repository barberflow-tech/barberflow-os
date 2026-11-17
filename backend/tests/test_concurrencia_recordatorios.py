"""Concurrencia real de los recordatorios contra PostgreSQL (SCRUM-63).

Usan django_db(transaction=True): cada hilo abre su propia conexion y sus
transacciones hacen COMMIT de verdad (ver test_concurrencia_cancelar_cita.py).
"""

import threading
from datetime import datetime, timedelta
from datetime import timezone as zona_utc
from decimal import Decimal

import pytest
from django.core import mail
from django.db import connection

from apps.barberias.models import Barberia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas import services_recordatorios
from apps.citas.models import Cita, RecordatorioCita

AHORA = datetime(2026, 11, 20, 15, 0, tzinfo=zona_utc.utc)


@pytest.fixture
def cita(django_user_model):
    cliente = django_user_model.objects.create_user(
        username="cliente", email="cliente@example.com", password="x"
    )
    barberia = Barberia.objects.create(name="Barberia Centro")
    barbero = Barbero.objects.create(barberia=barberia, name="Juan")
    servicio = Servicio.objects.create(
        barberia=barberia,
        name="Corte Clasico",
        price=Decimal("25000.00"),
        duration_minutes=30,
    )
    inicio = AHORA + timedelta(hours=24)
    return Cita.objects.create(
        barberia=barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        price=servicio.price,
    )


@pytest.mark.django_db(transaction=True)
def test_dos_ejecuciones_simultaneas_envian_un_solo_correo(cita):
    # Dado dos cron que se solapan y buscan la misma cita a la vez
    barrera = threading.Barrier(2)
    resumenes: list[services_recordatorios.ResumenRecordatorios] = []

    def ejecutar():
        try:
            barrera.wait()
            resumenes.append(services_recordatorios.enviar_recordatorios(ahora=AHORA))
        finally:
            connection.close()

    hilos = [threading.Thread(target=ejecutar) for _ in range(2)]
    for hilo in hilos:
        hilo.start()
    for hilo in hilos:
        hilo.join(timeout=30)

    # Entonces el cliente recibe un solo correo y queda un solo registro
    assert len(resumenes) == 2
    assert sum(r.enviados for r in resumenes) == 1
    assert len(mail.outbox) == 1
    registro = RecordatorioCita.objects.get(appointment=cita)
    assert registro.sent_at is not None
    assert registro.attempts == 1
