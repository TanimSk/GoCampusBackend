from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


class User(AbstractUser):
    # Boolean fields to select the type of account.
    is_admin = models.BooleanField(default=False)
    is_student = models.BooleanField(default=False)
    is_ecart = models.BooleanField(default=False)

    def __str__(self):
        return self.username
