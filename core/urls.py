from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    path("activity/", views.activity_log, name="activity_log"),
]
