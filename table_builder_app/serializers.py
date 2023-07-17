from rest_framework import serializers
from django.db import connection
from .models import DynamicModel


class TableUpdateSerializer(serializers.Serializer):
    field_types = serializers.ListField(child=serializers.CharField())
    field_titles = serializers.ListField(child=serializers.CharField())

    def validate_field_types(self, value):
        for field_type in value:
            if field_type not in ["string", "number", "boolean"]:
                raise serializers.ValidationError(
                    "Invalid field type. Field types must be 'string', 'number', or 'boolean'."
                )
        return value

    def validate(self, attrs):
        field_types = attrs.get("field_types")
        field_titles = attrs.get("field_titles")

        if field_types and field_titles:
            if len(field_types) != len(field_titles):
                raise serializers.ValidationError("field_types and field_titles must have the same length")

        return attrs


class TableCreateSerializer(TableUpdateSerializer):
    table_name = serializers.CharField()

    def validate_table_name(self, value):
        # Check if a table with the given name already exists
        table_exists = DynamicModel.objects.filter(name=value).first()
        if table_exists:
            raise serializers.ValidationError(f"A table with the name '{value}' already exists.")
        return value


def create_dynamic_serializer(columns):
    fields = {}
    for column, column_type in columns.items():
        field_name = column.lower().replace(" ", "_")
        if column_type == "string":
            field = serializers.CharField()
        elif column_type == "number":
            field = serializers.FloatField()
        elif column_type == "boolean":
            field = serializers.BooleanField()
        else:
            field = serializers.CharField()  # Customize based on your specific column types

        fields[field_name] = field

    DynamicSerializer = type("DynamicSerializer", (serializers.Serializer,), fields)
    return DynamicSerializer
