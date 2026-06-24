from django.urls import path

from grades.report_views import generate_report_cards
from . import views

app_name = "grades"

urlpatterns = [
	path("",                                        views.grades_home,             name="home"),
	path("section/<int:section_pk>/",               views.section_grade_table,     name="section_table"),
	path("section/<int:section_pk>/save/",          views.grades_save,             name="grades_save"),
	path("section/<int:section_pk>/evaluation/",    views.evaluation_create,       name="evaluation_create"),
	path("section/<int:section_pk>/bulk/",          views.bulk_grade_upload,       name="bulk_upload"),
	path("evaluation/<int:pk>/edit/",               views.evaluation_edit,         name="evaluation_edit"),
	path("evaluation/<int:pk>/delete/",             views.evaluation_delete,       name="evaluation_delete"),
	path("windows/",                                views.grade_window_manage,     name="windows"),
	path("visibility/",                             views.visibility_overview,     name="visibility"),
	path("visibility/school/",                      views.visibility_set_school,   name="visibility_school"),
	path("visibility/student/<int:student_pk>/",    views.visibility_set_student,  name="visibility_student"),
	path("report-cards/",                           views.report_card_list,        name="report_card_list"),
	path("report-cards/<int:pk>/",                  views.report_card_detail,      name="report_card_detail"),
	path("report-cards/<int:pk>/publish/",          views.report_card_publish,     name="report_card_publish"),
    path("report-cards/generate/", 					generate_report_cards, 		   name="report_card_generate_pdf"),
]