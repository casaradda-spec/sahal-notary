from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ('Sahal Notary', {'fields': ('role', 'must_change_password')}),
    )
    list_display = ('username', 'first_name', 'last_name', 'role', 'must_change_password', 'is_staff')
    list_filter = UserAdmin.list_filter + ('role',)
