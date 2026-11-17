from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied


def operator_required(permission):
    def decorate(view):
        @wraps(view)
        def wrapped(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not request.user.is_active or not request.user.is_staff or not request.user.has_perm(permission):
                raise PermissionDenied('Ushbu amal uchun vakolatingiz yo‘q.')
            return view(request, *args, **kwargs)
        return wrapped
    return decorate
