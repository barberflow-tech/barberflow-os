from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import (
    APIException,
    AuthenticationFailed,
    ValidationError,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from apps.barberias.models import Membresia, barberia_de

from .cookies import borrar_cookie_refresh, nombre_cookie_refresh, poner_cookie_refresh
from .models import PerfilUsuario, Rol, rol_de
from .permissions import HasRole, OrigenPermitido
from .serializers import (
    CambioDeRolSerializer,
    LoginSerializer,
    RegistroSerializer,
    UsuarioConRolSerializer,
)
from .tokens import LoginTokenSerializer, RefreshTokenSerializer


class RegistroView(APIView):
    """POST /api/v1/auth/register: crea una cuenta de cliente (HU-06).

    Es publica: sin autenticacion, para que un token vencido en el navegador
    no convierta el registro en un 401. No inicia sesion; el frontend lleva al
    usuario al login.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        entrada = RegistroSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        usuario = entrada.save()
        return Response(
            {
                "id": usuario.pk,
                "email": usuario.email,
                "role": usuario.perfil.role,
                "fullName": usuario.perfil.full_name,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """POST /api/v1/auth/login: inicia sesion con email y password.

    Responde {access, user: {id, email, role}}. El refresh token NO va en el
    cuerpo: se entrega solo en una cookie HttpOnly (ver cookies.py). Es publica
    y sin clases de autenticacion para que un token vencido en el navegador no
    impida iniciar sesion.
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        entrada = LoginSerializer(data=request.data, context={"request": request})
        entrada.is_valid(raise_exception=True)
        usuario = entrada.validated_data["user"]

        refresh = LoginTokenSerializer.get_token(usuario)
        respuesta = Response(
            {
                "access": str(refresh.access_token),
                "user": {
                    "id": usuario.pk,
                    "email": usuario.email,
                    "role": rol_de(usuario),
                },
            },
            status=status.HTTP_200_OK,
        )
        poner_cookie_refresh(respuesta, str(refresh))
        # Una respuesta con tokens no debe quedar en caches intermedias.
        respuesta["Cache-Control"] = "no-store"
        return respuesta


class RefreshView(APIView):
    """POST /api/v1/auth/refresh: renueva el access con el refresh de la cookie.

    El refresh token se lee EXCLUSIVAMENTE de la cookie HttpOnly: el cuerpo, la
    query string y las cabeceras ni se consultan. Si la cookie falta, esta
    alterada, es invalida o expiro, responde 401 y la elimina. Responde
    {access, user: {id, email, role}} con el rol y el email vigentes; con
    ROTATE_REFRESH_TOKENS activo, el refresh nuevo reemplaza la cookie.

    Sin clases de autenticacion (un access vencido en la cabecera no debe
    estorbar). Al depender de una cookie, OrigenPermitido rechaza con 403 las
    peticiones de otros sitios (CSRF).
    """

    authentication_classes = []
    permission_classes = [OrigenPermitido]

    def post(self, request):
        refresh = request.COOKIES.get(nombre_cookie_refresh())
        if not refresh:
            return self._sesion_invalida()

        serializador = RefreshTokenSerializer(data={"refresh": refresh})
        try:
            serializador.is_valid(raise_exception=True)
        except (TokenError, AuthenticationFailed, ValidationError):
            return self._sesion_invalida()

        datos = serializador.validated_data
        usuario = serializador.usuario
        respuesta = Response(
            {
                "access": datos["access"],
                "user": {
                    "id": usuario.pk,
                    "email": usuario.email,
                    "role": rol_de(usuario),
                },
            },
            status=status.HTTP_200_OK,
        )
        if "refresh" in datos:  # rotacion: el refresh nuevo solo viaja en la cookie
            poner_cookie_refresh(respuesta, datos["refresh"])
        respuesta["Cache-Control"] = "no-store"
        return respuesta

    @staticmethod
    def _sesion_invalida():
        # Mensaje unico: no revela si la cookie falto, vencio o fue alterada.
        respuesta = Response(
            {"detail": "Sesion invalida o expirada."},
            status=status.HTTP_401_UNAUTHORIZED,
        )
        borrar_cookie_refresh(respuesta)
        respuesta["Cache-Control"] = "no-store"
        return respuesta


class LogoutView(APIView):
    """POST /api/v1/auth/logout: borra la cookie del refresh token.

    Sin esto, cerrar sesion solo limpiaba el estado del navegador y la cookie
    HttpOnly (que el frontend no puede borrar) restauraba la sesion al recargar.
    Es idempotente y publica: si no hay cookie, tambien responde 204.
    """

    authentication_classes = []
    permission_classes = [OrigenPermitido]

    def post(self, request):
        respuesta = Response(status=status.HTTP_204_NO_CONTENT)
        borrar_cookie_refresh(respuesta)
        respuesta["Cache-Control"] = "no-store"
        return respuesta


class ProtectedTestView(APIView):
    """GET /api/v1/auth/protected-test: solo para el rol admin.

    Existe para validar de punta a punta el JWT, la autenticacion y los
    permisos por rol: sin token o con un token invalido responde 401, con un
    rol distinto de admin responde 403 y con admin responde 200. La
    autenticacion (JWT) viene de REST_FRAMEWORK en settings.
    """

    permission_classes = [HasRole("admin")]

    def get(self, request):
        return Response(
            {
                "detail": "Acceso concedido.",
                "user": {
                    "id": request.user.pk,
                    "email": request.user.email,
                    "role": rol_de(request.user),
                },
            }
        )


# --- Asignacion de roles por el administrador (SCRUM-70 / HU-09) ------------

User = get_user_model()

# Roles que necesitan pertenecer a una barberia: al asignarlos a un usuario
# sin barberia, queda vinculado a la del administrador.
ROLES_DEL_PERSONAL = {Rol.ADMIN, Rol.BARBERO}


class AdminSinBarberia(APIException):
    status_code = status.HTTP_409_CONFLICT
    default_detail = "Tu cuenta de administrador no pertenece a ninguna barberia."
    default_code = "admin_sin_barberia"


def _barberia_del_admin(request):
    barberia = barberia_de(request.user)
    if barberia is None:
        raise AdminSinBarberia()
    return barberia


def _usuarios_alcanzables(barberia):
    """Usuarios que el admin puede ver: los de su barberia y los que no tienen barberia.

    Los de otra barberia nunca aparecen: para este admin no existen (404).
    """
    return User.objects.select_related("perfil", "membresia").filter(
        Q(membresia__barberia=barberia) | Q(membresia__isnull=True)
    )


class UsuariosView(APIView):
    """GET /api/v1/users: usuarios de la barberia del admin, con su rol.

    Con ?email=<correo> busca por correo exacto (sin distinguir mayusculas)
    entre los de su barberia y los que aun no tienen barberia, para poder
    ascender a un cliente registrado. Una coincidencia parcial no devuelve nada,
    para no exponer el directorio de clientes.
    """

    permission_classes = [HasRole("admin")]

    def get(self, request):
        barberia = _barberia_del_admin(request)
        email = request.query_params.get("email", "").strip()
        if email:
            usuarios = _usuarios_alcanzables(barberia).filter(email__iexact=email)
        else:
            usuarios = User.objects.select_related("perfil", "membresia").filter(
                membresia__barberia=barberia
            )
        salida = UsuarioConRolSerializer(
            usuarios.order_by("email"), many=True, context={"barberia": barberia}
        )
        return Response(salida.data)


class RolDeUsuarioView(APIView):
    """PATCH /api/v1/users/<id>/role: el admin cambia el rol de un usuario.

    El rol se lee de la base en cada peticion (RolRequerido), asi que el cambio
    rige desde la siguiente peticion del usuario. El admin no puede cambiar su
    propio rol: asi la barberia nunca se queda sin administrador.
    """

    permission_classes = [HasRole("admin")]

    def patch(self, request, usuario_id: int):
        barberia = _barberia_del_admin(request)
        usuario = get_object_or_404(_usuarios_alcanzables(barberia), pk=usuario_id)
        if usuario.pk == request.user.pk:
            return Response(
                {"detail": "No puedes cambiar tu propio rol."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        entrada = CambioDeRolSerializer(data=request.data)
        entrada.is_valid(raise_exception=True)
        rol = entrada.validated_data["role"]

        with transaction.atomic():
            perfil, _ = PerfilUsuario.objects.get_or_create(user=usuario)
            perfil.role = rol
            perfil.save()
            if rol in ROLES_DEL_PERSONAL and not hasattr(usuario, "membresia"):
                usuario.membresia = Membresia.objects.create(
                    user=usuario, barberia=barberia
                )
        usuario.perfil = perfil

        salida = UsuarioConRolSerializer(usuario, context={"barberia": barberia})
        return Response(salida.data)
