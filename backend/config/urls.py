from django.contrib import admin
from django.urls import include, path

from marketplace.views import LoginView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/login/", LoginView.as_view(), name="api-token-auth"),
    path("api/", include("marketplace.urls")),
]
