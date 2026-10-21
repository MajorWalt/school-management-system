from django.urls import path

from core import search
from . import views

app_name = "core"

urlpatterns = [
    path("activity/", views.activity_log, name="activity_log"),
    path("search/", search.global_search, name="global_search"),
]
