from django.contrib import admin
from .models import Chat, Friend
from users.models import CustomUser


# Register your models here.
admin.site.register(Chat)
admin.site.register(Friend)
