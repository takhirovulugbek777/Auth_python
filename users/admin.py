from django.contrib import admin

from users.models import *


# Register your models here.
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'phone_number')


admin.site.register(User, UserAdmin)
admin.site.register(UserConfirmation)
