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
            # Try to extract JSON from response (model may include extra text)
            json_start = json_str.find("{")
            json_end = json_str.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str_clean = json_str[json_start:json_end]
                data = json.loads(json_str_clean)

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
                return cls(medicamentos=medicamentos, raw_response=json_str, parse_success=True)
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
            json_start = json_str.find("{")
            json_end = json_str.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str_clean = json_str[json_start:json_end]
                data = json.loads(json_str_clean)

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
