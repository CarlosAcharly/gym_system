from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):

    # Campos que se muestran al editar usuario
    fieldsets = UserAdmin.fieldsets + (
        ('Rol del sistema', {'fields': ('role',)}),
    )

    # Campos al crear usuario
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Rol del sistema', {'fields': ('role',)}),
    )

    list_display = ('username', 'email', 'role', 'is_staff', 'is_superuser')
    list_filter = ('role',)
