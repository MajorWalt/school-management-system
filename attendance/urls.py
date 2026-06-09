from django.urls import path
from . import views

app_name = "attendance"

urlpatterns = [
	path("",                                        views.attendance_home,    name="home"),
	path("<str:date>/",                             views.homeroom_select,    name="homeroom_select"),
	path("<str:date>/<int:homeroom_pk>/",           views.attendance_mark,    name="mark"),
	path("report/<int:homeroom_pk>/",               views.attendance_report,  name="report"),
]