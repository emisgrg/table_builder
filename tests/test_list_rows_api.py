from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from unittest.mock import patch, MagicMock

from table_builder_app.models import DynamicModel
from table_builder_app.views import CreateRowAPIView
from django.db import connection


class ListRowsAPIViewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.url = reverse("rows-list", args=["test_table"])

    def test_successful_list_rows(self):
        create_url = reverse("table-create")
        table_name = "test_table"
        field_types = ["string", "number", "boolean"]
        field_titles = ["Name", "Age", "Active"]
        existing_columns = {
            "name": "string",
            "age": "number",
            "active": "boolean",
        }

        data = {
            "table_name": table_name,
            "field_types": field_types,
            "field_titles": field_titles,
        }

        response = self.client.post(create_url, data, format="json")

        created_table = DynamicModel.objects.get(name=table_name)
        self.assertEqual(created_table.columns, existing_columns)

        url = reverse("row-create", args=["test_table"])

        data = {"name": "John", "age": 30, "active": True}
        response = self.client.post(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        assert response.data["success"] == "Row inserted"

        url = reverse("rows-list", args=[table_name])

        response = self.client.get(self.url, format="json")
        assert response.status_code == status.HTTP_200_OK

        assert len(response.data) == 1

    def test_list_rows_table_not_found(self):
        table_name = "test_table"
        data = {"name": "John", "age": 30, "active": True}
        response = self.client.get(self.url, data, format="json")

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], f"A table with the name '{table_name}' does not exist.")
