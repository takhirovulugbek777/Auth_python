from django.urls import path

from .views import *

urlpatterns = [
    path('signup/', CreateUserView.as_view(), name='signup'),
    path('verify/', VerifyAPIView.as_view(), name='verify'),
    path('new-verfy/', GetNewVerification.as_view(), name='new-verify'),
    path('change_user/', ChangeUserInformationView.as_view(), name='change-user'),
]
