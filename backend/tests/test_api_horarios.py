"""API de horarios del barbero (HU-08 / SCRUM-72).

GET/PUT /api/v1/barbers/{id}/schedule y PUT/DELETE
/api/v1/barbers/{id}/schedule/{weekday}. Solo el administrador de la barberia
del barbero puede usarla. Las reglas de negocio se prueban en
test_horarios_servicios.py; aqui se prueban roles, formatos y codigos HTTP.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal

import pytest
from django.db import DatabaseError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Barberia, Membresia
from apps.barberos import services_horarios
from apps.barberos.jornada import ZONA_HORARIA_BARBERIA
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO = range(6)


def url_semana(barbero_id) -> str:
    return f"/api/v1/barbers/{barbero_id}/schedule"


def url_dia(barbero_id, weekday) -> str:
    return f"/api/v1/barbers/{barbero_id}/schedule/{weekday}"


def dia_json(weekday, abre="09:00", cierra="17:00", descanso=None) -> dict:
    datos = {"weekday": weekday, "open_time": abre, "close_time": cierra}
    if descanso is not None:
        datos["break_start"], datos["break_duration_minutes"] = descanso
    return datos


def sin_weekday(datos: dict) -> dict:
    return {campo: valor for campo, valor in datos.items() if campo != "weekday"}


def proxima_fecha(weekday: int, desde_dias: int = 3):
    fecha = timezone.now().astimezone(ZONA_HORARIA_BARBERIA).date()
    fecha += timedelta(days=desde_dias)
    while fecha.weekday() != weekday:
        fecha += timedelta(days=1)
    return fecha


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Centro")


@pytest.fixture
def otra_barberia():
    return Barberia.objects.create(name="Barberia Norte")


@pytest.fixture
def barbero(barberia):
    return Barbero.objects.create(barberia=barberia, name="Thiago")


@pytest.fixture
def barbero_ajeno(otra_barberia):
    return Barbero.objects.create(barberia=otra_barberia, name="Ajeno")


@pytest.fixture
def admin(make_user, barberia):
    usuario = make_user("admin", email="admin@barberflow.test")
    Membresia.objects.create(user=usuario, barberia=barberia)
    return usuario


@pytest.fixture
def admin_ajeno(make_user, otra_barberia):
    usuario = make_user("admin", email="admin.ajeno@barberflow.test")
    Membresia.objects.create(user=usuario, barberia=otra_barberia)
    return usuario


@pytest.fixture
def admin_sin_barberia(make_user):
    return make_user("admin", email="admin.suelto@barberflow.test")


@pytest.fixture
def api(admin):
    return autenticado(admin)


def autenticado(usuario) -> APIClient:
    cliente = APIClient()
    cliente.force_authenticate(user=usuario)
    return cliente


@pytest.fixture
def semana(api, barbero):
    """Deja a Thiago con lunes y viernes de 09:00 a 17:00 y descanso 13:00-14:00."""
    respuesta = api.put(
        url_semana(barbero.pk),
        {
            "days": [
                dia_json(LUNES, descanso=("13:00", 60)),
                dia_json(VIERNES, descanso=("13:00", 60)),
            ]
        },
        format="json",
    )
    assert respuesta.status_code == 200
    return respuesta.json()


def cita_en(barbero, fecha, hora, minuto=0, estado=Cita.Estado.PENDING) -> Cita:
    servicio = Servicio.objects.create(
        barberia=barbero.barberia,
        name=f"Corte {Servicio.objects.count()}",
        price=Decimal("25000.00"),
        duration_minutes=30,
    )
    inicio = datetime.combine(fecha, time(hora, minuto), tzinfo=ZONA_HORARIA_BARBERIA)
    return Cita.objects.create(
        barberia=barbero.barberia,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=30),
        price=servicio.price,
        status=estado,
        contact_name="Visitante",
        contact_phone="3001234567",
    )


# --------------------------------------------------------------------------- #
# GET /barbers/{id}/schedule                                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_ver_horario_semanal_como_admin(api, barbero, semana):
    respuesta = api.get(url_semana(barbero.pk))

    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["barber"] == barbero.pk
    assert cuerpo["name"] == "Thiago"
    assert cuerpo["timezone"] == "America/Bogota"
    assert cuerpo["days"] == [
        {
            "weekday": 0,
            "open_time": "09:00",
            "close_time": "17:00",
            "break_start": "13:00",
            "break_duration_minutes": 60,
        },
        {
            "weekday": 4,
            "open_time": "09:00",
            "close_time": "17:00",
            "break_start": "13:00",
            "break_duration_minutes": 60,
        },
    ]
    assert cuerpo["updated_at"] is not None


@pytest.mark.django_db
def test_ver_horario_de_un_barbero_sin_horario_devuelve_dias_vacios(api, barbero):
    respuesta = api.get(url_semana(barbero.pk))

    assert respuesta.status_code == 200
    assert respuesta.json()["days"] == []
    assert respuesta.json()["updated_at"] is None


@pytest.mark.django_db
def test_ver_horario_de_un_barbero_inactivo_se_permite(api, barbero):
    barbero.is_active = False
    barbero.save()

    assert api.get(url_semana(barbero.pk)).status_code == 200


@pytest.mark.django_db
def test_ver_horario_acepta_la_ruta_sin_barra_final_y_con_ella(api, barbero):
    assert api.get(url_semana(barbero.pk)).status_code == 200
    assert api.get(url_semana(barbero.pk) + "/").status_code == 200


# --------------------------------------------------------------------------- #
# PUT /barbers/{id}/schedule                                                  #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_definir_semana_de_lunes_a_viernes(api, barbero):
    cuerpo = {"days": [dia_json(d) for d in range(5)]}

    respuesta = api.put(url_semana(barbero.pk), cuerpo, format="json")

    assert respuesta.status_code == 200
    assert [d["weekday"] for d in respuesta.json()["days"]] == [0, 1, 2, 3, 4]
    assert respuesta.json()["days"][0]["break_start"] is None
    assert HorarioBarbero.objects.filter(barbero=barbero).count() == 5


@pytest.mark.django_db
def test_definir_semana_dos_veces_es_idempotente(api, barbero):
    cuerpo = {"days": [dia_json(LUNES), dia_json(MARTES)]}

    primera = api.put(url_semana(barbero.pk), cuerpo, format="json")
    segunda = api.put(url_semana(barbero.pk), cuerpo, format="json")

    assert primera.status_code == segunda.status_code == 200
    assert primera.json()["days"] == segunda.json()["days"]
    assert HorarioBarbero.objects.filter(barbero=barbero).count() == 2


@pytest.mark.django_db
def test_la_disponibilidad_refleja_el_horario_nuevo(api, barbero):
    api.put(
        url_semana(barbero.pk),
        {"days": [dia_json(LUNES, descanso=("13:00", 60))]},
        format="json",
    )
    lunes = proxima_fecha(LUNES)

    respuesta = api.get(
        "/api/v1/availability/",
        {"barber": barbero.pk, "date": lunes.isoformat(), "slot_duration": 30},
    )

    assert respuesta.status_code == 200
    assert len(respuesta.json()["available_slots"]) == 14


@pytest.mark.django_db
def test_cierre_anterior_a_la_apertura_devuelve_400_por_dia(api, barbero):
    cuerpo = {"days": [dia_json(LUNES), dia_json(MARTES, "17:00", "09:00")]}

    respuesta = api.put(url_semana(barbero.pk), cuerpo, format="json")

    assert respuesta.status_code == 400
    dias = respuesta.json()["days"]
    assert dias[0] == {}
    assert dias[1] == {"close_time": ["El cierre debe ser posterior a la apertura."]}
    assert not HorarioBarbero.objects.filter(barbero=barbero).exists()


@pytest.mark.django_db
def test_descanso_fuera_del_turno_devuelve_400(api, barbero):
    cuerpo = {"days": [dia_json(LUNES, descanso=("16:30", 60))]}

    respuesta = api.put(url_semana(barbero.pk), cuerpo, format="json")

    assert respuesta.status_code == 400
    assert "break_start" in respuesta.json()["days"][0]


@pytest.mark.django_db
def test_dia_repetido_devuelve_400(api, barbero):
    cuerpo = {"days": [dia_json(LUNES), dia_json(LUNES)]}

    respuesta = api.put(url_semana(barbero.pk), cuerpo, format="json")

    assert respuesta.status_code == 400
    assert "weekday" in respuesta.json()["days"][1]


@pytest.mark.django_db
def test_semana_sin_el_campo_days_devuelve_400(api, barbero):
    respuesta = api.put(url_semana(barbero.pk), {}, format="json")

    assert respuesta.status_code == 400
    assert "days" in respuesta.json()


@pytest.mark.django_db
def test_semana_vacia_devuelve_400_para_no_borrar_el_horario_por_error(
    api, barbero, semana
):
    respuesta = api.put(url_semana(barbero.pk), {"days": []}, format="json")

    assert respuesta.status_code == 400
    assert HorarioBarbero.objects.filter(barbero=barbero).count() == 2


@pytest.mark.django_db
def test_mas_de_siete_dias_devuelve_400(api, barbero):
    cuerpo = {"days": [dia_json(d % 7) for d in range(8)]}

    assert api.put(url_semana(barbero.pk), cuerpo, format="json").status_code == 400


@pytest.mark.django_db
@pytest.mark.parametrize("hora", ["9am", "25:00", "09:00:30", "", "9"])
def test_hora_con_formato_invalido_devuelve_400(api, barbero, hora):
    cuerpo = {"days": [dia_json(LUNES, abre=hora)]}

    respuesta = api.put(url_semana(barbero.pk), cuerpo, format="json")

    assert respuesta.status_code == 400
    assert "open_time" in respuesta.json()["days"][0]


@pytest.mark.django_db
@pytest.mark.parametrize("weekday", [-1, 7, "lunes", None])
def test_weekday_fuera_de_rango_devuelve_400(api, barbero, weekday):
    cuerpo = {"days": [dia_json(weekday)]}

    respuesta = api.put(url_semana(barbero.pk), cuerpo, format="json")

    assert respuesta.status_code == 400
    assert "weekday" in respuesta.json()["days"][0]


@pytest.mark.django_db
def test_semana_que_deja_una_cita_fuera_devuelve_409_con_los_conflictos(
    api, barbero, semana
):
    cita = cita_en(barbero, proxima_fecha(VIERNES), 10)

    respuesta = api.put(
        url_semana(barbero.pk), {"days": [dia_json(LUNES)]}, format="json"
    )

    assert respuesta.status_code == 409
    cuerpo = respuesta.json()
    assert cuerpo["code"] == "horario_con_citas_futuras"
    assert cuerpo["detail"].startswith("El cambio afecta citas futuras")
    assert len(cuerpo["conflicts"]) == 1
    conflicto = cuerpo["conflicts"][0]
    assert conflicto["appointment"] == cita.pk
    assert conflicto["reason"] == "dia_no_laborable"
    assert datetime.fromisoformat(conflicto["start_at"]) == cita.start_at
    assert conflicto["start_at"].endswith("-05:00")  # hora de la barberia
    assert HorarioBarbero.objects.filter(barbero=barbero).count() == 2


@pytest.mark.django_db
def test_semana_de_un_barbero_inactivo_devuelve_400(api, barbero):
    barbero.is_active = False
    barbero.save()

    respuesta = api.put(
        url_semana(barbero.pk), {"days": [dia_json(LUNES)]}, format="json"
    )

    assert respuesta.status_code == 400
    assert "detail" in respuesta.json()


@pytest.mark.django_db
def test_semana_de_un_barbero_inexistente_devuelve_404(api):
    respuesta = api.put(url_semana(999999), {"days": [dia_json(LUNES)]}, format="json")

    assert respuesta.status_code == 404


@pytest.mark.django_db
def test_error_de_base_de_datos_devuelve_500_en_json(api, barbero, monkeypatch):
    def fallar(**_):
        raise DatabaseError("caido")

    monkeypatch.setattr(services_horarios, "reemplazar_horario_semanal", fallar)

    respuesta = api.put(
        url_semana(barbero.pk), {"days": [dia_json(LUNES)]}, format="json"
    )

    assert respuesta.status_code == 500
    assert "detail" in respuesta.json()


# --------------------------------------------------------------------------- #
# PUT /barbers/{id}/schedule/{weekday}                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_crear_un_dia_devuelve_201(api, barbero):
    cuerpo = sin_weekday(dia_json(LUNES, "10:00", "18:00", ("14:00", 30)))

    respuesta = api.put(url_dia(barbero.pk, LUNES), cuerpo, format="json")

    assert respuesta.status_code == 201
    assert respuesta.json() == {
        "barber": barbero.pk,
        "weekday": 0,
        "open_time": "10:00",
        "close_time": "18:00",
        "break_start": "14:00",
        "break_duration_minutes": 30,
        "updated_at": respuesta.json()["updated_at"],
    }
    assert respuesta.json()["updated_at"] is not None


@pytest.mark.django_db
def test_editar_un_dia_existente_devuelve_200(api, barbero, semana):
    cuerpo = sin_weekday(dia_json(LUNES, "10:00", "18:00"))

    respuesta = api.put(url_dia(barbero.pk, LUNES), cuerpo, format="json")

    assert respuesta.status_code == 200
    assert respuesta.json()["open_time"] == "10:00"
    assert respuesta.json()["break_start"] is None  # el PUT reemplaza el dia
    viernes = HorarioBarbero.objects.get(barbero=barbero, weekday=VIERNES)
    assert viernes.open_time == time(9)


@pytest.mark.django_db
def test_editar_un_dia_con_cierre_anterior_devuelve_400(api, barbero):
    cuerpo = sin_weekday(dia_json(LUNES, "18:00", "10:00"))

    respuesta = api.put(url_dia(barbero.pk, LUNES), cuerpo, format="json")

    assert respuesta.status_code == 400
    assert "close_time" in respuesta.json()


@pytest.mark.django_db
def test_editar_un_dia_sin_horas_devuelve_400(api, barbero):
    respuesta = api.put(url_dia(barbero.pk, LUNES), {}, format="json")

    assert respuesta.status_code == 400
    assert {"open_time", "close_time"} <= set(respuesta.json())


@pytest.mark.django_db
def test_editar_un_dia_que_deja_una_cita_fuera_devuelve_409(api, barbero, semana):
    cita_en(barbero, proxima_fecha(LUNES), 16, 30)
    cuerpo = sin_weekday(dia_json(LUNES, cierra="16:00"))

    respuesta = api.put(url_dia(barbero.pk, LUNES), cuerpo, format="json")

    assert respuesta.status_code == 409
    assert respuesta.json()["conflicts"][0]["reason"] == "fuera_de_jornada"


@pytest.mark.django_db
def test_un_dia_fuera_de_0_a_6_en_la_ruta_devuelve_404(api, barbero):
    cuerpo = sin_weekday(dia_json(LUNES))

    assert api.put(url_dia(barbero.pk, 7), cuerpo, format="json").status_code == 404


# --------------------------------------------------------------------------- #
# DELETE /barbers/{id}/schedule/{weekday}                                     #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_quitar_un_dia_devuelve_204(api, barbero, semana):
    respuesta = api.delete(url_dia(barbero.pk, VIERNES))

    assert respuesta.status_code == 204
    assert not respuesta.content
    assert not HorarioBarbero.objects.filter(barbero=barbero, weekday=VIERNES).exists()


@pytest.mark.django_db
def test_quitar_un_dia_dos_veces_devuelve_404_la_segunda(api, barbero, semana):
    assert api.delete(url_dia(barbero.pk, VIERNES)).status_code == 204
    assert api.delete(url_dia(barbero.pk, VIERNES)).status_code == 404


@pytest.mark.django_db
def test_quitar_un_dia_con_cita_futura_devuelve_409(api, barbero, semana):
    cita_en(barbero, proxima_fecha(VIERNES), 10)

    respuesta = api.delete(url_dia(barbero.pk, VIERNES))

    assert respuesta.status_code == 409
    assert respuesta.json()["code"] == "horario_con_citas_futuras"
    assert HorarioBarbero.objects.filter(barbero=barbero, weekday=VIERNES).exists()


@pytest.mark.django_db
def test_quitar_un_dia_con_una_cita_cancelada_devuelve_204(api, barbero, semana):
    cita_en(barbero, proxima_fecha(VIERNES), 10, estado=Cita.Estado.CANCELLED)

    assert api.delete(url_dia(barbero.pk, VIERNES)).status_code == 204


# --------------------------------------------------------------------------- #
# Seguridad de roles                                                          #
# --------------------------------------------------------------------------- #


def todas_las_operaciones(barbero_id) -> list[tuple[str, str, dict | None]]:
    cuerpo_dia = sin_weekday(dia_json(LUNES))
    return [
        ("get", url_semana(barbero_id), None),
        ("put", url_semana(barbero_id), {"days": [dia_json(LUNES)]}),
        ("put", url_dia(barbero_id, LUNES), cuerpo_dia),
        ("delete", url_dia(barbero_id, LUNES), None),
    ]


def ejecutar(cliente: APIClient, metodo: str, url: str, cuerpo):
    if cuerpo is None:
        return getattr(cliente, metodo)(url)
    return getattr(cliente, metodo)(url, cuerpo, format="json")


@pytest.mark.django_db
def test_sin_sesion_devuelve_401_en_todas_las_operaciones(barbero):
    for metodo, url, cuerpo in todas_las_operaciones(barbero.pk):
        assert ejecutar(APIClient(), metodo, url, cuerpo).status_code == 401, url


@pytest.mark.django_db
@pytest.mark.parametrize("rol", ["cliente", "barbero"])
def test_cliente_y_barbero_reciben_403_y_no_cambian_el_horario(
    make_user, barbero, semana, rol
):
    usuario = make_user(rol, email=f"{rol}.prueba@barberflow.test")
    Membresia.objects.create(user=usuario, barberia=barbero.barberia)

    for metodo, url, cuerpo in todas_las_operaciones(barbero.pk):
        respuesta = ejecutar(autenticado(usuario), metodo, url, cuerpo)
        assert respuesta.status_code == 403, (metodo, url)

    assert HorarioBarbero.objects.filter(barbero=barbero).count() == 2


@pytest.mark.django_db
def test_is_staff_con_rol_cliente_no_alcanza(make_user, barbero):
    usuario = make_user("cliente", email="staff.cliente@barberflow.test")
    usuario.is_staff = True
    usuario.save()
    Membresia.objects.create(user=usuario, barberia=barbero.barberia)

    respuesta = autenticado(usuario).put(
        url_semana(barbero.pk), {"days": [dia_json(LUNES)]}, format="json"
    )

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_admin_de_otra_barberia_recibe_404_y_no_cambia_nada(
    admin_ajeno, barbero, semana
):
    for metodo, url, cuerpo in todas_las_operaciones(barbero.pk):
        respuesta = ejecutar(autenticado(admin_ajeno), metodo, url, cuerpo)
        assert respuesta.status_code == 404, (metodo, url)

    assert HorarioBarbero.objects.filter(barbero=barbero).count() == 2


@pytest.mark.django_db
def test_admin_no_ve_ni_edita_el_barbero_de_otra_barberia(api, barbero_ajeno):
    for metodo, url, cuerpo in todas_las_operaciones(barbero_ajeno.pk):
        assert ejecutar(api, metodo, url, cuerpo).status_code == 404, (metodo, url)

    assert not HorarioBarbero.objects.filter(barbero=barbero_ajeno).exists()


@pytest.mark.django_db
def test_admin_sin_barberia_recibe_403(admin_sin_barberia, barbero):
    respuesta = autenticado(admin_sin_barberia).get(url_semana(barbero.pk))

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_rol_degradado_pierde_el_acceso_aunque_su_token_sea_de_admin(admin, barbero):
    cliente_api = autenticado(admin)
    assert cliente_api.get(url_semana(barbero.pk)).status_code == 200

    admin.perfil.role = "cliente"
    admin.perfil.save()
    admin.refresh_from_db()

    assert autenticado(admin).get(url_semana(barbero.pk)).status_code == 403
