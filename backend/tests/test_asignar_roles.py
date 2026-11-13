"""SCRUM-70 / HU-09 (SUB-09-D): el administrador asigna roles a los usuarios.

GET   /api/v1/users                lista los usuarios de la barberia del admin.
GET   /api/v1/users?email=<correo> busca por correo exacto (su barberia o sin barberia).
PATCH /api/v1/users/<id>/role      cambia el rol de un usuario.
"""

import pytest
from rest_framework.test import APIClient

from apps.barberias.models import Barberia, Membresia
from apps.usuarios.models import Rol

pytestmark = pytest.mark.django_db

LOGIN = "/api/v1/auth/login"
PROTEGIDO_ADMIN = "/api/v1/auth/protected-test"
LISTA = "/api/v1/users"
CONTRASENA = "Corte.Fade-2026"


def url_rol(usuario_id) -> str:
    return f"/api/v1/users/{usuario_id}/role"


@pytest.fixture
def barberia():
    return Barberia.objects.create(name="Barberia Norte")


@pytest.fixture
def otra_barberia():
    return Barberia.objects.create(name="Barberia Sur")


@pytest.fixture
def crear(django_user_model):
    def _crear(email, rol=Rol.CLIENTE, barberia=None, full_name=""):
        usuario = django_user_model.objects.create_user(
            username=email, email=email, password=CONTRASENA
        )
        usuario.perfil.role = rol
        usuario.perfil.full_name = full_name
        usuario.perfil.save()
        if barberia is not None:
            Membresia.objects.create(user=usuario, barberia=barberia)
        return usuario

    return _crear


@pytest.fixture
def admin(crear, barberia):
    return crear("dueno@norte.com", Rol.ADMIN, barberia, "Dueno Norte")


def cliente_api(usuario) -> APIClient:
    """Cliente HTTP con el access token de un login real."""
    api = APIClient()
    respuesta = api.post(
        LOGIN, {"email": usuario.email, "password": CONTRASENA}, format="json"
    )
    assert respuesta.status_code == 200
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {respuesta.json()['access']}")
    return api


# --- Criterio: el admin cambia el rol y los permisos cambian --------------


def test_admin_cambia_el_rol_de_un_usuario_de_su_barberia(admin, crear, barberia):
    # Dado un administrador y un cliente de su barberia
    cliente = crear("ana@norte.com", Rol.CLIENTE, barberia)

    # Cuando cambia su rol a barbero
    respuesta = cliente_api(admin).patch(
        url_rol(cliente.pk), {"role": "barbero"}, format="json"
    )

    # Entonces el rol queda guardado y la respuesta trae el usuario actualizado
    assert respuesta.status_code == 200
    assert respuesta.json()["role"] == "barbero"
    cliente.perfil.refresh_from_db()
    assert cliente.perfil.role == Rol.BARBERO


def test_los_permisos_cambian_en_la_siguiente_sesion_del_usuario(
    admin, crear, barberia
):
    # Dado un cliente que hoy no puede entrar a un recurso de administrador
    cliente = crear("ana@norte.com", Rol.CLIENTE, barberia)
    assert cliente_api(cliente).get(PROTEGIDO_ADMIN).status_code == 403

    # Cuando el administrador lo asciende a admin
    cliente_api(admin).patch(url_rol(cliente.pk), {"role": "admin"}, format="json")

    # Entonces en su siguiente sesion ya tiene los permisos de admin
    assert cliente_api(cliente).get(PROTEGIDO_ADMIN).status_code == 200


# --- Criterio: un no administrador no puede hacerlo -----------------------


@pytest.mark.parametrize("rol", [Rol.BARBERO, Rol.CLIENTE])
def test_un_no_administrador_no_puede_cambiar_roles(crear, barberia, rol):
    # Dado un usuario que no es administrador
    actor = crear("actor@norte.com", rol, barberia)
    otro = crear("otro@norte.com", Rol.CLIENTE, barberia)

    # Cuando intenta cambiar el rol de otro usuario
    respuesta = cliente_api(actor).patch(
        url_rol(otro.pk), {"role": "admin"}, format="json"
    )

    # Entonces recibe 403 y el rol no cambia
    assert respuesta.status_code == 403
    otro.perfil.refresh_from_db()
    assert otro.perfil.role == Rol.CLIENTE


@pytest.mark.parametrize("rol", [Rol.BARBERO, Rol.CLIENTE])
def test_un_no_administrador_no_puede_listar_usuarios(crear, barberia, rol):
    actor = crear("actor@norte.com", rol, barberia)

    assert cliente_api(actor).get(LISTA).status_code == 403


def test_sin_sesion_recibe_401(crear, barberia):
    otro = crear("otro@norte.com", Rol.CLIENTE, barberia)

    assert APIClient().get(LISTA).status_code == 401
    assert (
        APIClient()
        .patch(url_rol(otro.pk), {"role": "admin"}, format="json")
        .status_code
        == 401
    )


# --- DoD: el administrador no puede quitarse su propio rol ---------------


@pytest.mark.parametrize("rol", ["barbero", "cliente"])
def test_el_admin_no_puede_cambiar_su_propio_rol(admin, rol):
    # Dado un administrador
    # Cuando intenta cambiar su propio rol
    respuesta = cliente_api(admin).patch(
        url_rol(admin.pk), {"role": rol}, format="json"
    )

    # Entonces recibe 400 y sigue siendo administrador
    assert respuesta.status_code == 400
    assert "propio rol" in respuesta.json()["detail"]
    admin.perfil.refresh_from_db()
    assert admin.perfil.role == Rol.ADMIN


# --- Alcance por barberia ---------------------------------------------------


def test_la_lista_solo_trae_los_usuarios_de_la_barberia_del_admin(
    admin, crear, barberia, otra_barberia
):
    # Dado usuarios en su barberia, en otra barberia y sin barberia
    crear("ana@norte.com", Rol.BARBERO, barberia, "Ana")
    crear("luis@sur.com", Rol.BARBERO, otra_barberia)
    crear("libre@correo.com", Rol.CLIENTE)

    # Cuando el administrador lista los usuarios
    respuesta = cliente_api(admin).get(LISTA)

    # Entonces solo ve los de su barberia, el mismo incluido
    assert respuesta.status_code == 200
    correos = [u["email"] for u in respuesta.json()]
    assert correos == ["ana@norte.com", "dueno@norte.com"]
    ana = respuesta.json()[0]
    assert ana == {
        "id": ana["id"],
        "email": "ana@norte.com",
        "full_name": "Ana",
        "role": "barbero",
        "en_barberia": True,
    }


def test_busca_por_correo_exacto_a_un_usuario_sin_barberia(admin, crear):
    # Dado un cliente registrado que no pertenece a ninguna barberia
    crear("libre@correo.com", Rol.CLIENTE)

    # Cuando el administrador lo busca por su correo (sin distinguir mayusculas)
    respuesta = cliente_api(admin).get(LISTA, {"email": " Libre@Correo.com "})

    # Entonces lo encuentra, marcado como fuera de la barberia
    assert respuesta.status_code == 200
    assert [(u["email"], u["en_barberia"]) for u in respuesta.json()] == [
        ("libre@correo.com", False)
    ]


def test_la_busqueda_no_encuentra_usuarios_de_otra_barberia(
    admin, crear, otra_barberia
):
    crear("luis@sur.com", Rol.BARBERO, otra_barberia)

    respuesta = cliente_api(admin).get(LISTA, {"email": "luis@sur.com"})

    assert respuesta.status_code == 200
    assert respuesta.json() == []


def test_la_busqueda_por_correo_parcial_no_devuelve_nada(admin, crear):
    crear("libre@correo.com", Rol.CLIENTE)

    assert cliente_api(admin).get(LISTA, {"email": "libre"}).json() == []


def test_no_puede_cambiar_el_rol_de_un_usuario_de_otra_barberia(
    admin, crear, otra_barberia
):
    # Dado un usuario de otra barberia
    ajeno = crear("luis@sur.com", Rol.BARBERO, otra_barberia)

    # Cuando el administrador intenta cambiar su rol
    respuesta = cliente_api(admin).patch(
        url_rol(ajeno.pk), {"role": "admin"}, format="json"
    )

    # Entonces recibe 404 (no se revela que existe) y el rol no cambia
    assert respuesta.status_code == 404
    ajeno.perfil.refresh_from_db()
    assert ajeno.perfil.role == Rol.BARBERO


@pytest.mark.parametrize("rol", ["barbero", "admin"])
def test_ascender_a_un_usuario_sin_barberia_lo_vincula_a_la_del_admin(
    admin, crear, barberia, rol
):
    # Dado un cliente sin barberia
    libre = crear("libre@correo.com", Rol.CLIENTE)

    # Cuando el administrador lo asciende a barbero o admin
    respuesta = cliente_api(admin).patch(
        url_rol(libre.pk), {"role": rol}, format="json"
    )

    # Entonces queda con ese rol y vinculado a la barberia del administrador
    assert respuesta.status_code == 200
    assert respuesta.json()["en_barberia"] is True
    libre.perfil.refresh_from_db()
    assert libre.perfil.role == rol
    assert libre.membresia.barberia == barberia


def test_asignar_cliente_a_un_usuario_sin_barberia_no_lo_vincula(admin, crear):
    libre = crear("libre@correo.com", Rol.CLIENTE)

    respuesta = cliente_api(admin).patch(
        url_rol(libre.pk), {"role": "cliente"}, format="json"
    )

    assert respuesta.status_code == 200
    assert not Membresia.objects.filter(user=libre).exists()


def test_ascender_a_barbero_no_crea_la_ficha_de_barbero(admin, crear, barberia):
    from apps.barberos.models import Barbero

    cliente = crear("ana@norte.com", Rol.CLIENTE, barberia)

    cliente_api(admin).patch(url_rol(cliente.pk), {"role": "barbero"}, format="json")

    assert not Barbero.objects.filter(user=cliente).exists()


def test_un_admin_puede_cambiar_el_rol_de_otro_admin_de_su_barberia(
    admin, crear, barberia
):
    socio = crear("socio@norte.com", Rol.ADMIN, barberia)

    respuesta = cliente_api(admin).patch(
        url_rol(socio.pk), {"role": "barbero"}, format="json"
    )

    assert respuesta.status_code == 200
    socio.perfil.refresh_from_db()
    assert socio.perfil.role == Rol.BARBERO


# --- Validacion de la entrada -----------------------------------------------


@pytest.mark.parametrize("valor", ["superadmin", "", None])
def test_un_rol_desconocido_recibe_400(admin, crear, barberia, valor):
    cliente = crear("ana@norte.com", Rol.CLIENTE, barberia)

    respuesta = cliente_api(admin).patch(
        url_rol(cliente.pk), {"role": valor}, format="json"
    )

    assert respuesta.status_code == 400
    cliente.perfil.refresh_from_db()
    assert cliente.perfil.role == Rol.CLIENTE


def test_un_usuario_inexistente_recibe_404(admin):
    respuesta = cliente_api(admin).patch(
        url_rol(99999), {"role": "admin"}, format="json"
    )

    assert respuesta.status_code == 404


def test_un_admin_sin_barberia_recibe_409(crear):
    # Dado un admin que no pertenece a ninguna barberia
    huerfano = crear("solo@correo.com", Rol.ADMIN)
    libre = crear("libre@correo.com", Rol.CLIENTE)

    # Cuando intenta listar o cambiar roles
    api = cliente_api(huerfano)

    # Entonces recibe 409: no hay una barberia a la cual aplicar el cambio
    assert api.get(LISTA).status_code == 409
    respuesta = api.patch(url_rol(libre.pk), {"role": "barbero"}, format="json")
    assert respuesta.status_code == 409
