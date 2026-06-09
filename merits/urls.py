from django.urls import path
from . import views

app_name = "merits"

urlpatterns = [
	path("",                                views.merit_list,            name="list"),
	path("add/",                            views.merit_add,             name="add"),
	path("<int:pk>/delete/",                views.merit_delete,          name="delete"),
	path("demerit/add/",                    views.demerit_add,           name="demerit_add"),
	path("demerit/<int:pk>/delete/",        views.demerit_delete,        name="demerit_delete"),
	path("student/<int:student_pk>/",       views.student_merit_report,  name="student_report"),
	path("summary/",                        views.school_summary,        name="summary"),
]