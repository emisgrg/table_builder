from .models import DynamicModel


from django.db import connections, models
from .serializers import TableCreateSerializer, TableUpdateSerializer, create_dynamic_serializer

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class DynamicModelMetaclass(models.base.ModelBase):
    def __new__(cls, name, bases, attrs):
        attrs["__module__"] = __name__
        return super().__new__(cls, name, bases, attrs)


def get_field_by_type(field_type):
    if field_type == "string":
        return models.CharField(max_length=255)
    elif field_type == "number":
        return models.IntegerField()
    elif field_type == "boolean":
        return models.BooleanField()
    else:
        raise ValueError(f"Unsupported field type: {field_type}")


def combine_columns(existing_columns, new_columns):
    combined_dict = dict(existing_columns)
    for key, value in new_columns.items():
        if key in combined_dict:
            combined_dict[key] = new_columns[key]
        else:
            combined_dict[key] = value
    return combined_dict


def generate_insert_query(table_name, data):
    columns = ", ".join(data.keys())
    values = ", ".join([f"'{value}'" if isinstance(value, str) else str(value) for value in data.values()])

    insert_query = f"INSERT INTO {table_name} ({columns}) VALUES ({values});"
    return insert_query


class TableCreateAPIView(APIView):
    def post(self, request):
        serializer = TableCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        field_types = serializer.validated_data["field_types"]
        field_titles = serializer.validated_data["field_titles"]
        model_name = serializer.validated_data["table_name"]

        # Generate fields dynamically based on the provided field types and titles
        model_fields = {}
        dynamic_fileds = {}
        for index, field_title in enumerate(field_titles):
            field_type = field_types[index]
            model_fields[field_title.lower().replace(" ", "_")] = get_field_by_type(field_type)
            dynamic_fileds[field_title.lower().replace(" ", "_")] = field_type

        # Create the dynamic model class using the custom metaclass
        model_class = DynamicModelMetaclass(model_name, (models.Model,), model_fields)

        # Get the default database connection
        connection = connections["default"]

        schema_editor = connection.schema_editor()

        with connection.schema_editor() as schema_editor:
            try:
                schema_editor.create_model(model_class)
            except Exception as e:
                return Response({"error": str(e), "description": "problem with creating dynamic model"}, status=500)

        # Store the dynamically created model's app label and model name
        try:
            dynamic_model = DynamicModel(name=model_name, columns=dynamic_fileds)
            dynamic_model.save()
        except Exception as e:
            return Response({"error": str(e), "description": "problem with saving dynamic model context"}, status=500)

        return Response({"success": "Dynamic model created and applied"}, status=status.HTTP_201_CREATED)


class TableUpdateAPIView(APIView):
    def put(self, request, table_name):
        serializer = TableUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        field_types = serializer.validated_data["field_types"]
        field_titles = serializer.validated_data["field_titles"]

        connection = connections["default"]

        # Check if table exist
        table = DynamicModel.objects.filter(name=table_name).first()

        if not table:
            return Response(
                {"error": f"A table with the name '{table_name}' does not exist."}, status=status.HTTP_404_NOT_FOUND
            )

        # Generate fields dynamically based on the provided field types and titles
        new_colimns = {}
        for index, field_title in enumerate(field_titles):
            field_type = field_types[index]
            new_colimns[field_title.lower().replace(" ", "_")] = field_type

        all_columns = combine_columns(table.columns, new_colimns)

        model_fields = {}
        for column, type in all_columns.items():
            model_fields[column] = get_field_by_type(type)

        # Create the dynamic model class using the custom metaclass
        model_class = DynamicModelMetaclass(table_name, (models.Model,), model_fields)

        # Get the default database connection
        connection = connections["default"]

        schema_editor = connection.schema_editor()

        # Delete existing table
        with connection.schema_editor() as schema_editor:
            schema_editor.execute(f"DROP TABLE table_builder_app_{table_name};")
            schema_editor.create_model(model_class)

        table.columns = all_columns
        table.save()

        return Response({"success": "Dynamic model updated"})


class CreateRowAPIView(APIView):
    def post(self, request, table_name):

        # Check if table exist
        table = DynamicModel.objects.filter(name=table_name).first()

        if not table:
            return Response(
                {"error": f"A table with the name '{table_name}' does not exist."}, status=status.HTTP_404_NOT_FOUND
            )

        dynamic_serializer = create_dynamic_serializer(table.columns)
        serializer = dynamic_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        connection = connections["default"]

        # Get the default database connection
        connection = connections["default"]

        schema_editor = connection.schema_editor()

        # Insert in dynamic table
        with connection.schema_editor() as schema_editor:
            schema_editor.execute(generate_insert_query(f"table_builder_app_{table_name}", serializer.validated_data))

        return Response({"success": "Row inserted"})


class ListRowsAPIView(APIView):
    def get(self, request, table_name):

        # Check if table exist
        table = DynamicModel.objects.filter(name=table_name).first()

        if not table:
            return Response(
                {"error": f"A table with the name '{table_name}' does not exist."}, status=status.HTTP_404_NOT_FOUND
            )

        dynamic_serializer = create_dynamic_serializer(table.columns)

        connection = connections["default"]

        # Get the default database connection
        connection = connections["default"]

        # Get data from table
        with connection.cursor() as cursor:
            try:

                cursor.execute(f"SELECT * FROM table_builder_app_{table_name};")
                rows = cursor.fetchall()
                columns = [col[0] for col in cursor.description]

                data = []
                for row in rows:
                    data.append(dict(zip(columns, row)))

                serializer = dynamic_serializer(data=data, many=True)
                serializer.is_valid()
                return Response(serializer.data)
            except Exception as e:
                return Response({"error": str(e)}, status=500)
