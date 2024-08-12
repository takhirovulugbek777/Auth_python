from django.urls import path

from .views import *

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('login/refresh/', LoginRefreshView.as_view(), name='refresh'),
    path('logout/', LogOutView.as_view(), name='logout'),
    path('signup/', CreateUserView.as_view(), name='signup'),
    path('verify/', VerifyAPIView.as_view(), name='verify'),
    path('new-verfy/', GetNewVerification.as_view(), name='new-verify'),
    path('change_user/', ChangeUserInformationView.as_view(), name='change-user'),
    path('change_photo/', ChangeUserPhotoView.as_view(), name='change-photo'),
    path('forgot-password/', ForgotPasswordView.as_view()),
    path('reset-password/', ResetPasswordView.as_view()),

]
