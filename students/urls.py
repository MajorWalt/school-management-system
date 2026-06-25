from django.urls import path

from students.note_views import note_add, note_delete, note_edit
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
	path("<int:student_pk>/notes/add/",   note_add,    name="note_add"),
	path("notes/<int:pk>/edit/",          note_edit,   name="note_edit"),
	path("notes/<int:pk>/delete/",        note_delete, name="note_delete"),	
]   