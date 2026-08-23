"""
Client API untuk ProdSeller.
Dokumentasi: https://prodseller.com/api-docs/
"""

import requests
from config import PRODSELLER_API_KEY, PRODSELLER_BASE_URL


class ProdSellerAPI:
    """Client untuk API ProdSeller."""

    def __init__(self):
        self.base_url = PRODSELLER_BASE_URL
        self.headers = {
            "X-API-Key": PRODSELLER_API_KEY,
            "Content-Type": "application/json",
        }

    def _handle_error(self, e: requests.exceptions.HTTPError) -> dict:
        """Ambil pesan detail dari body response error API."""
        status = e.response.status_code
        detail = ""
        try:
            body = e.response.json()
            detail = (
                body.get("message")
                or body.get("error")
                or body.get("detail")
                or body.get("errors")
                or body
            )
        except ValueError:
            detail = e.response.text[:300]

        return {"error": f"HTTP {status}: {detail}"}

    def get_products(self) -> dict:
        """
        Mengambil daftar semua produk aktif.
        GET /v1/products
        """
        try:
            r = requests.get(
                f"{self.base_url}/products",
                headers=self.headers,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            return {"error": "Koneksi timeout. Coba lagi nanti."}
        except requests.exceptions.ConnectionError:
            return {"error": "Gagal terhubung ke server."}
        except requests.exceptions.HTTPError as e:
            return self._handle_error(e)
        except requests.exceptions.RequestException as e:
            return {"error": f"Terjadi kesalahan: {str(e)}"}
        except ValueError:
            return {"error": "Response dari server tidak valid."}

    def get_product(self, product_id: str) -> dict:
        """
        Mengambil detail produk berdasarkan ID.
        GET /v1/products/:id
        """
        try:
            r = requests.get(
                f"{self.base_url}/products/{product_id}",
                headers=self.headers,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            return {"error": "Koneksi timeout. Coba lagi nanti."}
        except requests.exceptions.ConnectionError:
            return {"error": "Gagal terhubung ke server."}
        except requests.exceptions.HTTPError as e:
            return self._handle_error(e)
        except requests.exceptions.RequestException as e:
            return {"error": f"Terjadi kesalahan: {str(e)}"}
        except ValueError:
            return {"error": "Response dari server tidak valid."}

    def get_balance(self) -> dict:
        """
        Mengambil saldo akun.
        GET /v1/balance
        """
        try:
            r = requests.get(
                f"{self.base_url}/balance",
                headers=self.headers,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            return {"error": "Koneksi timeout. Coba lagi nanti."}
        except requests.exceptions.ConnectionError:
            return {"error": "Gagal terhubung ke server."}
        except requests.exceptions.HTTPError as e:
            return self._handle_error(e)
        except requests.exceptions.RequestException as e:
            return {"error": f"Terjadi kesalahan: {str(e)}"}
        except ValueError:
            return {"error": "Response dari server tidak valid."}

    def create_order(
        self, product_id: str, quantity: int = 1, idempotency_key: str = None
    ) -> dict:
        """
        Membuat pesanan (mengurangi saldo).
        POST /v1/orders

        Args:
            product_id: ID produk ProdSeller
            quantity: Jumlah unit (default: 1)
            idempotency_key: Kunci unik untuk mencegah double-charge (max 100 char)
        """
        payload = {
            "productId": product_id,
            "quantity": quantity,
        }
        headers = dict(self.headers)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key[:100]

        try:
            r = requests.post(
                f"{self.base_url}/orders",
                headers=headers,
                json=payload,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            return {"error": "Koneksi timeout. Coba lagi nanti."}
        except requests.exceptions.ConnectionError:
            return {"error": "Gagal terhubung ke server."}
        except requests.exceptions.HTTPError as e:
            return self._handle_error(e)
        except requests.exceptions.RequestException as e:
            return {"error": f"Terjadi kesalahan: {str(e)}"}
        except ValueError:
            return {"error": "Response dari server tidak valid."}

    def get_orders(self, page: int = 1, limit: int = 50, status: str = None) -> dict:
        """
        Mengambil daftar order (riwayat pembelian via API).
        GET /v1/orders?page=&limit=&status=

        Args:
            page: Nomor halaman (default: 1)
            limit: Jumlah hasil per halaman (default: 50, max: 200)
            status: Filter status — pending | paid | delivered | failed
        """
        params = {"page": page, "limit": limit}
        if status:
            params["status"] = status

        try:
            r = requests.get(
                f"{self.base_url}/orders",
                headers=self.headers,
                params=params,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            return {"error": "Koneksi timeout. Coba lagi nanti."}
        except requests.exceptions.ConnectionError:
            return {"error": "Gagal terhubung ke server."}
        except requests.exceptions.HTTPError as e:
            return self._handle_error(e)
        except requests.exceptions.RequestException as e:
            return {"error": f"Terjadi kesalahan: {str(e)}"}
        except ValueError:
            return {"error": "Response dari server tidak valid."}

    def get_order(self, order_id: str) -> dict:
        """
        Mengambil status pesanan.
        GET /v1/orders/:id
        """
        try:
            r = requests.get(
                f"{self.base_url}/orders/{order_id}",
                headers=self.headers,
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except requests.exceptions.Timeout:
            return {"error": "Koneksi timeout. Coba lagi nanti."}
        except requests.exceptions.ConnectionError:
            return {"error": "Gagal terhubung ke server."}
        except requests.exceptions.HTTPError as e:
            return self._handle_error(e)
        except requests.exceptions.RequestException as e:
            return {"error": f"Terjadi kesalahan: {str(e)}"}
        except ValueError:
            return {"error": "Response dari server tidak valid."}

    # Alias untuk backward compatibility dengan bot.py
    def purchase(self, product_id: str, quantity: int = 1, idempotency_key: str = None) -> dict:
        """Alias untuk create_order."""
        return self.create_order(product_id, quantity, idempotency_key)
