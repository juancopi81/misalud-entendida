"""
SISMED (Sistema de Informacion de Precios de Medicamentos) API client.

Colombian drug price reporting from datos.gov.co (SODA/Socrata API).
Dataset: https://www.datos.gov.co/Salud-y-Protecci-n-Social/SISMED/3he6-m866

API Response Fields (validated 2026-01-20):
-------------------------------------------
- fechacorte: Cutoff/report date (format: "YYYY/MM/DD")
- rolactordesc: Actor role description ("ELABORA O IMPORTA EL MEDICAMENTO")
- tiporeportepreciodesc: Price report type ("VENTA", "COMPRA")
- transaccionsismeddesc: Transaction type ("TRANSACCION PRIMARIA INSTITUCIONAL")
- codigoium: IUM code
- nombreium: IUM name
- expedientecum: CUM file number (links to CUM database!)
- consecutivo: Consecutive number
- descripcioncomercial: Commercial description (packaging)
- formafarmaceutica: Pharmaceutical form
- atc: ATC code
- descripcion_atc: ATC description (note: uses underscore)
- via_administracion: Administration route (note: uses underscore)
- tipoentidaddesc: Entity type ("LABORATORIO", "MAYORISTA", "IPS", "EPS")
- unidadfacturadesc: Billing unit description
- valorminimo: Minimum price reported (COP, as string with decimals)
- valormaximo: Maximum price reported (COP, as string with decimals)
- valorpromedio: Average price reported (COP, as string with decimals)
- unidades: Units sold
- valortotal: Total value

Data Freshness (IMPORTANT):
---------------------------
- Most recent data found: 2019/06/01
- Data appears to be historical and NOT regularly updated
- Use prices as "reference ranges" only, not current market prices
- Always show the data date to users

Rate Limits:
- No authentication required for basic queries
- Default limit: 1000 records per request
"""

from typing import Optional
import requests

from src.models import PriceRecord

BASE_URL = "https://www.datos.gov.co/resource/3he6-m866.json"
DEFAULT_LIMIT = 50


def get_price_by_expediente(
    expedientecum: str,
    limit: int = DEFAULT_LIMIT,
) -> list[PriceRecord]:
    """
    Get price records for a specific CUM expediente number.

    The expedientecum links CUM (drug registry) to SISMED (prices).

    Args:
        expedientecum: CUM file number to search
        limit: Maximum number of results

    Returns:
        List of PriceRecord objects for the medication

    Example:
        >>> prices = get_price_by_expediente("20097257")
        >>> for p in prices:
        ...     print(f"${p.precio_promedio:.0f} COP ({p.fechacorte})")
    """
    params = {
        "expedientecum": expedientecum,
        "$limit": limit,
        "$order": "fechacorte DESC",  # Most recent first
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    records = []
    for item in response.json():
        # Skip records with zero prices (no actual transactions)
        precio_promedio = float(item.get("valorpromedio", 0) or 0)
        if precio_promedio == 0:
            continue

        records.append(
            PriceRecord(
                expedientecum=item.get("expedientecum", ""),
                descripcioncomercial=item.get("descripcioncomercial", ""),
                formafarmaceutica=item.get("formafarmaceutica", ""),
                atc=item.get("atc", ""),
                descripcion_atc=item.get("descripcion_atc", ""),
                precio_minimo=float(item.get("valorminimo", 0) or 0),
                precio_maximo=float(item.get("valormaximo", 0) or 0),
                precio_promedio=precio_promedio,
                unidades=float(item.get("unidades", 0) or 0),
                fechacorte=item.get("fechacorte", ""),
                tipo_reporte=item.get("tiporeportepreciodesc", ""),
                tipo_entidad=item.get("tipoentidaddesc", ""),
            )
        )
    return records


def search_prices_by_atc(
    atc_code: str,
    limit: int = DEFAULT_LIMIT,
) -> list[PriceRecord]:
    """
    Search prices by ATC code (WHO drug classification).

    Useful when you know the drug class but not the specific CUM number.

    Args:
        atc_code: ATC code (e.g., "A10BA02" for metformin)
        limit: Maximum number of results

    Returns:
        List of PriceRecord objects matching the ATC code
    """
    params = {
        "atc": atc_code.upper(),
        "$limit": limit,
        "$order": "fechacorte DESC",
    }

    response = requests.get(BASE_URL, params=params, timeout=30)
    response.raise_for_status()

    records = []
    for item in response.json():
        precio_promedio = float(item.get("valorpromedio", 0) or 0)
        if precio_promedio == 0:
            continue

        records.append(
            PriceRecord(
                expedientecum=item.get("expedientecum", ""),
                descripcioncomercial=item.get("descripcioncomercial", ""),
                formafarmaceutica=item.get("formafarmaceutica", ""),
                atc=item.get("atc", ""),
                descripcion_atc=item.get("descripcion_atc", ""),
                precio_minimo=float(item.get("valorminimo", 0) or 0),
                precio_maximo=float(item.get("valormaximo", 0) or 0),
                precio_promedio=precio_promedio,
                unidades=float(item.get("unidades", 0) or 0),
                fechacorte=item.get("fechacorte", ""),
                tipo_reporte=item.get("tiporeportepreciodesc", ""),
                tipo_entidad=item.get("tipoentidaddesc", ""),
            )
        )
    return records


def get_price_range(prices: list[PriceRecord]) -> Optional[dict]:
    """
    Calculate summary price range from a list of price records.

    Args:
        prices: List of PriceRecord objects

    Returns:
        Dictionary with min, max, avg prices and data date, or None if empty

    Example:
        >>> prices = get_price_by_expediente("20097257")
        >>> summary = get_price_range(prices)
        >>> print(f"Rango: ${summary['min']:.0f} - ${summary['max']:.0f} COP")
    """
    if not prices:
        return None

    all_min = min(p.precio_minimo for p in prices if p.precio_minimo > 0)
    all_max = max(p.precio_maximo for p in prices)
    all_avg = sum(p.precio_promedio for p in prices) / len(prices)

    # Get most recent date
    most_recent = max(p.fechacorte for p in prices)

    return {
        "min": all_min,
        "max": all_max,
        "avg": all_avg,
        "fecha_datos": most_recent,
        "num_registros": len(prices),
    }


def main():
    """
    Smoke test for SISMED API.

    Run with:
        uv run python -m src.api.sismed

    Or:
        uv run python src/api/sismed.py
    """
    print("=" * 60)
    print("SISMED API Smoke Test")
    print("=" * 60)

    # Test 1: Get prices by expediente (Mebendazol - known to have data)
    print("\n[Test 1] Getting prices for expediente 35811 (Mebendazol)...")
    prices = get_price_by_expediente("35811", limit=10)
    print(f"Found {len(prices)} price records")
    for p in prices[:3]:
        print(f"  - ${p.precio_promedio:.0f} COP ({p.fechacorte})")
        print(f"    {p.tipo_entidad} | {p.tipo_reporte}")

    # Test 2: Get price range summary
    if prices:
        print("\n[Test 2] Calculating price range...")
        summary = get_price_range(prices)
        if summary:
            print(f"  Min: ${summary['min']:.0f} COP")
            print(f"  Max: ${summary['max']:.0f} COP")
            print(f"  Avg: ${summary['avg']:.0f} COP")
            print(f"  Data date: {summary['fecha_datos']}")
            print(f"  Records: {summary['num_registros']}")

    # Test 3: Search by ATC code (A10BA02 = Metformin)
    print("\n[Test 3] Searching prices by ATC code A10BA02 (Metformin)...")
    atc_prices = search_prices_by_atc("A10BA02", limit=5)
    print(f"Found {len(atc_prices)} price records")
    for p in atc_prices[:2]:
        print(f"  - ${p.precio_promedio:.0f} COP | {p.descripcion_atc}")

    print("\n" + "=" * 60)
    print("Smoke test completed!")
    print("NOTE: SISMED data is from 2019 - use as reference only")
    print("=" * 60)


if __name__ == "__main__":
    main()
