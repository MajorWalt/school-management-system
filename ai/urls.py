from django.urls import path
from . import views

app_name = "ai"

urlpatterns = [
    path("settings/", views.settings_view, name="settings"),
    path("test/", views.test_view, name="test"),
]
