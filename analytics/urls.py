from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("at-risk/", views.risk_list, name="risk_list"),
    path("at-risk/recalculate/", views.risk_recalculate, name="risk_recalculate"),
]