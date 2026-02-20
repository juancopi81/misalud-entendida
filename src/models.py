"""
Data models for MiSalud Entendida.

All dataclasses used across the application are defined here:
- Extraction models: MedGemma output parsing (prescriptions, lab results)
- API models: CUM and SISMED record structures

Data flow:
1. MedGemma extracts JSON from medical document images
2. PrescriptionExtraction/LabResultExtraction parse the JSON
3. CUM API validates drugs and finds generics
4. SISMED API looks up price data
"""

from dataclasses import dataclass, field
import json
from typing import Any, Literal


# --- MedGemma Extraction Models ---


@dataclass
class MedicationItem:
    """Single medication extracted from a prescription."""

    nombre_medicamento: str = ""
    dosis: str = ""
    frecuencia: str = ""
    duracion: str = ""
    instrucciones: str = ""


@dataclass
class PrescriptionExtraction:
    """Extracted data from a prescription image."""

    medicamentos: list[MedicationItem] = field(default_factory=list)
    raw_response: str = ""
    parse_success: bool = False

    @classmethod
    def from_json(cls, json_str: str) -> "PrescriptionExtraction":
        """Parse JSON response into PrescriptionExtraction."""
        try:
            # Try direct parse first, then fallback to slicing
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                json_start = json_str.find("{")
                json_end = json_str.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str_clean = json_str[json_start:json_end]
                    data = json.loads(json_str_clean)
                else:
                    data = {}

            if "medicamentos" not in data:
                return cls(raw_response=json_str, parse_success=False)

            medicamentos = []
            for med in data.get("medicamentos", []):
                medicamentos.append(
                    MedicationItem(
                        nombre_medicamento=med.get("nombre_medicamento", ""),
                        dosis=med.get("dosis", ""),
                        frecuencia=med.get("frecuencia", ""),
                        duracion=med.get("duracion", ""),
                        instrucciones=med.get("instrucciones", ""),
                    )
                )
            return cls(
                medicamentos=medicamentos, raw_response=json_str, parse_success=True
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        return cls(raw_response=json_str, parse_success=False)


@dataclass
class LabResultItem:
    """Single lab result value."""

    nombre_prueba: str = ""
    valor: str = ""
    unidad: str = ""
    rango_referencia: str = ""
    estado: str = ""  # "normal", "alto", "bajo"


@dataclass
class LabResultExtraction:
    """Extracted data from a lab result image."""

    resultados: list[LabResultItem] = field(default_factory=list)
    raw_response: str = ""
    parse_success: bool = False

    @classmethod
    def from_json(cls, json_str: str) -> "LabResultExtraction":
        """Parse JSON response into LabResultExtraction."""
        try:
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                json_start = json_str.find("{")
                json_end = json_str.rfind("}") + 1
                if json_start >= 0 and json_end > json_start:
                    json_str_clean = json_str[json_start:json_end]
                    data = json.loads(json_str_clean)
                else:
                    data = {}

            if "resultados" not in data:
                return cls(raw_response=json_str, parse_success=False)

            resultados = []
            for res in data.get("resultados", []):
                resultados.append(
                    LabResultItem(
                        nombre_prueba=res.get("nombre_prueba", ""),
                        valor=res.get("valor", ""),
                        unidad=res.get("unidad", ""),
                        rango_referencia=res.get("rango_referencia", ""),
                        estado=res.get("estado", ""),
                    )
                )
            return cls(resultados=resultados, raw_response=json_str, parse_success=True)
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        return cls(raw_response=json_str, parse_success=False)


# --- CUM API Models ---


@dataclass
class CUMRecord:
    """Simplified CUM drug record.

    CUM (Codigo Unico de Medicamentos) is the Colombian drug registry.
    Data source: datos.gov.co/resource/i7cb-raxc.json
    """

    expedientecum: str
    producto: str  # Brand name
    principioactivo: str  # Active ingredient
    concentracion_valor: str  # e.g., "850"
    unidadmedida: str  # e.g., "mg"
    formafarmaceutica: str  # e.g., "TABLETA"
    titular: str  # Manufacturer/holder
    registrosanitario: str  # INVIMA number
    estadoregistro: str  # "Vigente" = active
    cantidadcum: str  # Quantity per package
    descripcioncomercial: str  # Package description


# --- SISMED API Models ---


@dataclass
class PriceRecord:
    """SISMED price record for a medication.

    SISMED (Sistema de Informacion de Precios de Medicamentos) contains
    Colombian drug price data.
    Data source: datos.gov.co/resource/3he6-m866.json

    Note: SISMED data is historical (last updated 2019). Use as reference only.
    """

    expedientecum: str
    descripcioncomercial: str
    formafarmaceutica: str
    atc: str
    descripcion_atc: str
    precio_minimo: float
    precio_maximo: float
    precio_promedio: float
    unidades: float
    fechacorte: str  # Report date
    tipo_reporte: str  # "VENTA" or "COMPRA"
    tipo_entidad: str  # "LABORATORIO", "MAYORISTA", etc.


# --- Unified Document Orchestration Models ---

DocumentKind = Literal["prescription", "lab", "unknown"]
EvidenceSource = Literal["text_pdf", "image", "pdf_no_text", "unsupported"]


@dataclass
class RouteDecision:
    """Result of routing a generic document to an internal processing flow."""

    kind: DocumentKind = "unknown"
    confidence: float = 0.0
    method: str = "heuristic"
    reasons: list[str] = field(default_factory=list)
    raw_response: str = ""


@dataclass
class DocumentChatContext:
    """Minimal grounded context used for follow-up Q&A."""

    document_kind: DocumentKind
    report_markdown: str
    extracted_text: str
    extracted_json: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    uncertainty_notes: list[str] = field(default_factory=list)
    route_confidence: float = 0.0
    evidence_source: EvidenceSource = "unsupported"

    def to_prompt_payload(self) -> str:
        """Serialize context to JSON for grounded prompt injection."""
        payload = {
            "document_kind": self.document_kind,
            "route_confidence": round(self.route_confidence, 3),
            "evidence_source": self.evidence_source,
            "warnings": self.warnings,
            "uncertainty_notes": self.uncertainty_notes,
            "extracted_json": self.extracted_json,
            "report_markdown": self.report_markdown,
            "extracted_text": self.extracted_text,
        }
        return json.dumps(payload, ensure_ascii=False)


@dataclass
class UnifiedDocumentResult:
    """Output of the unified document analysis flow."""

    file_path: str
    evidence_source: EvidenceSource
    evidence_quality: float
    route: RouteDecision
    report_markdown: str
    warnings: list[str] = field(default_factory=list)
    uncertainty_notes: list[str] = field(default_factory=list)
    extracted_text: str = ""
    parse_success: bool = False
    raw_verification_response: str = ""
    used_backend: str = ""
    prescription: PrescriptionExtraction | None = None
    lab: LabResultExtraction | None = None
    prescription_output: str = ""
    lab_output: str = ""

    def to_chat_context(self) -> DocumentChatContext:
        """Build grounded chat context from the unified result."""
        extracted_json: dict[str, Any]
        if self.prescription is not None:
            extracted_json = {
                "medicamentos": [
                    {
                        "nombre_medicamento": m.nombre_medicamento,
                        "dosis": m.dosis,
                        "frecuencia": m.frecuencia,
                        "duracion": m.duracion,
                        "instrucciones": m.instrucciones,
                    }
                    for m in self.prescription.medicamentos
                ]
            }
        elif self.lab is not None:
            extracted_json = {
                "resultados": [
                    {
                        "nombre_prueba": r.nombre_prueba,
                        "valor": r.valor,
                        "unidad": r.unidad,
                        "rango_referencia": r.rango_referencia,
                        "estado": r.estado,
                    }
                    for r in self.lab.resultados
                ]
            }
        else:
            extracted_json = {}

        return DocumentChatContext(
            document_kind=self.route.kind,
            report_markdown=self.report_markdown,
            extracted_text=self.extracted_text,
            extracted_json=extracted_json,
            warnings=list(self.warnings),
            uncertainty_notes=list(self.uncertainty_notes),
            route_confidence=self.route.confidence,
            evidence_source=self.evidence_source,
        )
