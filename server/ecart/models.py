from django.db import models
from django.conf import settings
import uuid


# Create your models here.
class ECart(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    ecart = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ecart_profile",
    )
    driver_name = models.CharField(max_length=100)
    driver_phone_number = models.CharField(max_length=20)
    driver_photo_url = models.URLField(max_length=200)
    ecart_id = models.CharField(max_length=20, unique=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6)
    longitude = models.DecimalField(max_digits=9, decimal_places=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ecart_id} - {self.driver_name}"
