from django.urls import path
from . import views

app_name = "students"

urlpatterns = [
	path("",                                views.student_list,          name="list"),
	path("add/",                            views.student_add,           name="add"),
	path("bulk/",                           views.student_bulk_enrol,    name="bulk"),
	path("<int:pk>/",                       views.student_detail,        name="detail"),
	path("<int:pk>/edit/",                  views.student_edit,          name="edit"),
	path("<int:pk>/status/",               views.student_status_change,  name="status"),
	path("<int:student_pk>/guardian/add/", views.guardian_add,           name="guardian_add"),
	path("<int:pk>/withdraw/", 			   views.student_withdraw, 		 name="withdraw"),
]   