from django.shortcuts import render
from django.utils import timezone
from rest_framework import permissions
from rest_framework.generics import CreateAPIView, UpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from datetime import datetime

from users.models import User, DONE, CODE_VERIFIED, NEW
from .serializers import *


# Create your views here.

class CreateUserView(CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = SignUpSerializer


class VerifyAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, *args, **kwargs):
        user = self.request.user  # user ->
        code = self.request.data.get('code')  # 4083

        self.check_verify(user, code)
        return Response(
            data={
                "success": True,
                "auth_status": user.auth_status,
                "access": user.token()['access'],
                "refresh": user.token()['refresh_token']
            }
        )

    @staticmethod
    def check_verify(user, code):  # 12:03 -> 12:05 => expiration_time=12:05   12:04
        verifies = user.verify_codes.filter(expiration_time__gte=datetime.now(), code=code, is_confirmed=False)
        print(verifies)
        if not verifies.exists():
            data = {
                "message": "Tasdiqlash kodingiz xato yoki eskirgan"
            }
            raise ValidationError(data)
        else:
            verifies.update(is_confirmed=True)
        if user.auth_status == NEW:
            user.auth_status = CODE_VERIFIED
            user.save()
        return True


class GetNewVerification(APIView):
    def get(self, request, *args, **kwargs):
        user = self.request.user
        self.check_verification(user)
        if user.auth_type == VIA_EMAIL:
            code = user.create_verify_code(VIA_EMAIL)
            send_email(user.email, code)

        elif user.auth_type == VIA_PHONE:
            code = user.create_verify_code(VIA_PHONE)
            send_email(user.phone_number, code)
        else:
            data = {
                "success": False,
                "massage": "Email yoki telefon raqam xato."
            }
            raise ValidationError(data)
        return Response({
            "success": True,
            "massage": 'Tasdizlash kodingiz qaytadan yuborildi.'
        })

    @staticmethod
    def check_verification(user):
        verifies = user.verify_codes.filter(expiration_time__gte=datetime.now(), is_confirmed=False)

        if verifies.exists():
            data = {
                "success": False,
                "massage": "So'rov yuborish vaqt oralig'i 2 daqiqa "
            }
            raise ValidationError(data)


class ChangeUserInformationView(UpdateAPIView):
    permissions_class = [IsAuthenticated]
    serializer_class = ChangeUserInformation
    http_method_names = ['put', 'patch']

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        super(ChangeUserInformationView, self).update(request, *args, **kwargs)

        data = {

            'success': True,
            'massage': 'User updated successfully',
            'auth_status': self.request.user.auth_status,
        }
        return Response(data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        super(ChangeUserInformationView, self).partial_update(request, *args, **kwargs)

        data = {

            'success': True,
            'massage': 'User updated successfully',
            'auth_status': self.request.user.auth_status,
        }
        return Response(data, status=status.HTTP_200_OK)
