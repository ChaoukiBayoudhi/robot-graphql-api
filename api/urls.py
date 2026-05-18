from django.urls import path
from strawberry.django.views import GraphQLView

from robot_graphql_api.schema import schema

from . import views

urlpatterns = [
    path("", views.api_root, name="api-root"),
    path("health/", views.health, name="api-health"),
    path("graphql/", GraphQLView.as_view(schema=schema, graphql_ide="graphiql"), name="graphql"),
]
