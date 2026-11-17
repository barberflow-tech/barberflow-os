"""Matriz RBAC de la API (HU-09 / SUB-09-B).

Dado un usuario sin sesion, un cliente, un barbero o un administrador, cuando
llama a cada endpoint de la API, entonces recibe el codigo que fija la matriz de
`RBAC.md`: 401 sin sesion y 403 con un rol sin acceso.

La tabla `CASOS` es la matriz en forma de datos: una fila por endpoint y, en
cada una, el codigo esperado por rol. Un codigo distinto de 401/403 prueba que
el permiso dejo pasar la peticion (el cuerpo vacio da 400, la ruta sin datos
da 404, etc.): aqui solo se verifica la autorizacion; las reglas de negocio
viven en las pruebas de cada modulo.

Ademas, `test_inventario_*` recorre las rutas reales y falla si aparece una
ruta nueva que nadie reviso o una vista sin permisos explicitos.
"""

from datetime import datetime, time, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.core.cache import cache
from django.urls import URLPattern, URLResolver, get_resolver
from django.utils import timezone
from rest_framework.test import APIClient

from apps.barberias.models import Membresia
from apps.barberos.jornada import ZONA_HORARIA_BARBERIA
from apps.barberos.models import Barbero, HorarioBarbero
from apps.catalogo.context import obtener_barberia_catalogo
from apps.catalogo.models import Servicio
from apps.citas.models import Cita

ANONIMO, CLIENTE, BARBERO, ADMIN = "anonimo", "cliente", "barbero", "admin"
ROLES = (ANONIMO, CLIENTE, BARBERO, ADMIN)

LUNES = 0
DIA_JSON = {"weekday": LUNES, "open_time": "09:00", "close_time": "17:00"}
CUERPO_DIA = {"open_time": "09:00", "close_time": "17:00"}
CUERPO_SERVICIO = {"name": "Barba", "price": "15000.00", "duration_minutes": 20}


def todos(codigo: int) -> dict[str, int]:
    return {rol: codigo for rol in ROLES}


def por_rol(anonimo: int, cliente: int, barbero: int, admin: int) -> dict[str, int]:
    return {ANONIMO: anonimo, CLIENTE: cliente, BARBERO: barbero, ADMIN: admin}


# (metodo, ruta, cuerpo, codigo esperado por rol). La ruta usa los datos de
# `contexto`: {servicio}, {propio}, {ajeno}, {cita_cliente}, etc.
CASOS = [
    # Cuenta y sesion: publicas.
    ("post", "/api/v1/auth/register", {}, todos(400)),
    ("post", "/api/v1/auth/login", {}, todos(400)),
    ("post", "/api/v1/auth/logout", None, todos(204)),
    ("post", "/api/v1/auth/refresh", None, todos(401)),  # sin cookie: sesion invalida
    ("post", "/api/v1/auth/password-reset", {}, todos(400)),
    ("post", "/api/v1/auth/password-reset/confirm", {}, todos(400)),
    ("get", "/api/v1/auth/protected-test", None, por_rol(401, 403, 403, 200)),
    # Finanzas: solo el administrador.
    ("get", "/api/v1/admin/finanzas", None, por_rol(401, 403, 403, 200)),
    # Citas: reservar es publico; cancelar y reprogramar, solo el propietario
    # (el barbero y el admin actuan "como cliente" sobre sus propias citas).
    ("post", "/api/v1/appointments", {}, todos(400)),
    # Listar citas: cada rol ve solo las suyas "como cliente".
    ("get", "/api/v1/appointments", None, por_rol(401, 200, 200, 200)),
    (
        "post",
        "/api/v1/appointments/{cita_cliente}/cancel",
        None,
        por_rol(401, 200, 403, 403),
    ),
    (
        "post",
        "/api/v1/appointments/{cita_barbero}/cancel",
        None,
        por_rol(401, 403, 200, 403),
    ),
    (
        "post",
        "/api/v1/appointments/{cita_admin}/cancel",
        None,
        por_rol(401, 403, 403, 200),
    ),
    (
        "post",
        "/api/v1/appointments/{cita_cliente}/reschedule",
        {"start_at": "{nuevo_inicio}"},
        {ANONIMO: 401, BARBERO: 403, ADMIN: 403},
    ),
    # Bloqueos de agenda: solo el administrador (no se editan: se borran y crean).
    # Historial (canceladas y vencidas): cada usuario autenticado ve solo las suyas.
    ("get", "/api/v1/appointments/history", None, por_rol(401, 200, 200, 200)),
    ("get", "/api/v1/blocks", None, por_rol(401, 403, 403, 200)),
    ("post", "/api/v1/blocks", {}, por_rol(401, 403, 403, 400)),
    ("put", "/api/v1/blocks/999999", {}, por_rol(401, 403, 403, 404)),
    ("delete", "/api/v1/blocks/999999", None, por_rol(401, 403, 403, 404)),
    # Disponibilidad (consulta de slots): publica.
    (
        "get",
        "/api/v1/availability?barber={propio}&date={fecha}&slot_duration=30",
        None,
        todos(200),
    ),
    # Catalogo: lectura publica, escritura solo del administrador.
    ("get", "/api/v1/services", None, todos(200)),
    ("get", "/api/v1/services/{servicio}", None, todos(200)),
    ("post", "/api/v1/services", CUERPO_SERVICIO, por_rol(401, 403, 403, 201)),
    (
        "put",
        "/api/v1/services/{servicio}",
        CUERPO_SERVICIO,
        por_rol(401, 403, 403, 200),
    ),
    ("delete", "/api/v1/services/{servicio}", None, por_rol(401, 403, 403, 204)),
    # Horario del barbero: el barbero solo VE el suyo; escribir es del admin.
    ("get", "/api/v1/barbers/{propio}/schedule", None, por_rol(401, 403, 200, 200)),
    ("get", "/api/v1/barbers/{ajeno}/schedule", None, por_rol(401, 403, 403, 200)),
    (
        "put",
        "/api/v1/barbers/{propio}/schedule",
        {"days": [DIA_JSON]},
        por_rol(401, 403, 403, 200),
    ),
    (
        "put",
        "/api/v1/barbers/{propio}/schedule/0",
        CUERPO_DIA,
        por_rol(401, 403, 403, 200),
    ),
    (
        "delete",
        "/api/v1/barbers/{propio}/schedule/0",
        None,
        por_rol(401, 403, 403, 204),
    ),
    # Barberos y sus servicios: el listado es publico; asignar es del admin.
    ("get", "/api/v1/barbers", None, todos(200)),
    ("get", "/api/v1/barbers/me/services", None, por_rol(401, 403, 200, 403)),
    (
        "put",
        "/api/v1/barbers/{propio}/services",
        {"servicios": ["{servicio}"]},
        por_rol(401, 403, 403, 200),
    ),
    # Portafolio publico y propio (el propio es solo del barbero; admin: 403).
    ("get", "/api/v1/portfolio", None, todos(200)),
    ("get", "/api/v1/barbers/me/portfolio", None, por_rol(401, 403, 200, 403)),
    ("post", "/api/v1/barbers/me/portfolio", None, por_rol(401, 403, 400, 403)),
    # Usuarios y roles: solo el administrador.
    ("get", "/api/v1/users", None, por_rol(401, 403, 403, 200)),
    (
        "patch",
        "/api/v1/users/{cliente_id}/role",
        {"role": "cliente"},
        por_rol(401, 403, 403, 200),
    ),
]

# Nombre (con namespace) de cada ruta de la API revisada contra la matriz.
RUTAS_REVISADAS = {
    "usuarios:register",
    "usuarios:login",
    "usuarios:logout",
    "usuarios:refresh",
    "usuarios:protected-test",
    "usuarios:password-reset",
    "usuarios:password-reset-confirm",
    "usuarios:users",
    "usuarios:user-role",
    "citas:crear",
    "citas:cancelar",
    "citas:reprogramar",
    "citas:historial",
    "citas:disponibilidad",
    "citas:bloqueos",
    "citas:bloqueo-detalle",
    "catalogo:service-list",
    "catalogo:service-detail",
    "barberos:barber-portfolio-upload",
    "barberos:barber-list",
    "barberos:barber-my-services",
    "barberos:barber-services",
    "barberos:portfolio-public",
    "barberos:horario-semanal",
    "barberos:horario-dia",
    "finanzas:finanzas",
}


@pytest.fixture(autouse=True)
def limpiar_throttle():
    # El limite de reservas sin cuenta se guarda en cache: se limpia por test.
    cache.clear()
    yield
    cache.clear()


def _cita(cliente, barbero, servicio, hora: int) -> Cita:
    inicio = (timezone.now() + timedelta(days=2)).replace(
        hour=hora, minute=0, second=0, microsecond=0
    )
    return Cita.objects.create(
        barberia=barbero.barberia,
        client=cliente,
        barber=barbero,
        service=servicio,
        start_at=inicio,
        end_at=inicio + timedelta(minutes=servicio.duration_minutes),
        price=servicio.price,
    )


def _autenticado(usuario) -> APIClient:
    api = APIClient()
    if usuario is not None:
        api.force_authenticate(user=usuario)
    return api


@pytest.fixture
def contexto(make_user):
    """Una barberia con los tres roles y los datos que tocan las rutas."""
    barberia = obtener_barberia_catalogo()
    cliente = make_user(CLIENTE)
    barbero_user = make_user(BARBERO)
    admin = make_user(ADMIN)
    Membresia.objects.create(user=barbero_user, barberia=barberia)
    Membresia.objects.create(user=admin, barberia=barberia)

    propio = Barbero.objects.create(barberia=barberia, name="Propio", user=barbero_user)
    ajeno = Barbero.objects.create(barberia=barberia, name="Ajeno")
    HorarioBarbero.objects.create(
        barbero=propio, weekday=LUNES, open_time=time(9), close_time=time(17)
    )
    servicio = Servicio.objects.create(
        barberia=barberia,
        name="Corte",
        price=Decimal("20000.00"),
        duration_minutes=30,
    )
    inicio_nuevo = timezone.now() + timedelta(days=3)

    return SimpleNamespace(
        usuarios={ANONIMO: None, CLIENTE: cliente, BARBERO: barbero_user, ADMIN: admin},
        datos={
            "servicio": servicio.pk,
            "cliente_id": cliente.pk,
            "propio": propio.pk,
            "ajeno": ajeno.pk,
            # Las citas son del barbero ajeno: editar el horario del propio
            # no choca con citas futuras (409) y aqui solo se prueba el permiso.
            "cita_cliente": _cita(cliente, ajeno, servicio, 10).pk,
            "cita_barbero": _cita(barbero_user, ajeno, servicio, 11).pk,
            "cita_admin": _cita(admin, ajeno, servicio, 12).pk,
            "fecha": (timezone.now() + timedelta(days=7)).date().isoformat(),
            "nuevo_inicio": inicio_nuevo.isoformat(),
        },
    )


def _expandir(valor, datos: dict):
    if isinstance(valor, str):
        return valor.format(**datos)
    if isinstance(valor, dict):
        return {clave: _expandir(v, datos) for clave, v in valor.items()}
    if isinstance(valor, list):
        return [_expandir(v, datos) for v in valor]
    return valor


CASOS_POR_ROL = [
    pytest.param(rol, metodo, ruta, cuerpo, esperados[rol], id=f"{rol}-{metodo}-{ruta}")
    for metodo, ruta, cuerpo, esperados in CASOS
    for rol in ROLES
    if rol in esperados
]


@pytest.mark.django_db
@pytest.mark.parametrize("rol,metodo,ruta,cuerpo,esperado", CASOS_POR_ROL)
def test_matriz_rbac_devuelve_el_codigo_del_rol(
    contexto, rol, metodo, ruta, cuerpo, esperado
):
    api = _autenticado(contexto.usuarios[rol])
    url = ruta.format(**contexto.datos)
    cuerpo = _expandir(cuerpo, contexto.datos)

    if cuerpo is None:
        respuesta = getattr(api, metodo)(url)
    else:
        respuesta = getattr(api, metodo)(url, cuerpo, format="json")

    assert respuesta.status_code == esperado, respuesta.content


# --------------------------------------------------------------------------- #
# Barbero -> finanzas (criterio de aceptacion obligatorio de HU-09)           #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_barbero_en_finanzas_recibe_403(contexto):
    respuesta = _autenticado(contexto.usuarios[BARBERO]).get("/api/v1/admin/finanzas")

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_cliente_en_finanzas_recibe_403(contexto):
    respuesta = _autenticado(contexto.usuarios[CLIENTE]).get("/api/v1/admin/finanzas")

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_finanzas_sin_sesion_recibe_401():
    assert APIClient().get("/api/v1/admin/finanzas").status_code == 401


@pytest.mark.django_db
def test_finanzas_acepta_la_ruta_con_barra_final(contexto):
    respuesta = _autenticado(contexto.usuarios[ADMIN]).get("/api/v1/admin/finanzas/")

    assert respuesta.status_code == 200


# --------------------------------------------------------------------------- #
# Catalogo: decide el rol, no is_staff                                        #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
@pytest.mark.parametrize("rol", [CLIENTE, BARBERO])
def test_is_staff_sin_rol_admin_no_puede_escribir_el_catalogo(contexto, rol):
    usuario = contexto.usuarios[rol]
    usuario.is_staff = True
    usuario.save()

    respuesta = _autenticado(usuario).post(
        "/api/v1/services", CUERPO_SERVICIO, format="json"
    )

    assert respuesta.status_code == 403
    assert not Servicio.objects.filter(name=CUERPO_SERVICIO["name"]).exists()


@pytest.mark.django_db
@pytest.mark.parametrize("rol", [CLIENTE, BARBERO])
def test_is_staff_sin_rol_admin_no_puede_asignar_servicios_a_un_barbero(contexto, rol):
    usuario = contexto.usuarios[rol]
    usuario.is_staff = True
    usuario.save()
    propio = contexto.datos["propio"]

    respuesta = _autenticado(usuario).put(
        f"/api/v1/barbers/{propio}/services", {"servicios": []}, format="json"
    )

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_admin_sin_is_staff_si_puede_escribir_el_catalogo(contexto):
    admin = contexto.usuarios[ADMIN]
    admin.is_staff = False
    admin.save()

    respuesta = _autenticado(admin).post(
        "/api/v1/services", CUERPO_SERVICIO, format="json"
    )

    assert respuesta.status_code == 201


@pytest.mark.django_db
@pytest.mark.parametrize(
    "rol,ve_inactivos",
    [(ANONIMO, False), (CLIENTE, False), (BARBERO, False), (ADMIN, True)],
)
def test_solo_el_admin_ve_los_servicios_inactivos(contexto, rol, ve_inactivos):
    Servicio.objects.create(
        barberia=obtener_barberia_catalogo(),
        name="Retirado",
        price=Decimal("10000.00"),
        duration_minutes=20,
        is_active=False,
    )
    usuario = contexto.usuarios[rol]
    if usuario is not None:
        usuario.is_staff = rol != ADMIN  # is_staff no debe cambiar lo que ve

    nombres = {s["name"] for s in _autenticado(usuario).get("/api/v1/services").json()}

    assert ("Retirado" in nombres) is ve_inactivos


@pytest.mark.django_db
@pytest.mark.parametrize("rol", [ANONIMO, CLIENTE, BARBERO])
def test_servicio_inactivo_en_detalle_da_404_salvo_para_el_admin(contexto, rol):
    inactivo = Servicio.objects.create(
        barberia=obtener_barberia_catalogo(),
        name="Retirado",
        price=Decimal("10000.00"),
        duration_minutes=20,
        is_active=False,
    )
    api = _autenticado(contexto.usuarios[rol])
    admin = _autenticado(contexto.usuarios[ADMIN])

    assert api.get(f"/api/v1/services/{inactivo.pk}").status_code == 404
    assert admin.get(f"/api/v1/services/{inactivo.pk}").status_code == 200


# --------------------------------------------------------------------------- #
# Horario: el barbero solo ve el suyo                                         #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_barbero_ve_su_propio_horario_con_el_contenido_del_dia(contexto):
    api = _autenticado(contexto.usuarios[BARBERO])

    respuesta = api.get(f"/api/v1/barbers/{contexto.datos['propio']}/schedule")

    assert respuesta.status_code == 200
    assert respuesta.json()["days"][0]["weekday"] == LUNES


@pytest.mark.django_db
def test_barbero_no_ve_el_horario_de_otro_y_no_se_filtra_si_existe(contexto):
    api = _autenticado(contexto.usuarios[BARBERO])

    ajeno = api.get(f"/api/v1/barbers/{contexto.datos['ajeno']}/schedule")
    inexistente = api.get("/api/v1/barbers/999999/schedule")

    # Mismo codigo exista o no el barbero: no sirve para sondear IDs.
    assert ajeno.status_code == inexistente.status_code == 403


@pytest.mark.django_db
def test_barbero_sin_cuenta_vinculada_no_ve_ningun_horario(contexto, make_user):
    huerfano = make_user(BARBERO, email="huerfano@barberflow.test")
    Membresia.objects.create(user=huerfano, barberia=obtener_barberia_catalogo())

    respuesta = _autenticado(huerfano).get(
        f"/api/v1/barbers/{contexto.datos['propio']}/schedule"
    )

    assert respuesta.status_code == 403


@pytest.mark.django_db
def test_barbero_no_modifica_su_horario_y_nada_cambia(contexto):
    api = _autenticado(contexto.usuarios[BARBERO])
    propio = contexto.datos["propio"]

    escrituras = [
        api.put(f"/api/v1/barbers/{propio}/schedule", {"days": []}, format="json"),
        api.put(f"/api/v1/barbers/{propio}/schedule/1", CUERPO_DIA, format="json"),
        api.delete(f"/api/v1/barbers/{propio}/schedule/0"),
    ]

    assert [r.status_code for r in escrituras] == [403, 403, 403]
    assert HorarioBarbero.objects.filter(barbero_id=propio).count() == 1


# --------------------------------------------------------------------------- #
# Reserva sin cuenta (criterio 4) y token invalido en rutas publicas (R2)     #
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_reserva_sin_cuenta_sigue_funcionando(contexto):
    """Un visitante consulta el catalogo y reserva con nombre y celular."""
    servicio = contexto.datos["servicio"]
    propio = Barbero.objects.get(pk=contexto.datos["propio"])
    visitante = APIClient()
    dia = timezone.now() + timedelta(days=4)
    while dia.weekday() != LUNES:
        dia += timedelta(days=1)
    inicio = datetime.combine(dia.date(), time(10), tzinfo=ZONA_HORARIA_BARBERIA)

    assert visitante.get("/api/v1/services").status_code == 200
    assert (
        visitante.get(
            f"/api/v1/availability?barber={propio.pk}&date={dia.date()}&slot_duration=30"
        ).status_code
        == 200
    )

    respuesta = visitante.post(
        "/api/v1/appointments",
        {
            "barber": propio.pk,
            "service": servicio,
            "start_at": inicio.isoformat(),
            "contact_name": "Visitante",
            "contact_phone": "3001234567",
        },
        format="json",
    )

    assert respuesta.status_code == 201, respuesta.content
    assert Cita.objects.get(pk=respuesta.json()["id"]).client_id is None


@pytest.mark.django_db
@pytest.mark.parametrize("ruta", ["/api/v1/services", "/api/v1/availability"])
def test_token_invalido_en_ruta_publica_devuelve_401_comportamiento_actual(ruta):
    """Deja registrado el comportamiento de HU-06 (no se cambia en HU-09).

    JWTAuthentication corre antes de AllowAny: una cabecera Authorization con
    un token vencido o alterado da 401 incluso en rutas publicas. login y
    register evitan esto con `authentication_classes = []`. Si algun dia se
    decide que las rutas publicas ignoren el token invalido, esta prueba debe
    actualizarse junto con ese cambio.
    """
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION="Bearer token.invalido.vencido")

    assert api.get(ruta).status_code == 401


# --------------------------------------------------------------------------- #
# Inventario: ninguna ruta de la API queda sin revisar                        #
# --------------------------------------------------------------------------- #


def _rutas_de_la_api() -> dict[str, type]:
    """Nombre (con namespace) -> clase de vista de cada ruta bajo /api/v1/."""
    encontradas: dict[str, type] = {}

    def recorrer(patrones, namespace: str = "") -> None:
        for patron in patrones:
            if isinstance(patron, URLResolver):
                recorrer(patron.url_patterns, patron.namespace or namespace)
            elif isinstance(patron, URLPattern):
                nombre = f"{namespace}:{patron.name}" if namespace else patron.name
                encontradas[nombre] = patron.callback.view_class

    for patron in get_resolver().url_patterns:
        if isinstance(patron, URLResolver) and str(patron.pattern) == "api/v1/":
            recorrer(patron.url_patterns, patron.namespace or "")
    return encontradas


def test_inventario_no_hay_rutas_sin_revisar():
    rutas = set(_rutas_de_la_api())

    assert rutas - RUTAS_REVISADAS == set(), (
        "Hay rutas nuevas sin revisar contra la matriz RBAC: agregalas a "
        "RBAC.md, a CASOS y a RUTAS_REVISADAS."
    )
    assert RUTAS_REVISADAS - rutas == set(), "Hay rutas revisadas que ya no existen."


def test_inventario_cada_vista_declara_sus_permisos():
    sin_permisos = []
    for nombre, vista in _rutas_de_la_api().items():
        propias = [
            clase
            for clase in vista.__mro__
            if not clase.__module__.startswith("rest_framework")
            and clase is not object
            and (
                "permission_classes" in vars(clase) or "get_permissions" in vars(clase)
            )
        ]
        if not propias:
            sin_permisos.append(nombre)

    assert (
        sin_permisos == []
    ), f"Vistas que dependen del permiso por defecto: {sin_permisos}"
