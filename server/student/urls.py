from django.urls import path
from student.views import (
    StudentRegistrationView,
    StudentProfileView,
    PaymentView,
    RideHistoryView,
)


urlpatterns = [
    path(
        "registration/", StudentRegistrationView.as_view(), name="student-registration"
    ),
    path("profile/", StudentProfileView.as_view(), name="student-profile"),
    path("payments/", PaymentView.as_view(), name="student-payment"),
    path("ride-history/", RideHistoryView.as_view(), name="student-rides"),
]
