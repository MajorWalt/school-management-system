from django.urls import path

from . import views

app_name = "ai"

urlpatterns = [
    path("settings/", views.settings_view, name="settings"),
    path("test/", views.test_view, name="test"),
    path("comments/section/<int:section_pk>/", views.comment_review, name="comment_review"),
    path("comments/section/<int:section_pk>/generate/", views.comment_generate, name="comment_generate"),
    path("comments/section/<int:section_pk>/progress/", views.comment_progress, name="comment_progress"),
    path("comments/section/<int:section_pk>/action/", views.comment_review_action, name="comment_review_action"),
    path("ask/history/", views.ask_history, name="ask_history"),
    path("ask/send/", views.ask_send, name="ask_send"),
    path("ask/reset/", views.ask_reset, name="ask_reset"),
]