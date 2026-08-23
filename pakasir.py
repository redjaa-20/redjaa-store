"""
Client untuk Pakasir Payment Gateway (QRIS).
Dokumentasi: https://pakasir.com/p/docs

Fokus: B.2 Opsi Hanya QRIS (URL integration) + C.2 Transaction create API + E. Transaction Detail API.
"""

import io
import qrcode
import requests
from config import PAKASIR_SLUG, PAKASIR_API_KEY

PAKASIR_PAY_BASE = "https://app.pakasir.com/pay"
PAKASIR_API_BASE = "https://app.pakasir.com/api"


def build_qris_url(amount: int, order_id: str) -> str:
    """
    Bangun URL pembayaran Pakasir dengan opsi qris_only=1 (B.2).

    Args:
        amount: nominal transaksi (Rupiah, tanpa titik/spasi)
        order_id: ID order/invoice di sistem kita

    Returns:
        URL pembayaran Pakasir (QRIS only)
    """
    return (
        f"{PAKASIR_PAY_BASE}/{PAKASIR_SLUG}/{amount}"
        f"?order_id={order_id}&qris_only=1"
    )


def create_qris_transaction(amount: int, order_id: str) -> dict:
    """
    Buat transaksi QRIS via API (C.2 Transaction create).

    POST https://app.pakasir.com/api/transactioncreate/qris

    Returns:
        dict dengan key 'payment' berisi:
        - payment_number (QR string)
        - total_payment (termasuk fee)
        - expired_at
        atau {'error': ...} jika gagal.
    """
    payload = {
        "project": PAKASIR_SLUG,
        "order_id": order_id,
        "amount": amount,
        "api_key": PAKASIR_API_KEY,
    }
    try:
        r = requests.post(
            f"{PAKASIR_API_BASE}/transactioncreate/qris",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        return {"error": "Koneksi timeout. Coba lagi nanti."}
    except requests.exceptions.ConnectionError:
        return {"error": "Gagal terhubung ke server Pakasir."}
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        detail = ""
        try:
            body = e.response.json()
            detail = body.get("message") or body.get("error") or body
        except ValueError:
            detail = e.response.text[:300]
        return {"error": f"HTTP {status}: {detail}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}
    except ValueError:
        return {"error": "Response dari server tidak valid."}


def generate_qr_image(qr_string: str) -> io.BytesIO:
    """
    Generate gambar QR code dari QR string.

    Returns:
        io.BytesIO berisi gambar PNG (siap dikirim via Telegram)
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(qr_string)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def check_transaction(amount: int, order_id: str) -> dict:
    """
    Cek status transaksi via API (E. Transaction Detail API).

    GET https://app.pakasir.com/api/transactiondetail
        ?project={slug}&amount={amount}&order_id={order_id}&api_key={api_key}

    Returns:
        dict dengan key 'transaction' berisi:
        - amount, order_id, project, status, payment_method, completed_at
        atau {'error': ...} jika gagal.
    """
    try:
        r = requests.get(
            f"{PAKASIR_API_BASE}/transactiondetail",
            params={
                "project": PAKASIR_SLUG,
                "amount": amount,
                "order_id": order_id,
                "api_key": PAKASIR_API_KEY,
            },
            timeout=30,
        )
        r.raise_for_status()
        return r.json()
    except requests.exceptions.Timeout:
        return {"error": "Koneksi timeout. Coba lagi nanti."}
    except requests.exceptions.ConnectionError:
        return {"error": "Gagal terhubung ke server Pakasir."}
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code
        detail = ""
        try:
            body = e.response.json()
            detail = body.get("message") or body.get("error") or body
        except ValueError:
            detail = e.response.text[:300]
        return {"error": f"HTTP {status}: {detail}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Terjadi kesalahan: {str(e)}"}
    except ValueError:
        return {"error": "Response dari server tidak valid."}
