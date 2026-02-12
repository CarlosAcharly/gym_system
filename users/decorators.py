from django.core.exceptions import PermissionDenied

def allowed_roles(roles=[]):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):

            # Superusuario siempre permitido
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Usuario normal con rol válido
            if hasattr(request.user, 'role') and request.user.role in roles:
                return view_func(request, *args, **kwargs)

            raise PermissionDenied

        return wrapper
    return decorator
