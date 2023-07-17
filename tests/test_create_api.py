from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from unittest.mock import patch
from table_builder_app.models import DynamicModel


class TableCreateAPIViewTests(APITestCase):
    def setUp(self):
        self.url = reverse("table-create")

    def test_successful_post_request(self):
        data = {
            "field_types": ["string", "number", "boolean"],
            "field_titles": ["Name", "Age", "Active"],
            "table_name": "test_table",
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Assert the dynamic model and dynamic model instance are created
        self.assertTrue(DynamicModel.objects.filter(name="test_table").exists())

        # Assert the response data contains the expected success message
        self.assertEqual(response.data, {"success": "Dynamic model created and applied"})

    def test_missing_or_invalid_fields(self):
        # Missing field_types
        data = {
            "field_titles": ["Name", "Age", "Active"],
            "table_name": "test_table",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Invalid field_types
        data = {
            "field_types": ["string", "number", "invalid_type"],
            "field_titles": ["Name", "Age", "Active"],
            "table_name": "test_table",
        }
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_duplicate_table_name(self):
        # Create a dynamic model instance with the same table name
        DynamicModel.objects.create(name="existing_table", columns={})

        data = {
            "field_types": ["string", "number", "boolean"],
            "field_titles": ["Name", "Age", "Active"],
            "table_name": "existing_table",
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("table_builder_app.views.DynamicModel.save")
    def test_database_error_during_model_context_creation(self, mock_save):
        mock_save.side_effect = Exception("Database error")

        data = {
            "field_types": ["string", "number", "boolean"],
            "field_titles": ["Name", "Age", "Active"],
            "table_name": "test_table",
        }

        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(response.json()["description"], "problem with saving dynamic model context")
