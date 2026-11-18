"""
location.py - WiFi-Radar ID

Bantuan lokasi: cari nama tempat (geocoding), ubah koordinat menjadi nama
tempat (reverse geocoding), dan cari lokasi terdekat yang sudah ada.

Memakai OpenStreetMap Nominatim (gratis, tanpa API key). Aturan pemakaian:
  - wajib mengirim User-Agent,
  - maksimal ~1 request per detik (hasil di-cache agar tidak berulang),
  - bukan untuk autocomplete -> pencarian dijalankan lewat tombol "Cari".

Semua fungsi jaringan TIDAK pernah raise error; jika gagal mengembalikan
[] atau None supaya aplikasi tetap berjalan dan pengguna bisa isi manual.
"""

from __future__ import annotations

import math

try:
    import requests
except ImportError:
    requests = None

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "WiFi-Radar-ID/1.0 (Project Prokom 7; student project)"
TIMEOUT = 8  # detik
COUNTRY_CODES = "id"  # batasi pencarian ke Indonesia; kosongkan untuk seluruh dunia


def _get(path: str, params: dict):
    if requests is None:
        return None
    try:
        resp = requests.get(
            f"{NOMINATIM_URL}/{path}",
            params={**params, "format": "jsonv2", "addressdetails": 1, "accept-language": "id"},
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        return resp.json()
    except (requests.RequestException, ValueError):
        return None


def _split_place(item: dict) -> dict:
    """Ubah satu hasil Nominatim menjadi {name, area, latitude, longitude, label}."""
    addr = item.get("address", {}) or {}
    name = (
        item.get("name")
        or addr.get("amenity") or addr.get("shop") or addr.get("tourism")
        or addr.get("building") or addr.get("road") or ""
    )
    area_parts = [
        addr.get("suburb") or addr.get("neighbourhood") or addr.get("village"),
        addr.get("city_district"),
        addr.get("city") or addr.get("town") or addr.get("county"),
        addr.get("state"),
    ]
    area = ", ".join(dict.fromkeys(p for p in area_parts if p))  # buang duplikat
    return {
        "name": name,
        "area": area,
        "latitude": float(item["lat"]),
        "longitude": float(item["lon"]),
        "label": item.get("display_name", name),
    }


def search_places(query: str, limit: int = 5) -> list[dict]:
    """Cari tempat berdasarkan nama (mis. 'Kopi Lembah UGM'). [] jika gagal/kosong."""
    query = (query or "").strip()
    if len(query) < 3:
        return []
    params = {"q": query, "limit": limit}
    if COUNTRY_CODES:
        params["countrycodes"] = COUNTRY_CODES
    data = _get("search", params)
    if not isinstance(data, list):
        return []
    results = []
    for item in data:
        try:
            results.append(_split_place(item))
        except (KeyError, ValueError, TypeError):
            continue
    return results


def reverse_geocode(latitude: float, longitude: float) -> dict | None:
    """Koordinat -> nama tempat terdekat. None jika gagal."""
    data = _get("reverse", {"lat": latitude, "lon": longitude, "zoom": 18})
    if not isinstance(data, dict) or "lat" not in data:
        return None
    try:
        place = _split_place(data)
    except (KeyError, ValueError, TypeError):
        return None
    # Titik yang dipilih pengguna tetap dipakai, bukan titik bangunan OSM
    place["latitude"], place["longitude"] = float(latitude), float(longitude)
    return place


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Jarak dua koordinat dalam meter (rumus haversine)."""
    r = 6_371_000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest_known_location(latitude: float, longitude: float, locations: list[dict],
                           radius_m: float = 75.0) -> dict | None:
    """Lokasi yang sudah ada di database dalam radius tertentu (hindari duplikat)."""
    best, best_d = None, radius_m
    for loc in locations:
        try:
            d = distance_m(latitude, longitude, float(loc["latitude"]), float(loc["longitude"]))
        except (KeyError, TypeError, ValueError):
            continue
        if d <= best_d:
            best, best_d = loc, d
    return best
