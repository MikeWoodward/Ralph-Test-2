from django.urls import path, include

urlpatterns = [
    path('', include('subway.urls')),
]
