from django.urls import path
from . import views

app_name = "staff"

urlpatterns = [
	path("",                      views.staff_list,       name="list"),
	path("add/",                  views.staff_add,        name="add"),
	path("<int:pk>/",             views.staff_detail,     name="detail"),
	path("<int:pk>/edit/",        views.staff_edit,       name="edit"),
	path("<int:pk>/deactivate/",  views.staff_deactivate, name="deactivate"),
	path("<int:pk>/reactivate/",  views.staff_reactivate, name="reactivate"),
]