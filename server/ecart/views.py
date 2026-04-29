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
from decimal import Decimal
from django.db.models import Sum

# models
from ecart.models import ECart
from student.models import Student, Trip

# serializers
from student.serializers import TripSerializer


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
        action = request.query_params.get("action")
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
            student = Student.objects.filter(student_id_num=card_id).first()
            if not student:
                return Response(
                    {"success": False, "message": "Student not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )

            # check if student is already on a trip in this ecart
            existing_trip = Trip.objects.filter(
                student=student, ecart=request.user.ecart_profile, status="started"
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
            if student.balance <= Decimal("10.00"):
                return Response(
                    {"success": False, "message": "Insufficient balance."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            # deduct fare from balance
            fare = Decimal("10.00")  # Assuming a fixed fare for simplicity
            student.balance -= fare
            student.save()

            # create a trip instance
            trip = Trip.objects.create(
                student=student,
                ecart=request.user.ecart_profile,
                fare=fare,
                status="started",
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

        else:
            return Response(
                {"success": False, "message": "Invalid action."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ECartProfileView(APIView):
    permission_classes = [AuthenticateOnlyEcart]

    def get(self, request):
        view = request.query_params.get("view")
        if view == "profile":
            ecart = request.user.ecart_profile
            return Response(
                {
                    "success": True,
                    "ecart": {
                        "id": ecart.id,
                        "ecart_id_num": ecart.ecart_id_num,
                        "driver_name": ecart.driver_name,
                        "driver_phone_number": ecart.driver_phone_number,
                        "driver_photo_url": ecart.driver_photo_url,
                        "is_online": ecart.is_online,
                        "latitude": str(ecart.latitude),
                        "longitude": str(ecart.longitude),
                    },
                },
                status=status.HTTP_200_OK,
            )

        if view == "stats":
            todays_earnings = Trip.objects.filter(
                ecart=request.user.ecart_profile,
                created_at__date=timezone.now().date(),
                status="completed",
            ).aggregate(total_earnings=Sum("fare"))["total_earnings"] or Decimal("0.00")
            total_trips_today = Trip.objects.filter(
                ecart=request.user.ecart_profile,
                created_at__date=timezone.now().date(),
            ).count()
            occupied_count = Trip.objects.filter(
                ecart=request.user.ecart_profile, status="started"
            ).count()

            return Response(
                {
                    "success": True,
                    "stats": {
                        "todays_earnings": str(todays_earnings),
                        "total_trips_today": total_trips_today,
                        "occupied_count": occupied_count,
                    },
                },
                status=status.HTTP_200_OK,
            )


class RideHistoryView(APIView):
    permission_classes = [AuthenticateOnlyEcart]

    def get(self, request, *args, **kwargs):
        total_trips = Trip.objects.filter(ecart=request.user.ecart_profile).count()
        total_earnings = Trip.objects.filter(
            ecart=request.user.ecart_profile, status="completed"
        ).aggregate(total_earnings=Sum("fare"))["total_earnings"] or Decimal("0.00")
        avg_fee = float(total_earnings) / total_trips if total_trips > 0 else 0.00

        trips = Trip.objects.filter(ecart=request.user.ecart_profile).order_by(
            "-created_at"
        )
        paginator = StandardResultsSetPagination()
        paginated_trips = paginator.paginate_queryset(trips, request)
        serializer = TripSerializer(paginated_trips, many=True)

        return Response(
            {
                "success": True,
                "total_trips": total_trips,
                "total_earnings": str(total_earnings),
                "avg_fee": str(avg_fee),
                "trips": paginator.get_paginated_response(serializer.data).data,
            },
            status=status.HTTP_200_OK,
        )


class EarningsAPIView(APIView):
    permission_classes = [AuthenticateOnlyEcart]

    def get(self, request):
        todays_earnings = Trip.objects.filter(
            ecart=request.user.ecart_profile,
            created_at__date=timezone.now().date(),
            status="completed",
        ).aggregate(total_earnings=Sum("fare"))["total_earnings"] or Decimal("0.00")
        this_week_earnings = Trip.objects.filter(
            ecart=request.user.ecart_profile,
            created_at__week=timezone.now().isocalendar()[1],
            created_at__year=timezone.now().year,
            status="completed",
        ).aggregate(total_earnings=Sum("fare"))["total_earnings"] or Decimal("0.00")
        trips_today = Trip.objects.filter(
            ecart=request.user.ecart_profile,
            created_at__date=timezone.now().date(),
            status="completed",
        ).count()

        todays_rides = Trip.objects.filter(
            ecart=request.user.ecart_profile,
            created_at__date=timezone.now().date(),
            status="completed",
        )

        serializer = TripSerializer(todays_rides, many=True)
        return Response(
            {
                "success": True,
                "cart_id": request.user.ecart_profile.ecart_id_num,
                "todays_earnings": str(todays_earnings),
                "this_week_earnings": str(this_week_earnings),
                "trips_today": trips_today,
                "todays_rides": serializer.data,
            },
            status=status.HTTP_200_OK,
        )
