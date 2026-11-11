from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render


def home(request: HttpRequest):
    """Placeholder landing page until M1 Identity & Sign-in lands."""
    return render(request, "core/home.html")


def healthz(request: HttpRequest) -> JsonResponse:
    """Liveness and readiness probe.

    Checks the database, because an application process that cannot reach
    PostgreSQL is not ready to serve. Used by the deploy script to decide
    whether a new release came up before it takes traffic.
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    # Deliberately broad: any failure reaching the database means "not ready",
    # and the probe must answer rather than raise.
    except Exception:
        return JsonResponse({"status": "unhealthy", "database": "unreachable"}, status=503)

    return JsonResponse({"status": "ok", "database": "ok"})
