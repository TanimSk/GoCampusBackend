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

# models
from ecart.models import ECart
from student.models import Student, Trip


# Authenticate only Ecart
class AuthenticateOnlyEcart(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            raise PermissionDenied("User is not authenticated.")

        if not request.user.role == "ecart":
            raise PermissionDenied("User is not an Ecart.")

        return True


class StudentOpsView(APIView):
    permission_classes = [AuthenticateOnlyEcart]

    def post(self, request):
        action = request.data.get("action")
        if action == "scan-id":
            # workflow:
            # 1. get student
            # 2. check if already on a trip
            # 3. if on a trip, complete the trip and return response
            # 4. if not on a trip, check balance and start a new trip

            card_id = request.data.get("card_id")

            # validation
            if not card_id:
                return Response(
                    {"success": False, "message": "Card ID is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # query in DB
            student = Student.objects.filter(card_id=card_id).first()
            if not student:
                return Response(
                    {"success": False, "message": "Student not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # check if student is already on a trip in this ecart
            existing_trip = Trip.objects.filter(
                student=student, ecart=request.user, status="started"
            ).first()
            if existing_trip:
                existing_trip.status = "completed"
                existing_trip.save()

                # return response indicating trip completion
                return Response(
                    {
                        "success": True,
                        "message": "Trip completed successfully.",
                        "student": {
                            "name": student.student_name,
                            "student_id_num": student.student_id_num,
                            "balance": student.balance,
                        },
                        "trip": {
                            "id": existing_trip.id,
                            "fare": existing_trip.fare,
                            "status": existing_trip.status,
                        },
                    },
                    status=status.HTTP_200_OK,
                )

            # check balance
            if student.balance <= 10:
                return Response(
                    {"success": False, "message": "Insufficient balance."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # deduct fare from balance
            fare = 10.00  # Assuming a fixed fare for simplicity
            student.balance -= fare
            student.save()

            # create a trip instance
            trip = Trip.objects.create(
                student=student, ecart=request.user, fare=fare, status="started"
            )

            # return success response with student details and trip info
            return Response(
                {
                    "success": True,
                    "message": "ID scanned successfully.",
                    "student": {
                        "name": student.student_name,
                        "student_id_num": student.student_id_num,
                        "balance": student.balance,
                    },
                    "trip": {
                        "id": trip.id,
                        "fare": trip.fare,
                        "status": trip.status,
                    },
                },
                status=status.HTTP_200_OK,
            )
