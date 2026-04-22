from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    # Boolean fields to select the type of account.
    ROLES = (
        ("student", "student"),
        ("admin", "admin"),
        ("ecart", "ecart"),
    )
    role = models.CharField(choices=ROLES, default="student")

    def __str__(self):
        return self.username
