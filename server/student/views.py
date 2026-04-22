from django.shortcuts import render, HttpResponse
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from django.http import HttpResponse
from django.utils import timezone
from django.conf import settings
from django.db.models import Q
from rest_framework.permissions import BasePermission, IsAuthenticated
from utils.shared import StandardResultsSetPagination
from dj_rest_auth.registration.views import RegisterView
from django.contrib.auth import get_user_model
from django.db import transaction


# models
from student.models import Student


# Authenticate only Student
class AuthenticateOnlyStudent(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("User is not authenticated.")

        if not request.user.role == "student":
            raise PermissionDenied("User is not a Student.")

        return True


User = get_user_model()


class StudentRegistrationView(APIView):
    def post(self, request, *args, **kwargs):
        payload = request.data

        required_fields = ["student_id_card_url", "password1", "password2", "email"]

        for field in required_fields:
            if not payload.get(field):
                return Response(
                    {"success": False, "message": f"{field} is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if payload["password1"] != payload["password2"]:
            return Response(
                {"success": False, "message": "Passwords do not match"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        id_card_url = payload["student_id_card_url"]

        student_name, student_id = self.extract_student_info_from_id_card(id_card_url)

        if not student_name or not student_id:
            return Response(
                {"success": False, "message": "Failed to extract student info"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Student.objects.filter(student_id=student_id).exists():
            return Response(
                {"success": False, "message": "Student already registered"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=payload["email"],
                    email=payload["email"],
                    password=payload["password1"],
                    role="student",
                )

                student_profile = Student.objects.create(
                    student=user,
                    student_name=student_name,
                    student_id=student_id,
                    id_card_img_url=id_card_url,
                )

            return Response(
                {
                    "success": True,
                    "data": {
                        "user_id": user.pk,
                        "student_profile_id": student_profile.pk,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
