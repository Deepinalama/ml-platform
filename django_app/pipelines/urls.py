from django.urls import path
from . import views

urlpatterns = [
    path("models/", views.model_versions, name="model_versions"),
    path("predictions/", views.predictions, name="predictions"),
    path("pipeline-runs/", views.pipeline_runs, name="pipeline_runs"),
    path("trigger-retrain/", views.trigger_retrain, name="trigger_retrain"),
]