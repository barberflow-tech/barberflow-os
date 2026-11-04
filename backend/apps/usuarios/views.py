from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError

from .cookies import borrar_cookie_refresh, nombre_cookie_refresh, poner_cookie_refresh
from .models import rol_de
from .permissions import HasRole, OrigenPermitido
from .serializers import LoginSerializer, RegistroSerializer
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
