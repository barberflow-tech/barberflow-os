"""SUB-06-A: infraestructura persistente de roles (admin, barbero, cliente)."""

import pytest
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor

from apps.barberias.models import Barberia, Membresia
from apps.usuarios.models import PerfilUsuario, Rol, rol_de

pytestmark = pytest.mark.django_db


def test_roles_validos_son_admin_barbero_cliente_en_minusculas():
    # Dado el catalogo de roles
    # Entonces solo existen estos tres valores, todos en minusculas
    assert set(Rol.values) == {"admin", "barbero", "cliente"}
    assert all(valor == valor.lower() for valor in Rol.values)


def test_usuario_nuevo_queda_con_rol_cliente_por_defecto(django_user_model):
    # Dado un usuario creado sin indicar rol
    usuario = django_user_model.objects.create_user(username="ana", password="x")

    # Entonces tiene perfil y su rol es cliente
    assert usuario.perfil.role == Rol.CLIENTE
    assert rol_de(usuario) == "cliente"


def test_cliente_sin_barberia_tiene_rol_y_no_necesita_membresia(django_user_model):
    # Dado un cliente que no esta vinculado a ninguna barberia
    usuario = django_user_model.objects.create_user(username="ana", password="x")

    # Entonces conserva su rol aunque no exista Membresia
    assert not Membresia.objects.filter(user=usuario).exists()
    assert rol_de(usuario) == "cliente"


def test_el_rol_no_depende_de_la_membresia(django_user_model):
    # Dado un barbero con y sin Membresia
    usuario = django_user_model.objects.create_user(username="juan", password="x")
    usuario.perfil.role = Rol.BARBERO
    usuario.perfil.save()
    assert rol_de(usuario) == "barbero"

    # Cuando se vincula a una barberia, el rol no cambia
    Membresia.objects.create(
        user=usuario, barberia=Barberia.objects.create(name="Centro")
    )
    usuario.refresh_from_db()
    assert rol_de(usuario) == "barbero"
    assert not hasattr(Membresia, "role")


def test_save_normaliza_el_rol_a_minusculas(django_user_model):
    usuario = django_user_model.objects.create_user(username="eva", password="x")

    perfil = usuario.perfil
    perfil.role = "  ADMIN "
    perfil.save()

    perfil.refresh_from_db()
    assert perfil.role == "admin"


def test_rol_invalido_es_rechazado_por_validacion(django_user_model):
    from django.core.exceptions import ValidationError

    usuario = django_user_model.objects.create_user(username="eva", password="x")
    usuario.perfil.role = "superadmin"

    with pytest.raises(ValidationError):
        usuario.perfil.full_clean()


def test_la_base_rechaza_un_rol_fuera_del_catalogo(django_user_model):
    # Dado un camino que se salta save() (update masivo)
    usuario = django_user_model.objects.create_user(username="eva", password="x")

    # Entonces PostgreSQL rechaza el valor por el CHECK
    with pytest.raises(IntegrityError), transaction.atomic():
        PerfilUsuario.objects.filter(user=usuario).update(role="ADMIN")


def test_rol_de_devuelve_cliente_si_el_perfil_no_existe(django_user_model):
    # Dado un usuario cuyo perfil se borro por fuera del flujo normal
    usuario = django_user_model.objects.create_user(username="ana", password="x")
    PerfilUsuario.objects.filter(user=usuario).delete()
    usuario = django_user_model.objects.get(pk=usuario.pk)

    # Entonces se trata como cliente (el menor privilegio)
    assert rol_de(usuario) == "cliente"


def test_rol_de_usuario_anonimo_es_none():
    from django.contrib.auth.models import AnonymousUser

    assert rol_de(AnonymousUser()) is None


@pytest.mark.django_db(transaction=True)
def test_migracion_crea_perfil_para_usuarios_existentes():
    """Compatibilidad: usuarios previos a SUB-06-A reciben perfil al migrar.

    Superusuarios -> admin; el resto -> cliente.
    """
    executor = MigrationExecutor(connection)
    anterior = [("usuarios", "0001_initial")]
    ultima = executor.loader.graph.leaf_nodes("usuarios")

    # Dado el esquema sin perfiles y usuarios que ya existian
    executor.migrate(anterior)
    apps_antes = executor.loader.project_state(anterior).apps
    User = apps_antes.get_model("auth", "User")
    User.objects.create(username="viejo_cliente", password="x")
    User.objects.create(username="viejo_root", password="x", is_superuser=True)

    # Cuando se aplica la migracion de datos
    executor = MigrationExecutor(connection)
    executor.migrate(ultima)

    # Entonces todos tienen perfil y rol valido
    roles = dict(PerfilUsuario.objects.values_list("user__username", "role"))
    assert roles["viejo_cliente"] == "cliente"
    assert roles["viejo_root"] == "admin"
