"""
Database sederhana menggunakan JSON file.
Menyimpan data reseller dan kode registrasi.
"""

import json
import os
import string
import random
from datetime import datetime

DB_FILE = "data.json"


def _load() -> dict:
    """Load database dari file."""
    if not os.path.exists(DB_FILE):
        return {"resellers": {}, "codes": {}, "orders": {}, "settings": {}}
    with open(DB_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Pastikan semua key ada
    data.setdefault("resellers", {})
    data.setdefault("codes", {})
    data.setdefault("orders", {})
    data.setdefault("settings", {})
    return data


def _save(data: dict):
    """Simpan database ke file."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ================================================================
# KODE RESELLER
# ================================================================
def generate_code(price: int) -> str:
    """
    Buat kode reseller acak (8 karakter) dengan harga per unit.

    Args:
        price: harga jual per unit untuk reseller yang pakai kode ini
    """
    chars = string.ascii_uppercase + string.digits
    code = "".join(random.choices(chars, k=8))

    db = _load()
    db["codes"][code] = {
        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "used": False,
        "used_by": None,
        "price": price,
    }
    _save(db)
    return code


def use_code(code: str, telegram_id: int, name: str) -> bool:
    """
    Pakai kode reseller untuk registrasi.
    Return True jika berhasil, False jika kode tidak valid/sudah dipakai.
    """
    db = _load()

    if code not in db["codes"]:
        return False
    if db["codes"][code]["used"]:
        return False

    # Ambil harga dari kode (fallback 0 untuk kode lama)
    price = db["codes"][code].get("price", 0)

    # Tandai kode sebagai sudah dipakai
    db["codes"][code]["used"] = True
    db["codes"][code]["used_by"] = telegram_id

    # Daftarkan reseller dengan harga yang diwariskan dari kode
    db["resellers"][str(telegram_id)] = {
        "name": name,
        "registered_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "code_used": code,
        "price": price,
    }

    _save(db)
    return True


def get_reseller_price(telegram_id: int, default: int = 0) -> int:
    """Ambil harga per unit khusus reseller."""
    db = _load()
    reseller = db["resellers"].get(str(telegram_id))
    if reseller:
        return reseller.get("price", default)
    return default

def set_reseller_price(telegram_id: int, price: int) -> bool:
    """Set harga per unit khusus untuk reseller tertentu."""
    db = _load()
    key = str(telegram_id)
    if key not in db["resellers"]:
        return False
    db["resellers"][key]["price"] = price
    _save(db)
    return True

def get_general_price(default: int = 0) -> int:
    """Ambil harga umum (untuk user biasa)."""
    db = _load()
    return db["settings"].get("general_price", default)

def set_general_price(price: int) -> None:
    """Set harga umum (untuk user biasa)."""
    set_setting("general_price", price)


def get_all_codes() -> dict:
    """Ambil semua kode reseller."""
    db = _load()
    return db.get("codes", {})


# ================================================================
# RESELLER
# ================================================================
def is_reseller(telegram_id: int) -> bool:
    """Cek apakah user adalah reseller terdaftar."""
    db = _load()
    return str(telegram_id) in db.get("resellers", {})


def get_reseller(telegram_id: int) -> dict | None:
    """Ambil data reseller."""
    db = _load()
    return db["resellers"].get(str(telegram_id))


def get_all_resellers() -> dict:
    """Ambil semua data reseller."""
    db = _load()
    return db.get("resellers", {})


# ================================================================
# ORDER (Pesanan Reseller)
# ================================================================
def generate_order_id() -> str:
    """
    Buat Order ID format RED-DDMMYY-NNN.
    NNN = nomor urut harian (reset tiap hari), mulai dari 001.
    """
    db = _load()
    today = datetime.now().strftime("%d%m%y")

    counters = db["settings"].get("order_counters", {})
    # Reset counter jika ganti hari
    seq = counters.get(today, 0) + 1
    counters = {today: seq}  # simpan hanya hari ini biar tidak menumpuk
    db["settings"]["order_counters"] = counters
    _save(db)

    return f"RED-{today}-{seq:03d}"


def create_order(telegram_id: int, name: str, quantity: int, total_price: int, username: str = "",
                 product_id: str = "", product_name: str = "", unique_code: int = 0) -> str:
    """
    Buat order baru dengan status 'pending'.
    Return order_id.
    """
    db = _load()

    order_id = generate_order_id()

    # Reload karena generate_order_id sudah menyimpan perubahan counter
    db = _load()
    db["orders"][order_id] = {
        "telegram_id": telegram_id,
        "name": name,
        "username": username,
        "quantity": quantity,
        "total_price": total_price,
        "unique_code": unique_code,
        "product_id": product_id,
        "product_name": product_name,
        "status": "pending",  # pending -> paid -> delivered / rejected
        "created_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "confirmed_at": None,
    }
    _save(db)
    return order_id


def get_order(order_id: str) -> dict | None:
    """Ambil data order."""
    db = _load()
    return db["orders"].get(order_id)


def update_order_status(order_id: str, status: str) -> bool:
    """Update status order."""
    db = _load()
    if order_id not in db["orders"]:
        return False
    db["orders"][order_id]["status"] = status
    if status in ("delivered", "rejected"):
        db["orders"][order_id]["confirmed_at"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    _save(db)
    return True


def get_pending_orders() -> dict:
    """Ambil semua order yang menunggu konfirmasi."""
    db = _load()
    return {
        oid: o for oid, o in db["orders"].items()
        if o["status"] in ("pending", "paid")
    }


def get_pending_order_by_user(telegram_id: int) -> tuple | None:
    """
    Cari order pending milik user.
    Return (order_id, order_data) atau None.
    """
    db = _load()
    for oid, o in db["orders"].items():
        if o["telegram_id"] == telegram_id and o["status"] == "pending":
            return oid, o
    return None


def get_all_orders() -> list:
    """
    Ambil semua order dari database lokal, urutkan dari terbaru ke terlama.
    Return list of dict, masing-masing dict sudah berisi key 'id' (order_id).
    """
    db = _load()
    orders = []
    for oid, o in db["orders"].items():
        entry = dict(o)
        entry["id"] = oid
        orders.append(entry)
    # Urutkan dari terbaru (created_at descending)
    orders.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return orders


# ================================================================
# SETTINGS (cache file_id QRIS, dll)
# ================================================================
def get_setting(key: str, default=None):
    """Ambil nilai setting."""
    db = _load()
    return db["settings"].get(key, default)

def generate_unique_code() -> int:
    """
    Buat kode unik 1-150 untuk membedakan transfer manual.
    Pastikan tidak ada kode yang sama yang masih pending.
    """
    import random as _random
    db = _load()
    # Ambil semua unique_code yang masih pending
    used_codes = {
        o.get("unique_code", 0)
        for o in db["orders"].values()
        if o.get("status") == "pending" and o.get("unique_code", 0) > 0
    }
    # Generate kode 1-150 yang belum dipakai
    for _ in range(200):
        code = _random.randint(1, 150)
        if code not in used_codes:
            return code
    # Fallback: return random saja
    return _random.randint(1, 150)


def set_setting(key: str, value):
    """Simpan nilai setting."""
    db = _load()
    db["settings"][key] = value
    _save(db)

# ================================================================
# SOLD COUNT (Jumlah terjual)
# ================================================================
def get_sold_count() -> int:
    """Ambil jumlah total produk yang terjual. Default 501."""
    db = _load()
    return db["settings"].get("sold_count", 501)

def increment_sold_count(quantity: int = 1) -> int:
    """Tambah jumlah terjual sebanyak quantity. Return nilai baru."""
    db = _load()
    current = db["settings"].get("sold_count", 501)
    current += quantity
    db["settings"]["sold_count"] = current
    _save(db)
    return current
