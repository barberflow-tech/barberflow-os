import threading
from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import DatabaseError, connection, transaction
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.barberias.models import Barberia, Membresia
from apps.barberos.models import Barbero
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

URL = "/api/v1/appointments"


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def otra_barberia():
    return Barberia.objects.create(name="Barberia Norte")


@pytest.fixture
def cliente(django_user_model, barberia):
    usuario = django_user_model.objects.create_user(username="cliente", password="x")
    Membresia.objects.create(user=usuario, barberia=barberia)
    return usuario


@pytest.fixture
def api(cliente):
    api = APIClient()
    api.force_authenticate(user=cliente)
    return api


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
    return (timezone.now() + timedelta(days=1)).replace(
        hour=15, minute=0, second=0, microsecond=0
    )


@pytest.fixture
def payload(barbero, servicio, inicio):
    return {
        "barber": barbero.pk,
        "service": servicio.pk,
        "start_at": inicio.isoformat(),
    }


@pytest.mark.django_db
def test_payload_valido_crea_cita_pending_y_retorna_201(api, cliente, payload):
    # Dado un payload de reserva valido
    # Cuando se envia POST /api/v1/appointments
    response = api.post(URL, payload, format="json")

    # Entonces se crea la cita PENDING y se retorna 201 con su ID
    assert response.status_code == 201
    cita = Cita.objects.get(pk=response.data["id"])
    assert cita.status == Cita.Estado.PENDING
    assert cita.client == cliente
    assert cita.barberia == cliente.membresia.barberia
    assert response.data["status"] == "PENDING"


@pytest.mark.django_db
def test_barbero_de_otra_barberia_retorna_400(api, payload, otra_barberia):
    # Dado un barbero activo de otra barberia cuyo ID conoce el usuario
    ajeno = Barbero.objects.create(barberia=otra_barberia, name="Pedro")
    payload["barber"] = ajeno.pk

    # Cuando intenta reservarlo
    response = api.post(URL, payload, format="json")

    # Entonces se responde como si no existiera y no se crea la cita
    assert response.status_code == 400
    assert "barber" in response.data
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_servicio_de_otra_barberia_retorna_400(api, payload, otra_barberia):
    ajeno = Servicio.objects.create(
        barberia=otra_barberia, name="Barba", price=1, duration_minutes=30
    )
    payload["service"] = ajeno.pk

    response = api.post(URL, payload, format="json")

    assert response.status_code == 400
    assert "service" in response.data
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_usuario_sin_barberia_retorna_403(django_user_model, payload):
    # Dado un usuario autenticado que no pertenece a ninguna barberia
    usuario = django_user_model.objects.create_user(username="suelto", password="x")
    api = APIClient()
    api.force_authenticate(user=usuario)

    # Cuando intenta reservar
    response = api.post(URL, payload, format="json")

    # Entonces se le niega el acceso y no se crea la cita
    assert response.status_code == 403
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_acepta_barra_final(api, payload):
    response = api.post(URL + "/", payload, format="json")

    assert response.status_code == 201


@pytest.mark.django_db
def test_autentica_con_jwt(cliente, payload):
    api = APIClient()
    token = RefreshToken.for_user(cliente).access_token
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    response = api.post(URL, payload, format="json")

    assert response.status_code == 201


@pytest.mark.django_db
def test_sin_autenticacion_retorna_401(payload):
    response = APIClient().post(URL, payload, format="json")

    assert response.status_code == 401
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_payload_invalido_retorna_400(api):
    response = api.post(URL, {"start_at": "no-es-fecha"}, format="json")

    assert response.status_code == 400
    assert {"barber", "service", "start_at"} <= set(response.data)
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_recurso_inexistente_retorna_400(api, payload):
    payload["barber"] = 999_999

    response = api.post(URL, payload, format="json")

    assert response.status_code == 400
    assert "barber" in response.data
    assert Cita.objects.count() == 0


@pytest.mark.django_db
def test_servicio_inactivo_retorna_400(api, payload, servicio):
    Servicio.objects.filter(pk=servicio.pk).update(is_active=False)

    response = api.post(URL, payload, format="json")

    assert response.status_code == 400
    assert "service" in response.data


@pytest.mark.django_db
def test_horario_pasado_retorna_400(api, payload):
    payload["start_at"] = (timezone.now() - timedelta(hours=1)).isoformat()

    response = api.post(URL, payload, format="json")

    assert response.status_code == 400
    assert "start_at" in response.data


@pytest.mark.django_db
def test_franja_ocupada_retorna_409(api, payload):
    # Dado una reserva existente en la misma franja
    assert api.post(URL, payload, format="json").status_code == 201

    # Cuando otro POST pide la misma franja
    response = api.post(URL, payload, format="json")

    # Entonces se responde 409 y no se crea una segunda cita
    assert response.status_code == 409
    assert response.data["detail"].code == "franja_no_disponible"
    assert Cita.objects.count() == 1


@pytest.mark.django_db
def test_franja_parcialmente_solapada_retorna_409(api, payload, inicio):
    # Dado una cita de 15:00 a 15:30
    assert api.post(URL, payload, format="json").status_code == 201

    # Cuando se pide 15:15 (se cruza con la existente)
    payload["start_at"] = (inicio + timedelta(minutes=15)).isoformat()
    response = api.post(URL, payload, format="json")

    # Entonces no se crea una segunda reserva incompatible
    assert response.status_code == 409
    assert Cita.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_fallo_al_guardar_hace_rollback_y_retorna_500(
    api, payload, barbero, monkeypatch
):
    # Dado que la BD falla justo despues de ejecutar el INSERT
    save_original = Cita.save
    ids_insertados = []

    def guardar_y_fallar(self, *args, **kwargs):
        save_original(self, *args, **kwargs)
        ids_insertados.append(self.pk)
        raise DatabaseError("fallo simulado durante el guardado")

    monkeypatch.setattr(Cita, "save", guardar_y_fallar)

    # Cuando se envia la reserva
    response = api.post(URL, payload, format="json")

    # Entonces se responde 500 en JSON...
    assert response.status_code == 500
    assert response.data["detail"].code == "error_al_guardar_cita"

    # ...el INSERT llego a PostgreSQL pero el ROLLBACK lo deshizo
    assert len(ids_insertados) == 1
    with connection.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) FROM citas_cita")
        assert cursor.fetchone() == (0,)

    # ...y el bloqueo del barbero quedo liberado: otra conexion lo toma
    # sin esperar (NOWAIT fallaria si la transaccion siguiera abierta).
    errores = []

    def tomar_bloqueo():
        try:
            with transaction.atomic():
                Barbero.objects.select_for_update(nowait=True).get(pk=barbero.pk)
        except DatabaseError as exc:
            errores.append(exc)
        finally:
            connection.close()

    hilo = threading.Thread(target=tomar_bloqueo)
    hilo.start()
    hilo.join()
    assert errores == []
