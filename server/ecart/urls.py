from django.urls import path
from ecart.views import StudentOpsView

urlpatterns = [
    path("student-ops/", StudentOpsView.as_view(), name="student-ops"),
]
