"""
Konversi mata uang USD → IDR (Rupiah) menggunakan exchange rate dinamis.
API: https://open.er-api.com/v6/latest/USD (free, no API key, update harian)
"""

import time
import logging
import requests

logger = logging.getLogger(__name__)

# Cache: simpan rate dan timestamp terakhir fetch
_cached_rate: float | None = None
_cached_at: float = 0.0
CACHE_TTL = 3600  # 1 jam dalam detik

# Rate fallback jika API gagal (update manual jika perlu)
FALLBACK_RATE = 15800.0

API_URL = "https://open.er-api.com/v6/latest/USD"


def _fetch_rate() -> float | None:
    """Fetch kurs USD→IDR dari API."""
    global _cached_rate, _cached_at
    try:
        r = requests.get(API_URL, timeout=10)
        r.raise_for_status()
        data = r.json()
        rate = data.get("rates", {}).get("IDR")
        if rate and isinstance(rate, (int, float)):
            _cached_rate = float(rate)
            _cached_at = time.time()
            logger.info(f"Kurs USD→IDR diperbarui: {_cached_rate}")
            return _cached_rate
    except Exception as e:
        logger.warning(f"Gagal fetch kurs USD→IDR: {e}")
    return None


def get_rate() -> float:
    """
    Ambil kurs USD→IDR, dengan cache 1 jam.
    Jika cache masih valid, gunakan cache.
    Jika API gagal, gunakan rate fallback.
    """
    global _cached_rate, _cached_at
    now = time.time()
    if _cached_rate is not None and (now - _cached_at) < CACHE_TTL:
        return _cached_rate

    rate = _fetch_rate()
    if rate is not None:
        return rate

    # Jika pernah fetch sebelumnya, gunakan cache lama
    if _cached_rate is not None:
        return _cached_rate

    return FALLBACK_RATE


def usd_to_idr(usd: float | int | str) -> int:
    """
    Konversi USD ke IDR (Rupiah), dibulatkan ke bilangan bulat.
    Menerima float, int, atau str (angka).
    """
    try:
        usd_float = float(usd)
    except (ValueError, TypeError):
        return 0
    rate = get_rate()
    return int(round(usd_float * rate))


def format_idr(amount: int) -> str:
    """Format angka ke string Rupiah: Rp 17.864.000 (pemisah titik)"""
    return f"Rp {format(amount, ',').replace(',', '.')}"
