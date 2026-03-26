from dj_rest_auth.registration.serializers import RegisterSerializer
from rest_framework import serializers
from student.models import Student


# Custom Registration
class StudentRegistrationSerializer(RegisterSerializer):
    agent = serializers.PrimaryKeyRelatedField(
        read_only=True,
    )  # by default allow_null = False
    name = serializers.CharField(required=True)
    mobile_no = serializers.IntegerField(required=True)
    ...

    def get_cleaned_data(self):
        data = super(StudentRegistrationSerializer, self).get_cleaned_data()
        extra_data = {
            "name": self.validated_data.get("name", ""),
            "mobile_no": self.validated_data.get("mobile_no", ""),
        }
        data.update(extra_data)
        return data

    def save(self, request):
        user = super(StudentRegistrationSerializer, self).save(request)
        user.is_agent = True
        user.first_name = self.cleaned_data.get("name")
        user.save()
        agent = Student(
            agent=user,
            name=self.cleaned_data.get("name"),
            mobile_no=self.cleaned_data.get("mobile_no"),
        )
        agent.save()
        return user
