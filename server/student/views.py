from django.shortcuts import render, HttpResponse
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.permissions import BasePermission
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
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
from utils.payment import payment
from utils.redis_handler import get_sync_redis
from decimal import Decimal
from utils.shared import StandardResultsSetPagination

# models
from student.models import Student
from student.models import Trip

# serializers
from student.serializers import StudentSerializer, TripSerializer


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


class StudentProfileView(APIView):
    permission_classes = [IsAuthenticated, AuthenticateOnlyStudent]

    def get(self, request, *args, **kwargs):
        view = request.query_params.get("view")

        if view == "profile":
            student_profile = request.user.student_profile
            serializer = StudentSerializer(student_profile)

            return Response({"success": True, "data": serializer.data})

        if view == "stats":
            student_profile = request.user.student_profile
            total_rides = Trip.objects.filter(student=student_profile).count()
            last_ride_fare = (
                Trip.objects.filter(student=student_profile)
                .order_by("-created_at")
                .first()
            )
            last_ride_fare = last_ride_fare.fare if last_ride_fare else Decimal("0.00")

            data = {
                "student_name": student_profile.student_name,
                "total_rides": total_rides,
                "balance": student_profile.balance,
                "last_ride_fare": last_ride_fare,
            }
            return Response({"success": True, "data": data})


class RideHistoryView(APIView):
    permission_classes = [AuthenticateOnlyStudent]

    def get(self, request, *args, **kwargs):
        trips = Trip.objects.filter(student=request.user.student_profile).order_by(
            "-created_at"
        )
        paginator = StandardResultsSetPagination()
        paginated_trips = paginator.paginate_queryset(trips, request)
        serializer = TripSerializer(paginated_trips, many=True)
        return paginator.get_paginated_response(serializer.data)


class PaymentOpsView(APIView):
    redis_client = get_sync_redis()

    def post(self, request, *args, **kwargs):
        tran_id = request.query_params.get("trans-id")
        status_param = request.query_params.get("status")

        if status_param == "success":
            amount = request.data.get("amount")
            stored_json = self.redis_client.get(f"payment-{tran_id}")

            if not stored_json:
                return HttpResponse(
                    "Session expired or invalid transaction ID",
                    status=status.HTTP_400_BAD_REQUEST,
                )
            stored_json = json.loads(stored_json)

            student_id_num = stored_json.get("student_id")

            if not amount or not student_id_num:
                return HttpResponse(
                    "Invalid payment info in cache",
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                student_profile = Student.objects.get(student_id_num=student_id_num)
                student_profile.balance += Decimal(str(amount))
                student_profile.save()

                # remove payment info from cache
                self.redis_client.delete(f"payment-{tran_id}")

                return HttpResponse("Payment successful", status=status.HTTP_200_OK)
            except Student.DoesNotExist:
                return HttpResponse(
                    "Student not found", status=status.HTTP_404_NOT_FOUND
                )
            except Exception as e:
                return HttpResponse(
                    f"Error processing payment: {str(e)}",
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )
        else:
            return HttpResponse(f"Payment {status_param}", status=status.HTTP_200_OK)


class PaymentView(APIView):
    permission_classes = [AuthenticateOnlyStudent]

    def post(self, request, *args, **kwargs):
        action = request.query_params.get("action")

        if action == "top-up":
            amount = request.data.get("amount")

            if not amount:
                return Response(
                    {"success": False, "message": "Amount is required"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            try:
                amount = float(amount)
            except ValueError:
                return Response(
                    {"success": False, "message": "Invalid amount format"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            payload = {
                "customer_name": request.user.student_profile.student_name,
                "amount": amount,
                "student_id": request.user.student_profile.student_id_num,
            }

            payment_response = payment(payload)
            return Response({"success": True, "payment_response": payment_response})
