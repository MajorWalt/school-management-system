from django.urls import path
from . import views

app_name = "reports"

urlpatterns = [
    path("", views.reports_home, name="home"),
    path("roster/", views.student_roster, name="student_roster"),
    path("staff/", views.staff_list_report, name="staff_list"),
    path("class/", views.class_list, name="class_list"),
    path("courses/", views.course_list_report, name="course_list"),
    path("attendance/", views.attendance_summary, name="attendance_summary"),
    path("conduct/", views.merit_demerit_report, name="merit_demerit"),
    path("grades/", views.grade_reports_home, name="grade_reports_home"),
    path("grades/by-course/", views.grade_by_course, name="grade_by_course"),
    path("grades/by-student/", views.grade_by_student, name="grade_by_student"),
    path("grades/gradebook/", views.teacher_gradebook, name="teacher_gradebook"),
    path("grades/overview/", views.grade_overview, name="grade_overview"),
]
