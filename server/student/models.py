from django.db import models
from django.conf import settings
import uuid


# Create your models here.
class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile",
    )
    student_name = models.CharField(max_length=100)
    student_id_num = models.CharField(max_length=20, unique=True)
    id_card_img_url = models.URLField(max_length=200)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.student_name


class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    ecart = models.ForeignKey("ecart.ECart", on_delete=models.CASCADE)
    fare = models.DecimalField(max_digits=10, decimal_places=2)
    STATUS = (
        ("started", "Started"),
        ("completed", "Completed"),
    )
    status = models.CharField(max_length=10, choices=STATUS, default="started")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trip {self.id} - {self.student.student_name} - {self.ecart.ecart_id_num}"


class PaymentInvoice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    invoice_id = models.CharField(unique=True, max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    platform_charge = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
