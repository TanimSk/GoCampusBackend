from rest_framework import serializers
from student.models import Student, Trip
from ecart.models import ECart


class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Student
        fields = "__all__"
        read_only_fields = ("id", "student", "balance", "created_at")


class ECartSerializer(serializers.ModelSerializer):
    class Meta:
        model = ECart
        fields = (
            "ecart_id_num",
            "driver_name",
            "id",
        )


class TripSerializer(serializers.ModelSerializer):
    ecart = ECartSerializer(read_only=True)

    class Meta:
        model = Trip
        fields = "__all__"
        read_only_fields = ("id", "student", "fare", "status", "created_at")
