"""Integration-style tests for app handlers and backend fallback behavior."""

import pytest

import src.app as app_module
from src.models import MedicationItem, PrescriptionExtraction
from src.pipelines.prescription_pipeline import PrescriptionPipelineResult


@pytest.fixture(autouse=True)
def _reset_app_backend_cache():
    app_module._backend_cache.clear()


def test_analyze_prescription_falls_back_to_transformers(monkeypatch):
    class ModalFailBackend:
        def __init__(self):
            self.calls = 0

        def extract_prescription(self, _image_path):
            self.calls += 1
            raise RuntimeError("modal backend unavailable")

    class TransformersSuccessBackend:
        def __init__(self):
            self.calls = 0

        def extract_prescription(self, _image_path):
            self.calls += 1
            return PrescriptionExtraction(
                medicamentos=[MedicationItem(nombre_medicamento="METFORMINA")],
                parse_success=True,
            )

    modal_backend = ModalFailBackend()
    transformers_backend = TransformersSuccessBackend()

    monkeypatch.setenv("INFERENCE_BACKEND", "auto")
    monkeypatch.setattr(
        app_module,
        "get_backend",
        lambda backend_name: {
            "modal": modal_backend,
            "transformers": transformers_backend,
        }[backend_name],
    )
    monkeypatch.setattr(
        app_module,
        "build_prescription_output",
        lambda *_args, **_kwargs: PrescriptionPipelineResult(
            medications_markdown="meds",
            generics_markdown="generics",
            prices_markdown="prices",
            explanations_markdown="explanations",
        ),
    )

    result = app_module.analyze_prescription("/tmp/fake-prescription.jpg")

    assert result == ("meds", "generics", "prices", "explanations")
    assert modal_backend.calls == 1
    assert transformers_backend.calls == 1


def test_analyze_lab_results_returns_stable_error_when_all_backends_fail(monkeypatch):
    class AlwaysFailBackend:
        def __init__(self):
            self.calls = 0

        def extract_lab_results(self, _image_path):
            self.calls += 1
            raise RuntimeError("backend unavailable")

    modal_backend = AlwaysFailBackend()
    transformers_backend = AlwaysFailBackend()

    monkeypatch.setenv("INFERENCE_BACKEND", "auto")
    monkeypatch.setattr(
        app_module,
        "get_backend",
        lambda backend_name: {
            "modal": modal_backend,
            "transformers": transformers_backend,
        }[backend_name],
    )
    monkeypatch.setattr(
        app_module,
        "build_lab_results_output",
        lambda _result: "should not be returned",
    )

    output = app_module.analyze_lab_results("/tmp/fake-lab.jpg")

    assert output.startswith("Error al analizar los resultados:")
    assert "No se logró extraer información con los backends configurados" in output
    assert modal_backend.calls == 1
    assert transformers_backend.calls == 1
