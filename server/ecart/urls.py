
from django.urls import path
from ecart.views import StudentOpsView, ECartProfileView

urlpatterns = [
    path("student-ops/", StudentOpsView.as_view(), name="student-ops"),
    path("profile/", ECartProfileView.as_view(), name="ecart-profile"),
]
