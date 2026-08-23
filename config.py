import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
PRODSELLER_API_KEY = os.getenv("PRODSELLER_API_KEY", "")
PRODSELLER_BASE_URL = os.getenv("PRODSELLER_BASE_URL", "https://prodseller.com/v1")
PROXY_URL = os.getenv("PROXY_URL", "")

def _int_env(key: str, default: int) -> int:
    """Baca env sebagai int, fallback ke default jika kosong/invalid."""
    value = os.getenv(key, "").strip()
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


ADMIN_ID = _int_env("ADMIN_ID", 0)

# Harga jual per unit untuk reseller (dalam Rupiah)
PRICE_PER_UNIT = _int_env("PRICE_PER_UNIT", 50000)

# Path file gambar QRIS statis (simpan di folder project)
QRIS_IMAGE_PATH = os.getenv("QRIS_IMAGE_PATH", "qris.jpg")

# Product ID ProdSeller yang dijual
PRODUCT_ID = os.getenv("PRODUCT_ID", "6a31035939dc014325da2c66")
PRODUCT_NAME = os.getenv("PRODUCT_NAME", "Gemini Pro 18 Months")

# Username Telegram admin untuk menu Support (tanpa @)
SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "").lstrip("@")

# ================================================================
# PAKASIR (Payment Gateway QRIS)
# ================================================================
PAKASIR_SLUG = os.getenv("PAKASIR_SLUG", "")
PAKASIR_API_KEY = os.getenv("PAKASIR_API_KEY", "")
