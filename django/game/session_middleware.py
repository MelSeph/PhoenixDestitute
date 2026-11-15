"""Keep admin authentication from rotating/deleting anonymous game ownership."""
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware


class GameSessionMiddleware(SessionMiddleware):
    admin_cookie_name = "phoenix_admin_session"

    def process_request(self, request):
        request._separate_admin_session = request.path_info.startswith("/admin/")
        if request._separate_admin_session:
            request.COOKIES = request.COOKIES.copy()
            request.COOKIES.pop(settings.SESSION_COOKIE_NAME, None)
            cookie = request.COOKIES.get(self.admin_cookie_name)
            if cookie:
                request.COOKIES[settings.SESSION_COOKIE_NAME] = cookie
        super().process_request(request)
        if not request._separate_admin_session and request.session.get("_auth_user_id"):
            # One-time compatibility for a staff login made before cookie
            # isolation. Validate it through Django before carrying game data.
            from django.contrib.auth import get_user
            user = get_user(request)
            if user.is_authenticated and user.is_staff:
                from django.db import transaction
                from .models import BirthStatDraft, LocalCharacter
                with transaction.atomic():
                    old_key = request.session.session_key
                    game = self.SessionStore()
                    game.update({key: value for key, value in request.session.items() if not key.startswith("_auth_")})
                    game.create()
                    LocalCharacter.objects.filter(session_id=old_key).update(session_id=game.session_key)
                    BirthStatDraft.objects.filter(session_id=old_key).update(session_id=game.session_key)
                    request.session = game

    def process_response(self, request, response):
        response = super().process_response(request, response)
        if getattr(request, "_separate_admin_session", False) and settings.SESSION_COOKIE_NAME in response.cookies:
            original = response.cookies.pop(settings.SESSION_COOKIE_NAME)
            response.cookies[self.admin_cookie_name] = original.value
            for attribute, value in original.items():
                response.cookies[self.admin_cookie_name][attribute] = value
        return response
