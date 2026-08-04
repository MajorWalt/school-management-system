from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.csrf import requires_csrf_token
from django.shortcuts import render


# Custom 404 Error Handler
@requires_csrf_token
def custom_404(request, exception=None):
    
    return render(request, '404.html', {'status_code': 404}, status=404)
 


# Custom 500 Error Handler
@requires_csrf_token
def custom_500(request):
   
    return render(request, '500.html', status=500)



# URL Patterns
urlpatterns = [
    path("admin/", admin.site.urls),
    path("__reload__/", include("django_browser_reload.urls")),
    path("accounts/", include("accounts.urls")),
    path("core/", include("core.urls")),
    path("staff/", include("staff.urls")),
    path("students/", include("students.urls")),
    path("scheduling/", include("scheduling.urls")),
    path("attendance/", include("attendance.urls")),
    path("grades/", include("grades.urls")),
    path("merits/", include("merits.urls")),
    path("backups/", include("backups.urls")),
    path("reports/", include("reports.urls")),
    path("", include("portals.urls")),
]

if settings.DEBUG:
    import debug_toolbar
    urlpatterns += [
        path("__debug__/", include(debug_toolbar.urls)),
    ]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
pass

# Custom error handlers
handler404 = custom_404
handler500 = custom_500