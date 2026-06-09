from django.urls import path
from . import views

app_name = "portals"

urlpatterns = [
	path("",            views.dashboard,         name="dashboard"),
	path("dashboard/",      views.admin_dashboard,   name="admin_dashboard"),
	path("teacher/",    views.teacher_dashboard, name="teacher_dashboard"),
	path("student/",    views.student_dashboard, name="student_dashboard"),
]