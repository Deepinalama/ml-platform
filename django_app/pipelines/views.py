import requests
from django.conf import settings
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response

from .models import ModelVersion, PipelineRun, Prediction
from .serializers import (
    ModelVersionSerializer,
    PipelineRunSerializer,
    PredictionSerializer,
)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def model_versions(request):
    versions = ModelVersion.objects.all().order_by("-trained_at")
    serializer = ModelVersionSerializer(versions, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def predictions(request):
    preds = Prediction.objects.all().order_by("-predicted_at")[:50]
    serializer = PredictionSerializer(preds, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def pipeline_runs(request):
    runs = PipelineRun.objects.all().order_by("-started_at")
    serializer = PipelineRunSerializer(runs, many=True)
    return Response(serializer.data)


@api_view(["POST"])
@permission_classes([IsAdminUser])
def trigger_retrain(request):
    try:
        response = requests.post(
            f"{settings.AIRFLOW_API_URL}/dags/churn_prediction_pipeline/dagRuns",
            json={"conf": {}},
            auth=(settings.AIRFLOW_ADMIN_USER, settings.AIRFLOW_ADMIN_PASSWORD),
            timeout=10,
        )
        if response.status_code in [200, 201]:
            return Response(
                {"message": "DAG triggered successfully"}, status=status.HTTP_200_OK
            )
        return Response(
            {"error": "Failed to trigger DAG"}, status=status.HTTP_502_BAD_GATEWAY
        )
    except requests.exceptions.RequestException as e:
        return Response({"error": str(e)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
