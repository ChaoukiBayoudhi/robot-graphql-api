import json

from django.test import Client, TestCase
from django.utils import timezone

from api.models import Robot


class ApiUrlTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_health_endpoint(self):
        response = self.client.get("/api/health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_api_root_lists_endpoints(self):
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["name"], "Robot GraphQL API")
        self.assertIn("graphql", payload["endpoints"])

    def test_graphql_query_robots(self):
        Robot.objects.create(
            name="Test Bot",
            serial_number="TB-001",
            battery_level=50,
            max_speed=1.5,
            is_active=False,
        )
        response = self.client.post(
            "/api/graphql/",
            data=json.dumps({"query": "{ robots { name serialNumber } }"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn("errors", payload)
        self.assertEqual(payload["data"]["robots"][0]["name"], "Test Bot")

    def test_graphql_mutation_create_robot(self):
        response = self.client.post(
            "/api/graphql/",
            data=json.dumps(
                {
                    "query": """
                        mutation {
                          createRobot(
                            input: {
                              name: "Mutated Bot"
                              serialNumber: "MB-001"
                              batteryLevel: 80
                              maxSpeed: 2.0
                              isActive: true
                            }
                          ) {
                            id
                            name
                          }
                        }
                    """
                }
            ),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertNotIn("errors", payload)
        self.assertEqual(payload["data"]["createRobot"]["name"], "Mutated Bot")
        self.assertTrue(Robot.objects.filter(serial_number="MB-001").exists())
