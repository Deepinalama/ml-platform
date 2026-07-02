from django.db import models


class ModelVersion(models.Model):
    version_name = models.CharField(max_length=100)
    accuracy = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    precision_score = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    recall_score = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    file_path = models.CharField(max_length=255)
    is_active = models.BooleanField(default=False)
    trained_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'model_versions'


class Prediction(models.Model):
    customer_id = models.CharField(max_length=50, null=True)
    prediction = models.BooleanField(null=True)
    probability = models.DecimalField(max_digits=5, decimal_places=4, null=True)
    model_version = models.ForeignKey(ModelVersion, on_delete=models.SET_NULL, null=True)
    requested_by = models.CharField(max_length=100, null=True)
    predicted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = 'predictions'


class PipelineRun(models.Model):
    dag_run_id = models.CharField(max_length=100, null=True)
    status = models.CharField(max_length=20, null=True)
    rows_processed = models.IntegerField(null=True)
    started_at = models.DateTimeField(null=True)
    finished_at = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = 'pipeline_runs'
