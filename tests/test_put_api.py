from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

from table_builder_app.models import DynamicModel
from table_builder_app.views import TableUpdateAPIView
from django.db import connection


class TableUpdateAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("table-update", args=["test_table"])

    def test_successful_table_update(self):
        create_url = reverse("table-create")
        table_name = "test_table"
        field_types = ["string", "number", "boolean"]
        field_titles = ["Name", "Age", "Active"]
        existing_columns = {
            "name": "string",
            "age": "number",
            "active": "boolean",
        }
        new_columns = {
            "email": "string",
            "address": "string",
        }
        expected_columns = {
            "name": "string",
            "age": "number",
            "active": "boolean",
            "email": "string",
            "address": "string",
        }

        data = {
            "table_name": table_name,
            "field_types": field_types,
            "field_titles": field_titles,
        }

        update_data = {
            "field_types": ["string", "string"],
            "field_titles": ["email", "address"],
        }

        response = self.client.post(create_url, data, format="json")

        created_table = DynamicModel.objects.get(name=table_name)
        self.assertEqual(created_table.columns, existing_columns)

        response = self.client.put(self.url, update_data, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Check if the table columns have been updated
        updated_table = DynamicModel.objects.get(name=table_name)
        self.assertEqual(updated_table.columns, expected_columns)

    def test_table_update_table_not_found(self):
        table_name = "non_existent_table"
        field_types = ["string", "number", "boolean"]
        field_titles = ["Name", "Age", "Active"]

        data = {
            "field_types": field_types,
            "field_titles": field_titles,
        }

        response = self.client.put(reverse("table-update", args=[table_name]), data)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], f"A table with the name '{table_name}' does not exist.")

    def test_table_update_invalid_fields(self):
        table_name = "test_table"
        field_types = ["string", "number", "invalid_type"]  # Invalid field type
        field_titles = ["Name", "Age", "Active"]

        data = {
            "field_types": field_types,
            "field_titles": field_titles,
        }

        response = self.client.put(reverse("table-update", args=[table_name]), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_table_update_wrong_number_of_titles(self):
        create_url = reverse("table-create")
        table_name = "test_table"
        field_types = ["string", "number", "boolean"]
        field_titles = ["Name", "Age", "Active"]

        data = {
            "table_name": table_name,
            "field_types": field_types,
            "field_titles": field_titles,
        }

        response = self.client.post(create_url, data, format="json")

        field_types = ["string", "number", "boolean"]
        field_titles = ["Name", "Age"]  # Missing title

        data = {
            "field_types": field_types,
            "field_titles": field_titles,
        }

        response = self.client.put(reverse("table-update", args=[table_name]), data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.json(), {"non_field_errors": ["field_types and field_titles must have the same length"]}
        )
