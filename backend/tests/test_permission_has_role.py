"""SCRUM-29 / HU-06: HasRole, permiso reutilizable por rol."""

import pytest
from django.contrib.auth.models import AnonymousUser
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.test import APIRequestFactory, force_authenticate
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.usuarios.models import PerfilUsuario, Rol
from apps.usuarios.permissions import HasRole, RolRequerido
from apps.usuarios.tokens import LoginTokenSerializer

pytestmark = pytest.mark.django_db

fabrica = APIRequestFactory()


# --- Vistas de prueba: la sintaxis que usaran las vistas reales ----------


class _Base(APIView):
    authentication_classes = [JWTAuthentication]

    def get(self, request):
        return Response({"ok": True})


class SoloAdmin(_Base):
    permission_classes = [HasRole("admin")]


class SoloBarbero(_Base):
    permission_classes = [HasRole("barbero")]


class SoloCliente(_Base):
    permission_classes = [HasRole("cliente")]


class AdminOBarbero(_Base):
    permission_classes = [HasRole("admin", "barbero")]


class AdminOBarberoComposicion(_Base):
    permission_classes = [HasRole("admin") | HasRole("barbero")]


class AutenticadoYAdmin(_Base):
    permission_classes = [IsAuthenticated & HasRole("admin")]


class SinAutenticadores(APIView):
    authentication_classes = []
    permission_classes = [HasRole("admin")]

    def get(self, request):
        return Response({"ok": True})


# --- Helpers -------------------------------------------------------------


def _usuario(django_user_model, rol, nombre=None):
    nombre = nombre or f"{rol}@test.com"
    usuario = django_user_model.objects.create_user(
        username=nombre, email=nombre, password="x"
    )
    usuario.perfil.role = rol
    usuario.perfil.save()
    return usuario


def _llamar(vista, usuario=None):
    request = fabrica.get("/")
    if usuario is not None:
        force_authenticate(request, user=usuario)
    return vista.as_view()(request)


def _llamar_con_token(vista, token):
    request = fabrica.get("/", HTTP_AUTHORIZATION=f"Bearer {token}")
    return vista.as_view()(request)


@pytest.fixture
def cliente(django_user_model):
    return _usuario(django_user_model, "cliente")


@pytest.fixture
def barbero(django_user_model):
    return _usuario(django_user_model, "barbero")


@pytest.fixture
def admin(django_user_model):
    return _usuario(django_user_model, "admin")


# --- Casos obligatorios --------------------------------------------------


def test_cliente_accediendo_a_un_recurso_admin_recibe_403(cliente):
    respuesta = _llamar(SoloAdmin, cliente)

    assert respuesta.status_code == 403


def test_admin_accediendo_a_un_recurso_admin_tiene_acceso(admin):
    respuesta = _llamar(SoloAdmin, admin)

    assert respuesta.status_code == 200
    assert respuesta.data == {"ok": True}


# --- Matriz de roles -----------------------------------------------------


@pytest.mark.parametrize(
    ("vista", "rol", "esperado"),
    [
        (SoloAdmin, "admin", 200),
        (SoloAdmin, "barbero", 403),
        (SoloAdmin, "cliente", 403),
        (SoloBarbero, "barbero", 200),
        (SoloBarbero, "admin", 403),
        (SoloBarbero, "cliente", 403),
        (SoloCliente, "cliente", 200),
        (SoloCliente, "admin", 403),
        (SoloCliente, "barbero", 403),
    ],
)
def test_cada_rol_solo_accede_a_lo_suyo(django_user_model, vista, rol, esperado):
    usuario = _usuario(django_user_model, rol)

    assert _llamar(vista, usuario).status_code == esperado


@pytest.mark.parametrize("vista", [AdminOBarbero, AdminOBarberoComposicion])
@pytest.mark.parametrize(
    ("rol", "esperado"), [("admin", 200), ("barbero", 200), ("cliente", 403)]
)
def test_varios_roles_o_composicion_permiten_cualquiera_de_ellos(
    django_user_model, vista, rol, esperado
):
    usuario = _usuario(django_user_model, rol)

    assert _llamar(vista, usuario).status_code == esperado


def test_se_compone_con_is_authenticated(admin, cliente):
    assert _llamar(AutenticadoYAdmin, admin).status_code == 200
    assert _llamar(AutenticadoYAdmin, cliente).status_code == 403


# --- Usuarios sin sesion o sin perfil -----------------------------------


def test_sin_token_retorna_401_cuando_la_vista_autentica_con_jwt():
    respuesta = _llamar(SoloAdmin)

    assert respuesta.status_code == 401


def test_sin_autenticadores_retorna_403_y_nunca_concede_acceso():
    assert _llamar(SinAutenticadores).status_code == 403


def test_token_invalido_retorna_401():
    assert _llamar_con_token(SoloAdmin, "token-invalido").status_code == 401


def test_usuario_anonimo_no_tiene_permiso():
    request = fabrica.get("/")
    request.user = AnonymousUser()

    assert HasRole("admin")().has_permission(request, view=None) is False


def test_usuario_sin_perfil_se_trata_como_cliente(django_user_model, cliente):
    PerfilUsuario.objects.filter(user=cliente).delete()
    cliente = django_user_model.objects.get(pk=cliente.pk)

    assert _llamar(SoloAdmin, cliente).status_code == 403
    assert _llamar(SoloCliente, cliente).status_code == 200


def test_ser_superusuario_no_reemplaza_al_rol(django_user_model):
    # Dado un superusuario de Django cuyo rol de aplicacion es cliente
    root = django_user_model.objects.create_superuser(
        username="root", email="root@test.com", password="x"
    )
    root.perfil.role = Rol.CLIENTE
    root.perfil.save()

    # Entonces HasRole decide por el rol, no por is_superuser ni is_staff
    assert _llamar(SoloAdmin, root).status_code == 403


# --- El rol sale de la base, no del claim del token ---------------------


def test_un_token_emitido_como_admin_pierde_acceso_si_el_rol_baja(admin):
    # Dado un access token emitido cuando el usuario era admin
    token = LoginTokenSerializer.get_token(admin).access_token
    assert token["role"] == "admin"
    assert _llamar_con_token(SoloAdmin, str(token)).status_code == 200

    # Cuando el usuario es degradado a cliente antes de que el token venza
    admin.perfil.role = Rol.CLIENTE
    admin.perfil.save()

    # Entonces el mismo token ya no abre recursos admin
    assert _llamar_con_token(SoloAdmin, str(token)).status_code == 403


def test_un_token_emitido_como_cliente_gana_acceso_si_el_rol_sube(cliente):
    token = LoginTokenSerializer.get_token(cliente).access_token
    assert _llamar_con_token(SoloAdmin, str(token)).status_code == 403

    cliente.perfil.role = Rol.ADMIN
    cliente.perfil.save()

    assert _llamar_con_token(SoloAdmin, str(token)).status_code == 200


# --- Contrato de la fabrica ---------------------------------------------


def test_has_role_devuelve_una_clase_de_permiso_que_drf_puede_instanciar():
    permiso = HasRole("admin")

    assert isinstance(permiso, type)
    assert issubclass(permiso, BasePermission)
    assert issubclass(permiso, RolRequerido)
    assert isinstance(permiso(), BasePermission)


def test_expone_los_roles_exigidos():
    assert HasRole("admin").roles == frozenset({"admin"})
    assert HasRole("barbero", "admin").roles == frozenset({"admin", "barbero"})


def test_acepta_miembros_del_enum_y_cadenas():
    assert HasRole(Rol.ADMIN).roles == HasRole("admin").roles


def test_el_mismo_conjunto_de_roles_reutiliza_la_clase():
    assert HasRole("admin", "barbero") is HasRole("barbero", "admin")
    assert HasRole("admin") is not HasRole("barbero")


def test_la_clase_tiene_un_nombre_legible_para_depurar():
    assert HasRole("admin", "barbero").__name__ == "HasRole_admin_barbero"


@pytest.mark.parametrize(
    "invalido",
    ["superadmin", "ADMIN", "Admin", " admin", "", None, 7],
    ids=repr,
)
def test_un_rol_desconocido_falla_al_definir_la_vista(invalido):
    # Un error de tipeo debe romper al importar, no dejar una ruta sin proteger
    with pytest.raises(ValueError, match="admin"):
        HasRole(invalido)


def test_sin_roles_falla_al_definir_la_vista():
    with pytest.raises(ValueError):
        HasRole()


@pytest.mark.parametrize("rol", list(Rol))
def test_todo_rol_del_enum_es_valido_sin_tocar_el_permiso(rol):
    # Extensible: los roles validos salen de Rol; agregar un miembro al enum
    # basta para poder usarlo en HasRole("nuevo-rol")
    assert HasRole(rol.value).roles == frozenset({rol.value})


def test_el_permiso_deniega_con_un_mensaje_claro(cliente):
    respuesta = _llamar(SoloAdmin, cliente)

    assert respuesta.data["detail"] == "No tienes permiso para realizar esta accion."
