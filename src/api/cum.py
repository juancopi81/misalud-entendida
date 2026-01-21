"""
CUM (Codigo Unico de Medicamentos) API client.

Colombian drug registry from datos.gov.co (SODA/Socrata API).
Dataset: https://www.datos.gov.co/Salud-y-Protecci-n-Social/C-digo-nico-de-Medicamentos/i7cb-raxc

API Response Fields (validated 2026-01-20):
------------------------------------------
- expediente: Record/file number
- producto: Product name (brand)
- titular: Registration holder company
- registrosanitario: INVIMA registry number (e.g., "INVIMA 2025M-0022013")
- fechaexpedicion: Issue date
- fechavencimiento: Expiration date (optional)
- estadoregistro: Registration status ("Vigente" = active)
- expedientecum: CUM file number (links to SISMED)
- consecutivocum: CUM consecutive number
- cantidadcum: Quantity per package
- descripcioncomercial: Commercial description (packaging details)
- estadocum: CUM status ("Activo"/"Inactivo")
- muestramedica: Medical sample ("No"/"Si")
- unidad: Unit ("U")
- atc: ATC code (WHO drug classification)
- descripcionatc: ATC description
- viaadministracion: Administration route ("ORAL", "SUBCUTANEA", etc.)
- concentracion: Concentration code
- principioactivo: Active ingredient (uppercase, e.g., "METFORMINA")
- unidadmedida: Unit of measure ("mg", "ml", etc.)
- cantidad: Amount/quantity of active ingredient
- unidadreferencia: Reference unit ("TABLETA", "ML", etc.)
- formafarmaceutica: Pharmaceutical form ("TABLETA", "SOLUCION INYECTABLE", etc.)
- nombrerol: Company/role name
- tiporol: Role type ("FABRICANTE", "IMPORTADOR")
- modalidad: Modality ("FABRICAR Y VENDER", "IMPORTAR Y VENDER")

Rate Limits:
- No authentication required for basic queries
- App token recommended for higher rate limits (free registration)
- Default limit: 1000 records per request

Data Freshness:
- Dataset is updated periodically by INVIMA
- Contains ~35,000+ products
"""

from typing import Optional
import requests

from src.models import CUMRecord

BASE_URL = "https://www.datos.gov.co/resource/i7cb-raxc.json"
DEFAULT_LIMIT = 50


def search_by_active_ingredient(
    ingredient: str,
    limit: int = DEFAULT_LIMIT,
    only_active: bool = True,
) -> list[CUMRecord]:
    """
    Search CUM database by active ingredient (principioactivo).

    Args:
        ingredient: Active ingredient name (case-insensitive, will be uppercased)
        limit: Maximum number of results to return
        only_active: If True, only return products with estadoregistro="Vigente"

    Returns:
        List of CUMRecord objects matching the search

    Example:
        >>> results = search_by_active_ingredient("metformina")
        >>> for r in results:
        ...     print(f"{r.producto} - {r.concentracion_valor}{r.unidadmedida}")
    """
    params = {
        "principioactivo": ingredient.upper(),
        "$limit": limit,
    }
    if only_active:
        params["estadoregistro"] = "Vigente"

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    records = []
    for item in response.json():
        records.append(
            CUMRecord(
                expedientecum=item.get("expedientecum", ""),
                producto=item.get("producto", ""),
                principioactivo=item.get("principioactivo", ""),
                concentracion_valor=item.get("cantidad", ""),
                unidadmedida=item.get("unidadmedida", ""),
                formafarmaceutica=item.get("formafarmaceutica", ""),
                titular=item.get("titular", ""),
                registrosanitario=item.get("registrosanitario", ""),
                estadoregistro=item.get("estadoregistro", ""),
                cantidadcum=item.get("cantidadcum", ""),
                descripcioncomercial=item.get("descripcioncomercial", ""),
            )
        )
    return records


def search_by_product_name(
    product_name: str,
    limit: int = DEFAULT_LIMIT,
) -> list[CUMRecord]:
    """
    Search CUM database by product/brand name.

    Uses full-text search ($q parameter) which is more flexible than exact match.

    Args:
        product_name: Product or brand name to search
        limit: Maximum number of results to return

    Returns:
        List of CUMRecord objects matching the search

    Example:
        >>> results = search_by_product_name("glucophage")
        >>> for r in results:
        ...     print(f"{r.producto} - {r.principioactivo}")
    """
    params = {
        "$q": product_name,
        "$limit": limit,
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    records = []
    for item in response.json():
        records.append(
            CUMRecord(
                expedientecum=item.get("expedientecum", ""),
                producto=item.get("producto", ""),
                principioactivo=item.get("principioactivo", ""),
                concentracion_valor=item.get("cantidad", ""),
                unidadmedida=item.get("unidadmedida", ""),
                formafarmaceutica=item.get("formafarmaceutica", ""),
                titular=item.get("titular", ""),
                registrosanitario=item.get("registrosanitario", ""),
                estadoregistro=item.get("estadoregistro", ""),
                cantidadcum=item.get("cantidadcum", ""),
                descripcioncomercial=item.get("descripcioncomercial", ""),
            )
        )
    return records


def find_generics(ingredient: str, concentration: Optional[str] = None) -> list[CUMRecord]:
    """
    Find generic alternatives for a given active ingredient.

    Generics are identified by having "GENERICO" in descripcioncomercial
    or by having a different titular than the original brand.

    Args:
        ingredient: Active ingredient name
        concentration: Optional concentration to filter (e.g., "850")

    Returns:
        List of CUMRecord objects that could be generic alternatives
    """
    results = search_by_active_ingredient(ingredient, limit=100)

    if concentration:
        results = [r for r in results if r.concentracion_valor == concentration]

    # Sort by whether "GENERICO" appears in description (generics first)
    results.sort(
        key=lambda r: (
            "GENERICO" not in r.descripcioncomercial.upper(),
            r.producto,
        )
    )

    return results


def main():
    """
    Smoke test for CUM API.

    Run with:
        uv run python -m src.api.cum

    Or:
        uv run python src/api/cum.py
    """
    print("=" * 60)
    print("CUM API Smoke Test")
    print("=" * 60)

    # Test 1: Search by active ingredient
    print("\n[Test 1] Searching for METFORMINA...")
    results = search_by_active_ingredient("METFORMINA", limit=5)
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(f"  - {r.producto}")
        print(f"    {r.concentracion_valor}{r.unidadmedida} | {r.formafarmaceutica}")
        print(f"    Expediente: {r.expedientecum}")

    # Test 2: Search by product name
    print("\n[Test 2] Searching for 'losartan'...")
    results = search_by_product_name("losartan", limit=3)
    print(f"Found {len(results)} results")
    for r in results[:2]:
        print(f"  - {r.producto} ({r.principioactivo})")

    # Test 3: Find generics
    print("\n[Test 3] Finding generics for ACETAMINOFEN...")
    generics = find_generics("ACETAMINOFEN", concentration="500")
    print(f"Found {len(generics)} options for 500mg")
    for r in generics[:3]:
        is_generic = "GENERICO" in r.descripcioncomercial.upper()
        print(f"  - {r.producto} {'[GENERICO]' if is_generic else ''}")

    print("\n" + "=" * 60)
    print("Smoke test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
