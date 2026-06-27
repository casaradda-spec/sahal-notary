from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = 'CLIENT', 'Macmiil'
        NOTARY = 'NOTARY', 'Notaayo'
        ADMIN = 'ADMIN', 'Maamule'

    role = models.CharField(max_length=10, choices=Role.choices)
    must_change_password = models.BooleanField(default=True)

    def role_home_url(self):
        return {
            self.Role.CLIENT: '/app/',
            self.Role.NOTARY: '/notary/',
            self.Role.ADMIN: '/admin-panel/reports/',
        }[self.role]
