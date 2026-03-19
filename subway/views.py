from django.http import JsonResponse


def index(request):
    """Placeholder root view — will redirect to trains-alerts in a later story."""
    return JsonResponse({"status": "ok", "app": "mbta-subway"})
