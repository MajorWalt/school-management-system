from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("at-risk/", views.risk_list, name="risk_list"),
    path("at-risk/recalculate/", views.risk_recalculate, name="risk_recalculate"),
    path("promotion/", views.promotion_report, name="promotion_report"),
    path("promotion/criteria/", views.criteria_list, name="criteria_list"),
    path("promotion/criteria/<int:form_pk>/", views.criteria_edit, name="criteria_edit"),
    path("promotion/criteria/<int:form_pk>/delete/", views.criteria_delete, name="criteria_delete"),
]