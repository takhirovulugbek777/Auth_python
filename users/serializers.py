from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.contrib.auth.password_validation import validate_password
from django.core.validators import FileExtensionValidator
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework_simplejwt.serializers import TokenObtainSerializer, TokenRefreshSerializer
from rest_framework_simplejwt.tokens import AccessToken

from shared.utility import check_email_or_phone, send_email, send_phone_code, check_user_type
from .models import User, VIA_EMAIL, VIA_PHONE, CODE_VERIFIED, DONE, PHOTO_DONE, NEW
from rest_framework import serializers, status
from rest_framework.exceptions import ValidationError, PermissionDenied, NotFound
import uuid


class SignUpSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)

    def __init__(self, *args, **kwargs):
        super(SignUpSerializer, self).__init__(*args, **kwargs)
        self.fields['email_phone_number'] = serializers.CharField(required=False)

    class Meta:
        model = User
        fields = (
            'id',
            'auth_type',
            'auth_status'
        )
        extra_kwargs = {
            'auth_type': {'read_only': True, 'required': False},
            'auth_status': {'read_only': True, 'required': False}
        }

    def create(self, validated_data):
        user = super(SignUpSerializer, self).create(validated_data)
        if user.auth_type == VIA_EMAIL:
            code = user.create_verify_code(VIA_EMAIL)
            send_email(user.email, code)
        elif user.auth_type == VIA_PHONE:
            code = user.create_verify_code(VIA_PHONE)
            send_email(user.phone_number, code)
            # send_phone_code(user.phone_number, code)
        user.save()
        return user

    def validate(self, data):
        super(SignUpSerializer, self).validate(data)
        data = self.auth_validate(data)
        return data

    @staticmethod
    def auth_validate(data):
        print(data)
        user_input = str(data.get('email_phone_number')).lower()
        input_type = check_email_or_phone(user_input)  # email or phone
        if input_type == "email":
            data = {
                "email": user_input,
                "auth_type": VIA_EMAIL
            }
        elif input_type == "phone":
            data = {
                "phone_number": user_input,
                "auth_type": VIA_PHONE
            }
        else:
            data = {
                'success': False,
                'message': "You must send email or phone number"
            }
            raise ValidationError(data)

        return data

    def validate_email_phone_number(self, value):
        value = value.lower()
        if value and User.objects.filter(email=value).exists():
            data = {
                "success": False,
                "message": "Bu email allaqachon ma'lumotlar bazasida bor"
            }
            raise ValidationError(data)
        elif value and User.objects.filter(phone_number=value).exists():
            data = {
                "success": False,
                "message": "Bu telefon raqami allaqachon ma'lumotlar bazasida bor"
            }
            raise ValidationError(data)

        return value

    def to_representation(self, instance):
        data = super(SignUpSerializer, self).to_representation(instance)
        data.update(instance.token())

        return data


class ChangeUserInformation(serializers.Serializer):
    first_name = serializers.CharField(required=True, write_only=True)
    last_name = serializers.CharField(required=True, write_only=True)
    username = serializers.CharField(required=True, write_only=True)
    password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, data):
        password = data.get('password', None)
        confirm_password = data.get('confirm_password', None)

        if password != confirm_password:
            raise ValidationError(
                {
                    "massage": 'Passwords do not match'
                }
            )
        if password:
            validate_password(password)
            validate_password(confirm_password)

        return data

    def validate_username(self, username):
        if len(username) < 5 or len(username) > 20:
            raise ValidationError({'massage': 'Username must be between 5 and 20 characters long.'})
        if username.isdigit():
            raise ValidationError({'massage': 'Username must be digest.'})

        return username

    #
    # def validate_first_name(self, first_name):
    #     if len(first_name) < 5 or len(first_name) > 20:
    #         raise ValidationError({'massage': 'First name must be between 5 and 20 characters long.'})
    #     if first_name.isdigit():
    #         raise ValidationError({'massage': 'First name must be digest.'})
    #
    #     return first_name
    #
    # def validate_last_name(self, last_name):
    #     if len(last_name) < 5 or len(last_name) > 20:
    #         raise ValidationError({'massage': 'Last name must be between 5 and 20 characters long.'})
    #     if last_name.isdigit():
    #         raise ValidationError({'massage': 'Last name must be digest.'})

    def update(self, instance, validated_data):
        instance.first_name = validated_data.get('first_name', instance.first_name)
        instance.last_name = validated_data.get('last_name', instance.last_name)
        instance.password = validated_data.get('password', instance.password)
        instance.username = validated_data.get('username', instance.username)
        if validated_data.get('password'):
            instance.set_password(validated_data.get('password'))
        if instance.auth_status == CODE_VERIFIED:
            instance.auth_status = DONE
            instance.save()
        instance.save()
        return instance


class ChangeUserPhotoSerializer(serializers.Serializer):
    photo = serializers.ImageField(
        validators=[FileExtensionValidator(allowed_extensions=['png', 'jpg', 'jpeg', 'heic'])])

    def update(self, instance, validated_data):
        photo = validated_data.get('photo', None)
        if photo:
            instance.photo = photo
            instance.auth_status = PHOTO_DONE
            instance.save()

        return instance


class LoginSerializer(TokenObtainSerializer):

    def __init__(self, *args, **kwargs):
        super(LoginSerializer, self).__init__(*args, **kwargs)
        self.fields['userinput'] = serializers.CharField(write_only=True, required=True)
        self.fields['username'] = serializers.CharField(read_only=True, required=False)

    def auth_validate(self, data):
        print(data)
        user_input = data.get('userinput')
        username = None

        if check_user_type(user_input) == 'username':
            username = user_input

        elif check_user_type(user_input) == 'email':
            user = self.get_user(email__iexact=user_input)
            if user:
                username = user.username

        elif check_user_type(user_input) == 'phone':
            user = self.get_user(phone_number=user_input)
            if user:
                username = user.username

        if not username:
            raise ValidationError({
                'success': False,
                'message': "You must send email, phone number, or username"
            })

        authentication_kwargs = {
            self.username_field: username,
            'password': data['password']
        }

        current_user = User.objects.filter(username__iexact=username).first()
        if not current_user:
            raise ValidationError({
                'success': False,
                'message': "User not found"
            })

        if current_user.auth_status in [NEW, CODE_VERIFIED]:
            raise ValidationError({
                'success': False,
                'message': "To'liq ro'yhatdan o'tmagansiz."
            })

        user = authenticate(**authentication_kwargs)
        if user is not None:
            self.user = user
        else:
            raise ValidationError({
                'success': False,
                'message': 'Login failed.',
                'status': status.HTTP_400_BAD_REQUEST
            })

    def validate(self, data):
        self.auth_validate(data)
        if self.user.auth_status not in [DONE, PHOTO_DONE]:
            raise PermissionDenied("Siz to'liq ro'yhatdan o'tib bo'lmagansiz, login qila olmaysiz ruxsat yo'q")
        data = self.user.token()
        data['auth_status'] = self.user.auth_status
        data['fullname'] = self.user.full_name
        data['auth_type'] = self.user.auth_type

        return data

    def get_user(self, **kwargs):
        users = User.objects.filter(**kwargs)
        if not users.exists():
            raise ValidationError({
                'success': False,
                'message': 'User not found',
                'status': status.HTTP_404_NOT_FOUND
            })
        return users.first()


class LoginRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        access_token_instance = AccessToken(data['access'])
        user_id = access_token_instance['user_id']
        user = get_object_or_404(User, id=user_id)
        update_last_login(None, user)
        return data


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class ForgotPasswordSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        email_or_phone = attrs.get('email_or_phone', None)
        if email_or_phone is None:
            raise ValidationError(
                {
                    "success": False,
                    'message': "Email yoki telefon raqami kiritilishi shart!"
                }
            )
        user = User.objects.filter(Q(phone_number=email_or_phone) | Q(email=email_or_phone))
        if not user.exists():
            raise NotFound(detail="User not found")
        attrs['user'] = user.first()
        return attrs


class ResetPasswordSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(read_only=True)
    password = serializers.CharField(min_length=8, required=True, write_only=True)
    confirm_password = serializers.CharField(min_length=8, required=True, write_only=True)

    class Meta:
        model = User
        fields = (
            'id',
            'password',
            'confirm_password'
        )

    def validate(self, data):
        password = data.get('password', None)
        confirm_password = data.get('password', None)
        if password != confirm_password:
            raise ValidationError(
                {
                    'success': False,
                    'message': "Parollaringiz qiymati bir-biriga teng emas"
                }
            )
        if password:
            validate_password(password)
        return data

    def update(self, instance, validated_data):
        password = validated_data.pop('password')
        instance.set_password(password)
        return super(ResetPasswordSerializer, self).update(instance, validated_data)

