from django.urls import path
from . import views

app_name = "behaviour"

urlpatterns = [
    path("", views.incident_list, name="incident_list"),
    path("new/", views.incident_create, name="incident_create"),
    path("<int:pk>/", views.incident_detail, name="incident_detail"),
    path("<int:pk>/edit/", views.incident_edit, name="incident_edit"),
    path("<int:pk>/delete/", views.incident_delete, name="incident_delete"),
]
