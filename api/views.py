from django.http import JsonResponse


def api_root(request):
    return JsonResponse(
        {
            "name": "Robot GraphQL API",
            "endpoints": {
                "health": request.build_absolute_uri("health/"),
                "graphql": request.build_absolute_uri("graphql/"),
                "admin": request.build_absolute_uri("/admin/"),
            },
        }
    )


def health(request):
    return JsonResponse({"status": "ok"})
