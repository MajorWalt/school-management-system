from django.urls import path
from . import views

app_name = "grades"

urlpatterns = [
	# Grade entry
	path("",                                        views.grade_section_select,     name="section_select"),
	path("section/<int:section_pk>/",               views.grade_section_overview,   name="section_overview"),
	path("enrolment/<int:enrolment_pk>/",           views.grade_enrolment_detail,   name="enrolment_detail"),
	path("entry/<int:pk>/delete/",                  views.grade_entry_delete,       name="entry_delete"),

	# Visibility
	path("visibility/",                             views.visibility_overview,      name="visibility"),
	path("visibility/school/",                      views.visibility_set_school,    name="visibility_school"),
	path("visibility/student/<int:student_pk>/",    views.visibility_set_student,   name="visibility_student"),

	# Report cards
	path("report-cards/",                           views.report_card_list,         name="report_card_list"),
	path("report-cards/generate/<int:section_pk>/", views.report_card_generate,     name="report_card_generate"),
	path("report-cards/<int:pk>/",                  views.report_card_detail,       name="report_card_detail"),
	path("report-cards/<int:pk>/publish/",          views.report_card_publish,      name="report_card_publish"),
]