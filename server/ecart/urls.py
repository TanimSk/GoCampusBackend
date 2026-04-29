
from django.urls import path
from ecart.views import StudentOpsView, ECartProfileView, RideHistoryView, EarningsAPIView

urlpatterns = [
    path("student-ops/", StudentOpsView.as_view(), name="student-ops"),
    path("profile/", ECartProfileView.as_view(), name="ecart-profile"),
    path("ride-history/", RideHistoryView.as_view(), name="ride-history"),
    path("earnings/", EarningsAPIView.as_view(), name="earnings"),
]
