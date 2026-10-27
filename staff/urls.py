from django.urls import path
from . import views

app_name = "staff"

urlpatterns = [
    path("", views.staff_list, name="list"),
    path("add/", views.staff_add, name="add"),
    path("<int:pk>/", views.staff_detail, name="detail"),
    path("<int:pk>/edit/", views.staff_edit, name="edit"),
    path("<int:pk>/deactivate/", views.staff_deactivate, name="deactivate"),
    path("<int:pk>/reactivate/", views.staff_reactivate, name="reactivate"),
    # Clock-in routes
    path("clock-ins/", views.clockin_list, name="clockin_list"),
    path("clock-ins/create/", views.clockin_create, name="clockin_create"),
    path("clock-ins/<int:pk>/edit/", views.clockin_edit, name="clockin_edit"),
    path("clock-ins/<int:pk>/delete/", views.clockin_delete, name="clockin_delete"),
    path("clock-ins/export/", views.clockin_export_excel, name="clockin_export"),
    path("clockin-self/", views.clockin_self, name="clockin_self"),
]
