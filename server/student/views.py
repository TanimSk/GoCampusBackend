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
from openai import OpenAI
import re
import json
import base64
import requests


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
client = OpenAI(api_key=settings.OPENAI_API_KEY)


class StudentRegistrationView(APIView):
    def extract_student_info_from_id_card(self, image_url):
        try:
            # 1. Download image into RAM
            response = requests.get(image_url, timeout=10)
            if response.status_code != 200:
                return "", ""

            image_bytes = response.content

            # 2. Convert to base64
            base64_image = base64.b64encode(image_bytes).decode("utf-8")

            # 3. Send to OpenAI
            ai_response = client.chat.completions.create(
                model="gpt-4o-mini",
                temperature=0,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an OCR system that extracts data from student ID cards.\n"
                            "Return ONLY valid JSON with keys:\n"
                            "- student_name (string)\n"
                            "- student_id_num (string)\n\n"
                            "Rules:\n"
                            '1. If student_name is missing or unclear → return ""\n'
                            '2. If student_id_num is missing or unclear → return ""\n'
                            "3. Student ID is numeric → extract only digits\n"
                            "4. Do NOT include explanations or markdown\n"
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract student_name and student_id_num.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                },
                            },
                        ],
                    },
                ],
            )

            content = ai_response.choices[0].message.content.strip()

            # 4. Clean response (handles ```json cases)
            content = re.sub(r"```json|```", "", content).strip()

            data = json.loads(content)

            # 5. Safe fallback
            student_name = data.get("student_name") or ""
            student_id_num = data.get("student_id_num") or ""

            return student_name, student_id_num

        except Exception as e:
            print("Extraction error:", str(e))
            return "", ""

    def post(self, request, *args, **kwargs):
        payload = request.data

        required_fields = ["student_id_card_url", "password1", "password2"]

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

        try:
            student_name, student_id_num = self.extract_student_info_from_id_card(
                id_card_url
            )
        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not student_id_num or not student_name:
            return Response(
                {
                    "success": False,
                    "message": "Failed to extract student info, please ensure the ID card image is clear and try again.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=student_id_num).exists():
            return Response(
                {"success": False, "message": "Student with this ID already exists"},
                status=status.HTTP_400_BAD_REQUEST,
            )        

        if not student_name or not student_id_num:
            return Response(
                {"success": False, "message": "Failed to extract student info"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Student.objects.filter(student_id_num=student_id_num).exists():
            return Response(
                {"success": False, "message": "Student already registered"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=student_id_num,
                    password=payload["password1"],
                    role="student",
                )

                student_profile = Student.objects.create(
                    student=user,
                    student_name=student_name,
                    student_id_num=student_id_num,
                    id_card_img_url=id_card_url,
                )

            return Response(
                {
                    "success": True,
                    "data": {
                        "user_id": user.pk,
                        "student_name": student_profile.student_name,
                        "student_id_num": student_profile.student_id_num,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
