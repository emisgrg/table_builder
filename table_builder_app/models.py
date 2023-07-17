from django.db import models


class DynamicModel(models.Model):
    name = models.CharField(max_length=255)
    columns = models.JSONField()
