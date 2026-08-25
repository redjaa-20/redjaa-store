"""
Bot Telegram untuk ProdSeller - Panel Distributor
Role: Admin & Reseller
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta

import os

from telegram import (
    BotCommand,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from telegram.request import HTTPXRequest

from config import (
    TELEGRAM_BOT_TOKEN,
    PROXY_URL,
    ADMIN_ID,
    PRICE_PER_UNIT,
    QRIS_IMAGE_PATH,
    PRODUCT_ID,
    PRODUCT_NAME,
    SUPPORT_USERNAME,
    PAKASIR_SLUG,
)
from api_client import ProdSellerAPI
import database as db
import pakasir
import currency

# ----------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------
# INISIALISASI
# ----------------------------------------------------------------
api = ProdSellerAPI()

# State untuk ConversationHandler
INPUT_QTY = 0
REGISTER_CODE = 2
WAIT_BUKTI = 4
INPUT_CUSTOM_PRICE = 3


# ================================================================
# HELPER: Cek Role
# ================================================================
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


def is_registered(user_id: int) -> bool:
    return is_admin(user_id) or db.is_reseller(user_id)


def get_role(user_id: int) -> str:
    """Ambil role user: admin, reseller, atau user."""
    if is_admin(user_id):
        return "admin"
    if db.is_reseller(user_id):
        return "reseller"
    return "user"

def pakasir_configured() -> bool:
    """Cek apakah konfigurasi Pakasir sudah lengkap."""
    return bool(PAKASIR_SLUG)


# ================================================================
# KEYBOARD
# ================================================================
def admin_keyboard():
    """Keyboard untuk Admin."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🛒 Gemini"), KeyboardButton("📦 Products")],
            [KeyboardButton("💰 Cek Saldo"), KeyboardButton("🏷️ Atur Harga")],
            [KeyboardButton("🔑 Buat Kode Reseller"), KeyboardButton("📋 Daftar Reseller")],
            [KeyboardButton("📜 Riwayat"), KeyboardButton("👤 Info Akun")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def user_keyboard():
    """Keyboard untuk User biasa."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🛒 Gemini")],
            [KeyboardButton("📝 Daftar Reseller")],
            [KeyboardButton("👤 Info Akun"), KeyboardButton("🆘 Support")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )

def reseller_keyboard():
    """Keyboard untuk Reseller."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("🛒 Gemini")],
            [KeyboardButton("👤 Info Akun"), KeyboardButton("🆘 Support")],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def batal_keyboard():
    """Keyboard dengan tombol Batal."""
    return ReplyKeyboardMarkup(
        [[KeyboardButton("❌ Batal")]],
        resize_keyboard=True,
    )


def jumlah_keyboard():
    """Keyboard pilihan jumlah 1 sampai 10 dan tombol Batal."""
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton("1"), KeyboardButton("2"), KeyboardButton("3"), KeyboardButton("4"), KeyboardButton("5")],
            [KeyboardButton("6"), KeyboardButton("7"), KeyboardButton("8"), KeyboardButton("9"), KeyboardButton("10")],
            [KeyboardButton("❌ Batal")],
        ],
        resize_keyboard=True,
    )

PRODUK_PER_PAGE = 10

def produk_nomor_keyboard(total_products: int, page: int = 0):
    """
    Keyboard ReplyKeyboard berisi tombol angka untuk daftar produk per halaman.
    Disusun 5 per baris, baris terakhir ditambah tombol Prev/Next dan Kembali ke Menu Utama.
    """
    per_page = PRODUK_PER_PAGE
    start = page * per_page       # 0-based index
    end = min(start + per_page, total_products)
    total_pages = (total_products + per_page - 1) // per_page

    rows = []
    row = []
    for i in range(start, end):
        # Nomor tampil = index global + 1
        row.append(KeyboardButton(str(i + 1)))
        if len(row) == 5:
            rows.append(row)
            row = []
    # Sisa tombol di baris terakhir
    if row:
        rows.append(row)

    # Baris Prev / Next (hanya tampilkan jika relevan)
    nav_row = []
    if page > 0:
        nav_row.append(KeyboardButton("⬅️ Prev"))
    if page < total_pages - 1:
        nav_row.append(KeyboardButton("➡️ Next"))
    if nav_row:
        rows.append(nav_row)

    # Baris Kembali ke Menu Utama
    rows.append([KeyboardButton("🏠 Kembali ke Menu Utama")])

    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def get_keyboard(user_id: int):
    """Ambil keyboard sesuai role user."""
    if is_admin(user_id):
        return admin_keyboard()
    elif db.is_reseller(user_id):
        return reseller_keyboard()
    else:
        return user_keyboard()


# ================================================================
# /start
# ================================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /start."""
    user = update.effective_user
    uid = user.id

    # Admin → langsung ke menu admin
    if is_admin(uid):
        await update.message.reply_text(
            f"👋 Halo, <b>{user.first_name}</b>!\n\n"
            f"Selamat datang di <b>Redjaa Digital Bot</b> 🚀\n"
            f"Role Anda: <b>👑 Admin</b>\n\n"
            f"Gunakan menu di bawah untuk memulai 👇",
            parse_mode="HTML",
            reply_markup=admin_keyboard(),
        )
        return ConversationHandler.END

    # Reseller terdaftar → langsung ke menu reseller
    if db.is_reseller(uid):
        await update.message.reply_text(
            f"👋 Halo, <b>{user.first_name}</b>!\n\n"
            f"Selamat datang kembali di <b>Redjaa Digital Bot</b> 🚀\n"
            f"Role Anda: <b>🏪 Reseller</b>\n\n"
            f"Gunakan menu di bawah untuk memulai 👇",
            parse_mode="HTML",
            reply_markup=reseller_keyboard(),
        )
        return ConversationHandler.END

    # Guest/User biasa → tampilkan menu user
    await update.message.reply_text(
        f"👋 Halo, <b>{user.first_name}</b>!\n\n"
        f"Selamat datang di <b>Redjaa Digital Bot</b> 🚀\n"
        f"Role Anda: <b>👤 User</b>\n\n"
        f"Gunakan menu di bawah untuk memulai 👇",
        parse_mode="HTML",
        reply_markup=user_keyboard(),
    )
    return ConversationHandler.END


async def daftar_reseller_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User biasa daftar jadi reseller → minta kode reseller."""
    uid = update.effective_user.id

    # Admin & reseller tidak perlu daftar lagi
    if is_admin(uid):
        await update.message.reply_text("ℹ️ Anda sudah Admin.")
        return ConversationHandler.END
    if db.is_reseller(uid):
        await update.message.reply_text("ℹ️ Anda sudah terdaftar sebagai Reseller.")
        return ConversationHandler.END

    await update.message.reply_text(
        f"📝 <b>Daftar Reseller</b>\n\n"
        f"🔐 Untuk menjadi reseller, masukkan <b>kode reseller</b> dari admin.\n\n"
        f"Silakan masukkan kode reseller Anda:",
        parse_mode="HTML",
        reply_markup=batal_keyboard(),
    )
    return REGISTER_CODE

async def start_input_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Guest memasukkan kode saat /start."""
    code = update.message.text.strip().upper()
    user = update.effective_user
    name = f"{user.first_name} {user.last_name or ''}".strip()

    success = db.use_code(code, user.id, name)

    if not success:
        await update.message.reply_text(
            "❌ Kode tidak valid atau sudah dipakai.\n"
            "Coba lagi atau ketuk <b>❌ Batal</b>.",
            parse_mode="HTML",
        )
        return REGISTER_CODE

    await update.message.reply_text(
        f"✅ <b>Registrasi Berhasil!</b>\n\n"
        f"Selamat, <b>{name}</b>! 🎉\n"
        f"Anda sekarang terdaftar sebagai <b>🏪 Reseller</b>.\n\n"
        f"Gunakan menu di bawah untuk mulai 👇",
        parse_mode="HTML",
        reply_markup=reseller_keyboard(),
    )
    return ConversationHandler.END


async def start_batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User membatalkan input kode."""
    uid = update.effective_user.id
    await update.message.reply_text(
        "❌ Dibatalkan.",
        reply_markup=get_keyboard(uid),
    )
    return ConversationHandler.END


# ================================================================
# HELPER: Waktu WIB
# ================================================================
def now_wib() -> str:
    """Waktu sekarang dalam format 'DD/MM/YYYY • HH:MM:SS WIB' (UTC+7)."""
    wib = datetime.now(timezone.utc) + timedelta(hours=7)
    return wib.strftime("%d/%m/%Y • %H:%M:%S WIB")


# ================================================================
# HELPER: Bangun pesan "Pembelian Berhasil"
# ================================================================
def build_success_message(order_id: str, quantity: int, result: dict, product_name: str = None) -> str:
    """
    Bangun pesan pembelian berhasil sesuai format Redjaa Digital.
    """
    pname = product_name or PRODUCT_NAME
    garis = "─" * 19

    text = "✅ <b>Pembelian Berhasil!</b>\n\n"
    text += f"🔖 Order ID : <code>{order_id}</code>\n"
    text += f"📦 Produk   : {pname}\n"
    text += f"🔢 Jumlah   : {quantity} unit\n"
    text += f"{garis}\n"
    text += "📋 <b>DATA PRODUK:</b>\n\n"

    # Ambil key dari response ProdSeller
    delivered_key = result.get("deliveredKey")
    delivered_keys = result.get("deliveredKeys", [])

    ada_data = False

    if delivered_keys and len(delivered_keys) > 0:
        # Multiple keys (quantity > 1)
        for idx, key in enumerate(delivered_keys, 1):
            if len(delivered_keys) > 1:
                text += f"<b>#{idx}</b>\n"
            text += f"🔑 Key : <code>{key}</code>\n"
            ada_data = True
            if len(delivered_keys) > 1:
                text += "\n"
    elif delivered_key:
        # Single key
        text += f"🔑 Key : <code>{delivered_key}</code>\n"
        ada_data = True

    # Fallback jika struktur tidak sesuai
    if not ada_data:
        for key, value in result.items():
            if key in ("orderId", "createdAt", "status"):
                continue
            text += f"🔑 {key} : <code>{value}</code>\n"
            ada_data = True

    text += f"{garis}\n"
    text += f"🕐 {now_wib()}\n\n"
    text += "<i>Terima kasih telah berbelanja!</i>"

    return text


# ================================================================
# HELPER: Kirim pesan panjang (split jika melebihi batas Telegram)
# ================================================================
TELEGRAM_MAX_CHARS = 4000  # Batas aman di bawah 4096 (batas Telegram)

def split_long_text(text: str, max_chars: int = TELEGRAM_MAX_CHARS) -> list[str]:
    """
    Pecah teks panjang menjadi beberapa bagian, maksimal max_chars per bagian.
    Pemotongan dilakukan di batas baris (\n) agar tidak memotong di tengah baris.
    """
    if len(text) <= max_chars:
        return [text]

    parts = []
    current = ""

    for line in text.split("\n"):
        # Jika satu baris saja sudah melebihi batas, potong paksa
        if len(line) > max_chars:
            if current:
                parts.append(current)
                current = ""
            for i in range(0, len(line), max_chars):
                parts.append(line[i:i + max_chars])
            continue

        # Jika menambah baris ini melebihi batas, simpan current dan mulai baru
        if len(current) + len(line) + 1 > max_chars:
            if current:
                parts.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line

    if current:
        parts.append(current)

    return parts


async def send_long_message(bot, chat_id: int, text: str, parse_mode: str = "HTML",
                            reply_markup=None, disable_notification: bool = False):
    """
    Kirim pesan yang mungkin lebih panjang dari batas Telegram.
    Jika melebihi batas, pecah menjadi beberapa pesan.
    reply_markup hanya dipasang di pesan terakhir.
    """
    parts = split_long_text(text)

    for i, part in enumerate(parts):
        is_last = (i == len(parts) - 1)
        await bot.send_message(
            chat_id=chat_id,
            text=part,
            parse_mode=parse_mode,
            reply_markup=reply_markup if is_last else None,
            disable_notification=disable_notification,
        )


# ================================================================
# 💰 CEK SALDO (Admin only)
# ================================================================
async def cek_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cek saldo - khusus Admin."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Akses ditolak. Menu ini khusus Admin.")
        return

    loading = await update.message.reply_text("⏳ Mengambil info saldo...")
    result = api.get_balance()

    if "error" in result:
        await loading.edit_text(
            f"❌ <b>Gagal mengambil saldo</b>\n\n{result['error']}",
            parse_mode="HTML",
        )
        return

    text = "💰 <b>Informasi Saldo</b>\n\n"
    text += f"🔹 <b>Username</b>  : <code>{result.get('username', '-')}</code>\n"
    saldo_usd = result.get('balance', 0)
    saldo_idr = currency.usd_to_idr(saldo_usd)
    text += f"🔹 <b>Saldo</b>     : <code>{currency.format_idr(saldo_idr)}</code> <i>(≈ ${saldo_usd})</i>\n"
    text += f"🔹 <b>Membership</b> : <code>{result.get('membership', '-')}</code>\n"
    text += f"\n📅 Diperbarui: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
    await loading.edit_text(text, parse_mode="HTML")


# ================================================================
# 🛒 GEMINI / BELI (Admin & Reseller)
# ================================================================
async def beli_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Langkah 1: Minta quantity."""
    uid = update.effective_user.id

    # Reset produk ke default (tombol Gemini langsung)
    context.user_data["selected_product_id"] = PRODUCT_ID
    context.user_data["selected_product_name"] = PRODUCT_NAME

    if is_admin(uid):
        info = (
            f"🛒 <b>Gemini — {PRODUCT_NAME}</b>\n\n"
            f"🔢 Masukkan jumlah yang ingin dibeli:\n"
            f"<i>(ketik angka, contoh: 1, 5, 10)</i>"
        )
    elif db.is_reseller(uid):
        harga = db.get_reseller_price(uid, PRICE_PER_UNIT)
        info = (
            f"🛒 <b>Gemini — {PRODUCT_NAME}</b>\n\n"
            f"💵 Harga per unit: <b>{currency.format_idr(harga)}</b>\n\n"
            f"🔢 Masukkan jumlah yang ingin dibeli:\n"
            f"<i>(ketik angka, contoh: 1, 5, 10)</i>"
        )
    else:
        # User biasa → pakai harga umum
        harga = db.get_general_price(PRICE_PER_UNIT)
        info = (
            f"🛒 <b>Gemini — {PRODUCT_NAME}</b>\n\n"
            f"💵 Harga per unit: <b>{currency.format_idr(harga)}</b>\n\n"
            f"🔢 Masukkan jumlah yang ingin dibeli:\n"
            f"<i>(ketik angka, contoh: 1, 5, 10)</i>"
        )

    await update.message.reply_text(
        info,
        parse_mode="HTML",
        reply_markup=jumlah_keyboard(),
    )
    return INPUT_QTY


async def beli_qty(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Langkah 2: Proses berdasarkan role."""
    text = update.message.text.strip()

    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ Jumlah harus berupa angka positif. Coba lagi:")
        return INPUT_QTY

    quantity = int(text)
    uid = update.effective_user.id

    # Ambil produk dari context (dari daftar Products) atau fallback ke default
    prod_id = context.user_data.get("selected_product_id", PRODUCT_ID)
    prod_name = context.user_data.get("selected_product_name", PRODUCT_NAME)

    # ADMIN → beli langsung ke API
    if is_admin(uid):
        return await _admin_beli_langsung(update, context, quantity, prod_id, prod_name)

    # USER/RESELLER → pilih metode konfirmasi pembayaran
    # Ambil harga untuk ditampilkan
    if db.is_reseller(uid):
        harga = db.get_reseller_price(uid, PRICE_PER_UNIT)
    else:
        harga = db.get_general_price(PRICE_PER_UNIT)
    total = quantity * harga

    # Cek apakah Pakasir tersedia
    pakasir_ready = pakasir_configured()

    buttons = []
    if pakasir_ready:
        buttons.append([InlineKeyboardButton(
            f"🤖 Otomatis (+biaya admin)",
            callback_data=f"metode_auto_{quantity}",
        )])
    buttons.append([InlineKeyboardButton(
        "👤 Manual (Tanpa biaya admin)",
        callback_data=f"metode_manual_{quantity}",
    )])

    metode_kb = InlineKeyboardMarkup(buttons)

    text_msg = (
        f"🛒 <b>Pilih Metode Pembayaran</b>\n\n"
        f"🔹 Produk : {prod_name}\n"
        f"🔹 Jumlah : {quantity} unit\n"
        f"🔹 Harga  : {currency.format_idr(harga)}/unit\n"
        f"🔹 Total  : <b>{currency.format_idr(total)}</b>\n\n"
    )
    if pakasir_ready:
        text_msg += (
            f"🤖 <b>Otomatis</b> — Bayar via QRIS Pakasir, verifikasi otomatis.\n"
            f"<i>(Ada biaya admin dari payment gateway)</i>\n\n"
            f"👤 <b>Manual</b> — Bayar via QRIS, kirim bukti transfer, admin verifikasi.\n"
            f"<i>(Tanpa biaya admin)</i>\n\n"
            f"Pilih metode pembayaran:"
        )
    else:
        text_msg += (
            f"👤 <b>Manual</b> — Bayar via QRIS, kirim bukti transfer, admin verifikasi.\n"
            f"<i>(Tanpa biaya admin)</i>\n\n"
            f"Pilih metode pembayaran:"
        )

    await update.message.reply_text(
        text_msg,
        parse_mode="HTML",
        reply_markup=metode_kb,
    )
    return ConversationHandler.END


async def _admin_beli_langsung(update, context, quantity: int, product_id: str = None, product_name: str = None):
    """Admin beli langsung ke API tanpa pembayaran."""
    uid = update.effective_user.id
    pid = product_id or context.user_data.get("selected_product_id", PRODUCT_ID)
    pname = product_name or context.user_data.get("selected_product_name", PRODUCT_NAME)

    loading = await update.message.reply_text(
        f"⏳ Memproses pembelian <b>{quantity}x</b> {pname}...",
        parse_mode="HTML",
    )

    result = api.purchase(product_id=pid, quantity=quantity)

    if "error" in result:
        await loading.edit_text(
            f"❌ <b>Gagal membeli</b>\n\n{result['error']}",
            parse_mode="HTML",
        )
        await update.message.reply_text(
            "Kembali ke menu admin.",
            reply_markup=admin_keyboard(),
        )
        # Cleanup
        context.user_data.pop("selected_product_id", None)
        context.user_data.pop("selected_product_name", None)
        return ConversationHandler.END

    order_id = db.generate_order_id()
    reply = build_success_message(order_id, quantity, result, product_name=pname)

    # Gunakan send_long_message untuk handle pesan yang mungkin sangat panjang
    await send_long_message(
        context.bot,
        chat_id=uid,
        text=reply,
        parse_mode="HTML",
    )
    # Hapus pesan loading setelah produk terkirim
    try:
        await loading.delete()
    except Exception:
        pass
    await update.message.reply_text(
        "Kembali ke menu admin.",
        reply_markup=admin_keyboard(),
    )
    # Cleanup
    context.user_data.pop("selected_product_id", None)
    context.user_data.pop("selected_product_name", None)
    return ConversationHandler.END


async def pilih_metode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: user/reseller pilih metode pembayaran (auto/manual)."""
    query = update.callback_query
    await query.answer()

    data = query.data  # metode_auto_5 atau metode_manual_5
    parts = data.split("_")
    method = parts[1]  # auto / manual
    quantity = int(parts[2])

    # Hapus pesan pilihan metode
    try:
        await query.message.delete()
    except Exception:
        pass

    # Lanjut buat order dengan metode yang dipilih
    await _reseller_buat_order(update, context, quantity, method)

async def _reseller_buat_order(update, context, quantity: int, method: str = "manual"):
    """Reseller buat order + tampilkan QRIS untuk pembayaran."""
    user = update.effective_user
    uid = user.id
    name = f"{user.first_name} {user.last_name or ''}".strip()

    # Ambil produk dari context (dari daftar Products) atau fallback ke default
    prod_id = context.user_data.get("selected_product_id", PRODUCT_ID)
    prod_name = context.user_data.get("selected_product_name", PRODUCT_NAME)

    # Tampilkan loading dulu supaya reseller tahu bot sedang bekerja
    loading = await context.bot.send_message(
        chat_id=uid,
        text="⏳ <b>Membuat order & menyiapkan QRIS...</b>\n"
        "<i>Mohon tunggu sebentar.</i>",
        parse_mode="HTML",
    )

    # Ambil harga sesuai role: reseller pakai harga reseller, user biasa pakai harga umum
    if db.is_reseller(uid):
        harga = db.get_reseller_price(uid, PRICE_PER_UNIT)
    else:
        harga = db.get_general_price(PRICE_PER_UNIT)
    total = quantity * harga
    order_id = db.create_order(uid, name, quantity, total, username=user.username or "",
                               product_id=prod_id, product_name=prod_name)

    # ================================================================
    # METODE OTOMATIS (Pakasir) → kirim QRIS image + URL pembayaran + cek status
    # ================================================================
    if method == "auto":
        if not pakasir_configured():
            try:
                await loading.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=uid,
                text="⚠️ <b>Mode konfirmasi otomatis aktif, tapi Pakasir belum dikonfigurasi.</b>\n"
                "Hubungi admin untuk mengatur integrasi Pakasir.",
                parse_mode="HTML",
                reply_markup=get_keyboard(uid),
            )
            db.update_order_status(order_id, "rejected")
            return ConversationHandler.END

        # Buat transaksi QRIS via API → dapat QR string
        await context.bot.send_chat_action(chat_id=uid, action="upload_photo")
        trx_result = pakasir.create_qris_transaction(amount=total, order_id=order_id)

        if "error" in trx_result:
            try:
                await loading.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=uid,
                text=f"❌ <b>Gagal membuat transaksi QRIS</b>\n\n{trx_result['error']}",
                parse_mode="HTML",
                reply_markup=get_keyboard(uid),
            )
            db.update_order_status(order_id, "rejected")
            return ConversationHandler.END

        payment = trx_result.get("payment", {})
        qr_string = payment.get("payment_number", "")
        total_payment = payment.get("total_payment", total)
        fee = total_payment - total
        expired_at = payment.get("expired_at", "")

        pay_url = pakasir.build_qris_url(amount=total, order_id=order_id)

        caption = (
            f"🧾 <b>Order Dibuat</b>\n\n"
            f"🔹 Order ID : <code>{order_id}</code>\n"
            f"🔹 Produk   : {prod_name}\n"
            f"🔹 Jumlah   : {quantity}\n"
            f"🔹 Subtotal : {currency.format_idr(total)}\n"
            f"🔹 Biaya admin : {currency.format_idr(fee)}\n"
            f"🔹 Total Bayar : <b>{currency.format_idr(total_payment)}</b>\n\n"
            f"📲 <b>Scan QRIS di atas untuk membayar</b>\n"
            f"atau klik tombol <b>💸 Buka Link QRIS</b> di bawah.\n\n"
            f"✅ Setelah membayar, klik <b>🔍 Cek Pembayaran</b>. "
            f"Produk akan dikirim otomatis jika pembayaran terkonfirmasi."
        )

        pay_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("💸 Buka Link QRIS", url=pay_url)],
            [InlineKeyboardButton("🔍 Cek Pembayaran", callback_data=f"cekpay_{order_id}")],
            [InlineKeyboardButton("❌ Batalkan Order", callback_data=f"cancel_{order_id}")],
        ])

        # Kirim gambar QRIS
        if qr_string:
            qr_image = pakasir.generate_qr_image(qr_string)
            try:
                await loading.delete()
            except Exception:
                pass
            qris_msg = await context.bot.send_photo(
                chat_id=uid,
                photo=qr_image,
                caption=caption,
                parse_mode="HTML",
                reply_markup=pay_kb,
            )
            context.user_data["qris_message_id"] = qris_msg.message_id
        else:
            # Fallback: tidak ada QR string → kirim URL saja
            try:
                await loading.delete()
            except Exception:
                pass
            await context.bot.send_message(
                chat_id=uid,
                text=caption,
                parse_mode="HTML",
                reply_markup=pay_kb,
            )

        # Tidak masuk WAIT_BUKTI — reseller bayar via Pakasir, cek via tombol
        # Cleanup selected product (sudah tersimpan di order)
        context.user_data.pop("selected_product_id", None)
        context.user_data.pop("selected_product_name", None)
        return ConversationHandler.END

    # ================================================================
    # METODE MANUAL → kirim QRIS statis, tunggu foto bukti
    # ================================================================
    await context.bot.send_chat_action(chat_id=uid, action="upload_photo")

    caption = (
        f"🧾 <b>Order Dibuat</b>\n\n"
        f"🔹 Order ID : <code>{order_id}</code>\n"
        f"🔹 Produk   : {prod_name}\n"
        f"🔹 Jumlah   : {quantity}\n"
        f"🔹 Total    : <b>{currency.format_idr(total)}</b>\n\n"
        f"📲 <b>Silakan scan QRIS di atas untuk membayar.</b>\n"
        f"Setelah membayar, <b>kirim foto bukti transfer</b> ke chat ini.\n\n"
        f"⏳ Pesanan akan diproses setelah admin memverifikasi bukti pembayaran."
    )

    confirm_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("❌ Batalkan Order", callback_data=f"cancel_{order_id}")],
    ])

    # Kirim gambar QRIS pakai file_id cache (lebih cepat) atau upload dari file
    cached_file_id = db.get_setting("qris_file_id")

    sent_photo = None
    if cached_file_id:
        # Pakai file_id yang sudah di-cache → hampir instan, tanpa upload
        try:
            sent_photo = await context.bot.send_photo(
                chat_id=uid,
                photo=cached_file_id,
                caption=caption,
                parse_mode="HTML",
                reply_markup=confirm_kb,
            )
        except Exception:
            # file_id tidak valid lagi → reset & fallback ke file
            db.set_setting("qris_file_id", None)
            cached_file_id = None

    if sent_photo is None and os.path.exists(QRIS_IMAGE_PATH):
        # Upload dari file lokal, lalu simpan file_id untuk pemakaian berikutnya
        with open(QRIS_IMAGE_PATH, "rb") as qris:
            sent_photo = await context.bot.send_photo(
                chat_id=uid,
                photo=qris,
                caption=caption,
                parse_mode="HTML",
                reply_markup=confirm_kb,
            )
        # Simpan file_id dari foto yang baru diupload
        if sent_photo and sent_photo.photo:
            db.set_setting("qris_file_id", sent_photo.photo[-1].file_id)

    if sent_photo is None:
        # Tidak ada cache & tidak ada file lokal
        await context.bot.send_message(
            chat_id=uid,
            text=f"⚠️ <i>File QRIS belum tersedia (admin belum upload).</i>\n\n" + caption,
            parse_mode="HTML",
            reply_markup=confirm_kb,
        )

    # Hapus pesan loading setelah QRIS siap ditampilkan
    try:
        await loading.delete()
    except Exception:
        pass

    # Simpan message_id QRIS untuk dihapus saat dibatalkan
    if sent_photo:
        context.user_data["qris_message_id"] = sent_photo.message_id

    # Simpan order_id di context untuk handler bukti transfer
    context.user_data["pending_order_id"] = order_id

    # Cleanup selected product (sudah tersimpan di order)
    context.user_data.pop("selected_product_id", None)
    context.user_data.pop("selected_product_name", None)

    # Conversation selesai — foto bukti ditangani standalone handler
    return ConversationHandler.END


# ================================================================
# 📸 RESELLER KIRIM BUKTI TRANSFER (foto) — standalone handler
# ================================================================
async def reseller_kirim_bukti(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reseller mengirim foto bukti transfer → teruskan ke admin."""
    uid = update.effective_user.id
    order_id = context.user_data.get("pending_order_id")

    # Hanya tangani jika ada order pending yang menunggu bukti (mode manual)
    if not order_id:
        return  # Bukan dalam state menunggu bukti → lewati

    order = db.get_order(order_id)
    if not order or order["status"] != "pending":
        await update.message.reply_text(
            "⚠️ Order tidak ditemukan atau sudah diproses.",
            reply_markup=get_keyboard(uid),
        )
        context.user_data.pop("pending_order_id", None)
        raise ApplicationHandlerStop

    # Ambil foto dengan resolusi tertinggi
    photo = update.message.photo[-1]

    # Update status ke paid
    db.update_order_status(order_id, "paid")

    # Beri tahu reseller
    await update.message.reply_text(
        f"✅ <b>Bukti pembayaran diterima!</b>\n\n"
        f"🔹 Order ID : <code>{order_id}</code>\n"
        f"🔹 Total    : <b>{currency.format_idr(order['total_price'])}</b>\n\n"
        f"⏳ Pembayaran Anda sedang diverifikasi admin.\n"
        f"Produk akan dikirim setelah dikonfirmasi.",
        parse_mode="HTML",
        reply_markup=get_keyboard(uid),
    )

    # Teruskan foto bukti ke admin dengan tombol konfirmasi
    admin_kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Konfirmasi & Kirim", callback_data=f"approve_{order_id}"),
            InlineKeyboardButton("❌ Tolak", callback_data=f"reject_{order_id}"),
        ],
    ])
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo.file_id,
        caption=(
            f"🔔 <b>Konfirmasi Pembayaran Baru</b>\n\n"
            f"🔹 Order ID : <code>{order_id}</code>\n"
            f"🔹 Reseller : {order['name']}\n"
            f"🔹 Username : {'@' + order['username'] if order.get('username') else '-'}\n"
            f"🔹 ID TG    : <code>{order['telegram_id']}</code>\n"
            f"🔹 Produk   : {order.get('product_name') or PRODUCT_NAME}\n"
            f"🔹 Jumlah   : {order['quantity']}\n"
            f"🔹 Total    : <b>{currency.format_idr(order['total_price'])}</b>\n"
            f"🔹 Waktu    : {order['created_at']}\n\n"
            f"📸 Cek bukti transfer di atas, lalu konfirmasi atau tolak."
        ),
        parse_mode="HTML",
        reply_markup=admin_kb,
    )

    context.user_data.pop("pending_order_id", None)
    raise ApplicationHandlerStop


async def reseller_bukti_bukan_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reseller kirim teks/dokumen (bukan foto) saat diminta bukti."""
    await update.message.reply_text(
        "📸 <b>Kirim bukti transfer sebagai FOTO.</b>\n"
        "Gunakan tombol klip/attach di Telegram, pilih foto bukti transfer.\n\n"
        "Atau ketuk <b>❌ Batalkan Order</b> di pesan QRIS untuk membatalkan.",
        parse_mode="HTML",
    )
    return WAIT_BUKTI


# ================================================================
# CALLBACK: Reseller batalkan order
# ================================================================
async def reseller_batal_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reseller membatalkan order."""
    query = update.callback_query
    await query.answer()

    order_id = query.data.replace("cancel_", "")
    order = db.get_order(order_id)

    if not order or order["status"] != "pending":
        await query.answer("Order tidak bisa dibatalkan.", show_alert=True)
        return

    db.update_order_status(order_id, "rejected")
    context.user_data.pop("pending_order_id", None)

    # Hapus pesan QRIS agar tidak bisa di-scan setelah dibatalkan
    try:
        await query.message.delete()
    except Exception:
        pass

    # Kirim notifikasi pembatalan ke reseller
    await context.bot.send_message(
        chat_id=order["telegram_id"],
        text=(
            f"❌ <b>Order Dibatalkan</b>\n\n"
            f"Order <code>{order_id}</code> telah dibatalkan."
        ),
        parse_mode="HTML",
        reply_markup=get_keyboard(order["telegram_id"]),
    )


# ================================================================
# CALLBACK: Admin approve / reject pembayaran
# ================================================================
async def admin_approve_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin konfirmasi pembayaran → request ke API → kirim produk ke reseller."""
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Hanya admin.", show_alert=True)
        return

    await query.answer()
    order_id = query.data.replace("approve_", "")
    order = db.get_order(order_id)

    if not order:
        await query.edit_message_caption(caption="❌ Order tidak ditemukan.", parse_mode="HTML")
        return

    if order["status"] == "delivered":
        await query.answer("Order ini sudah dikirim.", show_alert=True)
        return

    await query.edit_message_caption(
        caption=f"⏳ Memproses order <code>{order_id}</code> ke API...",
        parse_mode="HTML",
    )

    # Request ke API
    prod_id = order.get("product_id") or PRODUCT_ID
    prod_name = order.get("product_name") or PRODUCT_NAME
    result = api.purchase(product_id=prod_id, quantity=order["quantity"])

    if "error" in result:
        await query.edit_message_caption(
            caption=(
                f"❌ <b>Gagal request ke API</b>\n\n"
                f"Order: <code>{order_id}</code>\n"
                f"Error: {result['error']}\n\n"
                f"Order belum ditandai delivered. Coba lagi."
            ),
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔄 Coba Lagi", callback_data=f"approve_{order_id}"),
            ]]),
        )
        return

    db.update_order_status(order_id, "delivered")

    # Format data produk (harga API disembunyikan dari reseller)
    produk_text = build_success_message(order_id, order["quantity"], result, product_name=prod_name)

    # Kirim produk ke reseller
    await send_long_message(
        context.bot,
        chat_id=order["telegram_id"],
        text=produk_text,
        parse_mode="HTML",
    )

    # Notifikasi sukses ke admin
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=(
            f"✅ <b>Order Sukses (Manual)</b>\n\n"
            f"🔹 Order ID : <code>{order_id}</code>\n"
            f"🔹 Reseller : {order['name']}\n"
            f"🔹 Username : {'@' + order['username'] if order.get('username') else '-'}\n"
            f"🔹 ID TG    : <code>{order['telegram_id']}</code>\n"
            f"🔹 Produk   : {prod_name}\n"
            f"🔹 Jumlah   : {order['quantity']} unit\n"
            f"🔹 Total    : <b>{currency.format_idr(order['total_price'])}</b>\n"
            f"🔹 Metode   : 👤 Manual\n"
            f"🔹 Waktu    : {now_wib()}"
        ),
        parse_mode="HTML",
    )

    # Update pesan admin
    await query.edit_message_caption(
        caption=(
            f"✅ <b>Order Selesai</b>\n\n"
            f"Order <code>{order_id}</code> telah dikonfirmasi dan produk "
            f"sudah dikirim ke reseller <b>{order['name']}</b>."
        ),
        parse_mode="HTML",
    )


async def admin_reject_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin tolak pembayaran."""
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Hanya admin.", show_alert=True)
        return

    await query.answer()
    order_id = query.data.replace("reject_", "")
    order = db.get_order(order_id)

    if not order:
        await query.edit_message_caption(caption="❌ Order tidak ditemukan.", parse_mode="HTML")
        return

    db.update_order_status(order_id, "rejected")

    # Beri tahu reseller
    await context.bot.send_message(
        chat_id=order["telegram_id"],
        text=(
            f"❌ <b>Pembayaran Ditolak</b>\n\n"
            f"Order <code>{order_id}</code> ditolak oleh admin.\n"
            f"Jika Anda merasa ini keliru, silakan hubungi admin."
        ),
        parse_mode="HTML",
    )

    await query.edit_message_caption(
        caption=f"❌ Order <code>{order_id}</code> ditolak. Reseller sudah diberi tahu.",
        parse_mode="HTML",
    )

# ================================================================
# 🔍 CEK PEMBAYARAN (Mode Auto - Pakasir)
# ================================================================
async def cek_pembayaran(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cek status pembayaran via Pakasir API → auto-proses jika completed."""
    query = update.callback_query
    await query.answer("⏳ Mengecek status pembayaran...", show_alert=False)

    order_id = query.data.replace("cekpay_", "")
    order = db.get_order(order_id)

    if not order:
        await query.answer("❌ Order tidak ditemukan.", show_alert=True)
        return

    if order["status"] != "pending":
        await query.answer("ℹ️ Order ini sudah diproses.", show_alert=True)
        return

    result = pakasir.check_transaction(
        amount=order["total_price"],
        order_id=order_id,
    )

    if "error" in result:
        await query.answer(
            f"❌ Gagal cek pembayaran: {result['error']}",
            show_alert=True,
        )
        return

    transaction = result.get("transaction", {})
    status = transaction.get("status", "").lower()

    if status == "completed":
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text(
            f"✅ <b>Pembayaran Terkonfirmasi!</b>\n"
            f"Order <code>{order_id}</code> sedang diproses...",
            parse_mode="HTML",
        )

        api_result = api.purchase(
            product_id=order.get("product_id") or PRODUCT_ID,
            quantity=order["quantity"],
        )

        if "error" in api_result:
            await query.message.reply_text(
                f"❌ <b>Gagal request ke API</b>\n\n"
                f"Order: <code>{order_id}</code>\n"
                f"Error: {api_result['error']}\n\n"
                f"Pembayaran sudah diterima. Hubungi admin untuk penanganan manual.",
                parse_mode="HTML",
                reply_markup=get_keyboard(order["telegram_id"]),
            )
            db.update_order_status(order_id, "paid")
            return

        db.update_order_status(order_id, "delivered")

        prod_name = order.get("product_name") or PRODUCT_NAME
        produk_text = build_success_message(order_id, order["quantity"], api_result, product_name=prod_name)
        await send_long_message(
            context.bot,
            chat_id=order["telegram_id"],
            text=produk_text,
            parse_mode="HTML",
            reply_markup=get_keyboard(order["telegram_id"]),
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"✅ <b>Order Sukses (Otomatis)</b>\n\n"
                f"🔹 Order ID : <code>{order_id}</code>\n"
                f"🔹 Reseller : {order['name']}\n"
                f"🔹 Username : {'@' + order['username'] if order.get('username') else '-'}\n"
                f"🔹 ID TG    : <code>{order['telegram_id']}</code>\n"
                f"🔹 Produk   : {prod_name}\n"
                f"🔹 Jumlah   : {order['quantity']} unit\n"
                f"🔹 Total    : <b>{currency.format_idr(order['total_price'])}</b>\n"
                f"🔹 Metode   : 🤖 Otomatis (Pakasir)\n"
                f"🔹 Waktu    : {now_wib()}"
            ),
            parse_mode="HTML",
        )
        return

    status_display = status or "pending"
    await query.answer(
        f"ℹ️ Status: {status_display}. Pembayaran belum terkonfirmasi.",
        show_alert=True,
    )

# ================================================================
# 🏷️ ATUR HARGA (Admin only)
# ================================================================
async def _handle_price_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router untuk input harga (umum/reseller) berdasarkan flag awaiting_input."""
    awaiting = context.user_data.get("awaiting_input")
    if not awaiting:
        return  # Tidak menunggu input → lewati ke handler lain

    if awaiting == "general_price":
        await atur_harga_umum_input(update, context)
    elif awaiting == "reseller_price":
        await atur_harga_reseller_input(update, context)

    # Hentikan propagasi ke handler lain (conversation handler, dll)
    raise ApplicationHandlerStop

async def atur_harga_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin pilih: atur harga umum atau harga reseller."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Akses ditolak. Menu ini khusus Admin.")
        return ConversationHandler.END

    harga_umum = db.get_general_price(PRICE_PER_UNIT)

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"💵 Harga Umum ({currency.format_idr(harga_umum)})", callback_data="setharga_umum")],
        [InlineKeyboardButton("🏪 Harga Reseller", callback_data="setharga_reseller")],
    ])
    await update.message.reply_text(
        "🏷️ <b>Atur Harga</b>\n\n"
        "Pilih jenis harga yang ingin diatur:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    return ConversationHandler.END


async def atur_harga_umum_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin pilih harga umum → minta input harga."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Hanya admin.", show_alert=True)
        return

    harga_sekarang = db.get_general_price(PRICE_PER_UNIT)
    context.user_data["awaiting_input"] = "general_price"

    await query.edit_message_text(
        f"💵 <b>Atur Harga Umum</b>\n\n"
        f"Harga saat ini: <b>{currency.format_idr(harga_sekarang)}</b> / unit\n\n"
        f"Masukkan harga umum baru (dalam Rupiah, angka saja):\n"
        f"<i>(contoh: 60000)</i>",
        parse_mode="HTML",
    )

async def atur_harga_umum_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin input harga umum → simpan."""
    uid = update.effective_user.id
    if not is_admin(uid) or context.user_data.get("awaiting_input") != "general_price":
        return

    text = update.message.text.strip().replace(".", "").replace(",", "")

    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ Harga harus angka positif. Coba lagi:")
        return

    price = int(text)
    db.set_general_price(price)
    context.user_data.pop("awaiting_input", None)
    await update.message.reply_text(
        f"✅ <b>Harga umum diperbarui!</b>\n\n"
        f"Harga umum: <b>{currency.format_idr(price)}</b> / unit",
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )

async def atur_harga_reseller_pilih(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin pilih harga reseller → tampilkan daftar reseller."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Hanya admin.", show_alert=True)
        return

    resellers = db.get_all_resellers()
    if not resellers:
        await query.edit_message_text("🏪 <b>Atur Harga Reseller</b>\n\nBelum ada reseller terdaftar.")
        return

    buttons = []
    for tid, data in resellers.items():
        harga = data.get("price", 0)
        label = f"{data['name']} — {currency.format_idr(harga)}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"setharga_r_{tid}")])

    await query.edit_message_text(
        "🏪 <b>Atur Harga Reseller</b>\n\nPilih reseller:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )

async def atur_harga_reseller_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin pilih reseller → minta input harga."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Hanya admin.", show_alert=True)
        return

    tid = int(query.data.replace("setharga_r_", ""))
    reseller = db.get_reseller(tid)
    if not reseller:
        await query.edit_message_text("❌ Reseller tidak ditemukan.")
        return

    context.user_data["awaiting_input"] = "reseller_price"
    context.user_data["harga_reseller_tid"] = tid
    harga_sekarang = reseller.get("price", 0)

    await query.edit_message_text(
        f"🏪 <b>Atur Harga Reseller</b>\n\n"
        f"🔹 Reseller : <b>{reseller['name']}</b>\n"
        f"🔹 Harga saat ini: <b>{currency.format_idr(harga_sekarang)}</b> / unit\n\n"
        f"Masukkan harga baru (dalam Rupiah, angka saja):\n"
        f"<i>(contoh: 40000)</i>",
        parse_mode="HTML",
    )

async def atur_harga_reseller_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin input harga reseller → simpan."""
    uid = update.effective_user.id
    if not is_admin(uid) or context.user_data.get("awaiting_input") != "reseller_price":
        return

    text = update.message.text.strip().replace(".", "").replace(",", "")

    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text("❌ Harga harus angka positif. Coba lagi:")
        return

    tid = context.user_data.get("harga_reseller_tid")
    if not tid:
        await update.message.reply_text("⚠️ Sesi habis. Coba lagi dari menu.")
        context.user_data.pop("awaiting_input", None)
        return

    price = int(text)
    reseller = db.get_reseller(tid)
    success = db.set_reseller_price(tid, price)

    if not success:
        await update.message.reply_text("❌ Gagal menyimpan. Reseller tidak ditemukan.")
    else:
        await update.message.reply_text(
            f"✅ <b>Harga reseller diperbarui!</b>\n\n"
            f"🔹 Reseller : <b>{reseller['name']}</b>\n"
            f"🔹 Harga baru: <b>{currency.format_idr(price)}</b> / unit",
            parse_mode="HTML",
            reply_markup=admin_keyboard(),
        )

    context.user_data.pop("awaiting_input", None)
    context.user_data.pop("harga_reseller_tid", None)


async def beli_batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Batalkan pembelian & order pending jika ada."""
    uid = update.effective_user.id

    # Batalkan order pending milik user (jika ada)
    pending = db.get_pending_order_by_user(uid)
    if pending:
        order_id, _ = pending
        db.update_order_status(order_id, "rejected")

    context.user_data.pop("pending_order_id", None)

    # Cleanup selected product
    context.user_data.pop("selected_product_id", None)
    context.user_data.pop("selected_product_name", None)
    context.user_data.pop("produk_list", None)
    context.user_data.pop("awaiting_produk_nomor", None)
    context.user_data.pop("produk_page", None)

    # Hapus pesan QRIS agar tidak bisa di-scan setelah dibatalkan
    qris_msg_id = context.user_data.pop("qris_message_id", None)
    if qris_msg_id:
        try:
            await context.bot.delete_message(chat_id=uid, message_id=qris_msg_id)
        except Exception:
            pass

    # Langsung tampilkan keyboard menu utama
    await update.message.reply_text(
        "❌ Dibatalkan.",
        reply_markup=get_keyboard(uid),
    )
    return ConversationHandler.END


async def beli_to_saldo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cek_saldo(update, context)
    return ConversationHandler.END


async def beli_to_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await info_akun(update, context)
    return ConversationHandler.END


async def beli_to_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)
    return ConversationHandler.END


async def beli_to_daftar_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await daftar_reseller(update, context)
    return ConversationHandler.END

async def beli_to_riwayat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await riwayat_pembelian(update, context)
    return ConversationHandler.END


# ================================================================
# 👤 INFO AKUN (Admin & Reseller)
# ================================================================
async def info_akun(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Info akun."""
    user = update.effective_user
    uid = user.id

    if is_admin(uid):
        role = "👑 Admin"
    elif db.is_reseller(uid):
        role = "🏪 Reseller"
    else:
        role = "👤 User"

    text = (
        f"👤 <b>Info Akun</b>\n\n"
        f"🔹 ID Telegram : <code>{uid}</code>\n"
        f"🔹 Nama        : {user.first_name} {user.last_name or ''}\n"
        f"🔹 Username    : @{user.username or 'Tidak ada'}\n"
        f"🔹 Role        : <b>{role}</b>\n"
    )

    if db.is_reseller(uid):
        reseller = db.get_reseller(uid)
        harga = reseller.get("price", PRICE_PER_UNIT)
        text += (
            f"\n<b>── Data Reseller ──</b>\n"
            f"🔹 Terdaftar   : {reseller['registered_at']}\n"
            f"🔹 Kode Pakai  : <code>{reseller['code_used']}</code>\n"
            f"🔹 Harga/unit  : <b>{currency.format_idr(harga)}</b>\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")


# ================================================================
# 🔑 BUAT KODE RESELLER (Admin only)
# ================================================================
# Harga preset untuk tombol cepat
PRESET_PRICE = 35000


async def buat_kode_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Langkah 1: Admin pilih harga untuk kode reseller."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Akses ditolak. Menu ini khusus Admin.")
        return ConversationHandler.END

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{currency.format_idr(PRESET_PRICE)}", callback_data="genprice_preset")],
        [InlineKeyboardButton("✏️ Custom", callback_data="genprice_custom")],
    ])
    await update.message.reply_text(
        "🔑 <b>Buat Kode Reseller</b>\n\n"
        "Pilih harga jual per unit untuk reseller yang memakai kode ini:",
        parse_mode="HTML",
        reply_markup=kb,
    )
    return INPUT_CUSTOM_PRICE


async def genkode_preset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin pilih harga preset → langsung buat kode."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Hanya admin.", show_alert=True)
        return ConversationHandler.END

    code = db.generate_code(PRESET_PRICE)
    await query.edit_message_text(
        _kode_created_text(code, PRESET_PRICE),
        parse_mode="HTML",
    )
    return ConversationHandler.END


async def genkode_custom_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin pilih custom → minta input harga."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Hanya admin.", show_alert=True)
        return ConversationHandler.END

    await query.edit_message_text(
        "✏️ <b>Harga Custom</b>\n\n"
        "Masukkan harga jual per unit (dalam Rupiah, angka saja):\n"
        "<i>(contoh: 40000)</i>",
        parse_mode="HTML",
    )
    return INPUT_CUSTOM_PRICE


async def genkode_custom_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin input harga custom → buat kode."""
    text = update.message.text.strip().replace(".", "").replace(",", "")

    if not text.isdigit() or int(text) <= 0:
        await update.message.reply_text(
            "❌ Harga harus berupa angka positif. Coba lagi:"
        )
        return INPUT_CUSTOM_PRICE

    price = int(text)
    code = db.generate_code(price)
    await update.message.reply_text(
        _kode_created_text(code, price),
        parse_mode="HTML",
        reply_markup=admin_keyboard(),
    )
    return ConversationHandler.END


async def genkode_batal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Batalkan pembuatan kode."""
    await update.message.reply_text(
        "❌ Pembuatan kode dibatalkan.",
        reply_markup=admin_keyboard(),
    )
    return ConversationHandler.END


def _kode_created_text(code: str, price: int) -> str:
    """Format pesan kode berhasil dibuat."""
    return (
        f"🔑 <b>Kode Reseller Baru</b>\n\n"
        f"Kode  : <code>{code}</code>\n"
        f"Harga : <b>{currency.format_idr(price)}</b> / unit\n\n"
        f"📌 Berikan kode ini ke reseller.\n"
        f"Reseller cukup buka bot, ketik /start, "
        f"lalu masukkan kode ini. Harga jual reseller "
        f"akan otomatis mengikuti kode ini."
    )


# ================================================================
# 📋 DAFTAR RESELLER (Admin only)
# ================================================================
async def daftar_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lihat daftar semua reseller - khusus Admin."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Akses ditolak. Menu ini khusus Admin.")
        return

    resellers = db.get_all_resellers()

    if not resellers:
        await update.message.reply_text("📋 Belum ada reseller terdaftar.")
        return

    text = f"📋 <b>Daftar Reseller</b> ({len(resellers)} orang)\n\n"
    for tid, data in resellers.items():
        text += (
            f"👤 <b>{data['name']}</b>\n"
            f"   ID: <code>{tid}</code>\n"
            f"   Terdaftar: {data['registered_at']}\n"
            f"   Kode: <code>{data['code_used']}</code>\n\n"
        )

    await update.message.reply_text(text, parse_mode="HTML")


# ================================================================
# 📜 RIWAYAT PEMBELIAN (Admin only)
# ================================================================
RIWAYAT_PER_PAGE = 10

def _format_riwayat_page(orders: list, page: int, total: int) -> str:
    """Format teks riwayat untuk halaman tertentu."""
    garis = "─" * 22
    start = page * RIWAYAT_PER_PAGE
    end = start + RIWAYAT_PER_PAGE
    page_orders = orders[start:end]

    total_pages = (total + RIWAYAT_PER_PAGE - 1) // RIWAYAT_PER_PAGE

    text = "📜 <b>Riwayat Pembelian</b>\n\n"

    for o in page_orders:
        order_id = o.get("id") or o.get("order_id") or o.get("_id") or "-"
        status = o.get("status", "-")
        created = o.get("created_at") or o.get("createdAt") or o.get("date") or "-"

        # Produk & quantity
        items = o.get("items", [])
        if items:
            product_names = []
            total_qty = 0
            for item in items:
                product_names.append(item.get("product", item.get("name", "-")))
                total_qty += item.get("quantity", 0)
            produk = ", ".join(product_names[:3])
            if len(product_names) > 3:
                produk += f" (+{len(product_names) - 3})"
        else:
            produk = o.get("product") or PRODUCT_NAME
            total_qty = o.get("quantity", 0)

        # Harga
        total_price = o.get("total") or o.get("total_price") or o.get("price") or 0

        text += f"{garis}\n"
        text += f"🔖 Order ID : <code>{order_id}</code>\n"
        text += f"👤 Reseller : {o.get('name', '-')}\n"
        username = o.get("username")
        if username:
            text += f"📛 Username : @{username}\n"
        text += f"🆔 ID TG    : <code>{o.get('telegram_id', '-')}</code>\n"
        text += f"📦 Produk   : {produk}\n"
        text += f"🔢 Jumlah   : {total_qty} unit\n"

        if total_price:
            text += f"💰 Total    : <code>{currency.format_idr(total_price)}</code>\n"

        text += f"📊 Status   : <b>{status}</b>\n"
        text += f"🕐 Waktu    : {created}\n"

    text += f"{garis}\n"
    text += f"\n📄 Halaman {page + 1}/{total_pages} • Total {total} order"

    return text

def _riwayat_pagination_kb(page: int, total: int) -> InlineKeyboardMarkup:
    """Bangun tombol pagination untuk riwayat."""
    total_pages = (total + RIWAYAT_PER_PAGE - 1) // RIWAYAT_PER_PAGE
    buttons = []

    if total_pages <= 1:
        return None

    row = []
    if page > 0:
        row.append(InlineKeyboardButton("⬅️ Sebelumnya", callback_data=f"riwayat_{page - 1}"))
    if page < total_pages - 1:
        row.append(InlineKeyboardButton("Berikutnya ➡️", callback_data=f"riwayat_{page + 1}"))

    if row:
        buttons.append(row)

    return InlineKeyboardMarkup(buttons) if buttons else None

async def riwayat_pembelian(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan riwayat order dari database lokal - khusus Admin."""
    uid = update.effective_user.id

    if not is_admin(uid):
        await update.message.reply_text("⛔ Akses ditolak. Menu ini khusus Admin.")
        return

    loading = await update.message.reply_text("⏳ Mengambil riwayat order...")

    # ProdSeller API tidak punya endpoint list orders,
    # jadi ambil dari database lokal
    orders = db.get_all_orders()

    if not orders:
        await loading.edit_text(
            "📜 <b>Riwayat Pembelian</b>\n\n<i>Belum ada riwayat order.</i>",
            parse_mode="HTML",
        )
        return

    # Simpan orders ke context untuk pagination
    context.user_data["riwayat_orders"] = orders

    page = 0
    total = len(orders)
    text = _format_riwayat_page(orders, page, total)
    kb = _riwayat_pagination_kb(page, total)

    await loading.edit_text(text, parse_mode="HTML", reply_markup=kb)

async def riwayat_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback pagination riwayat pembelian."""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.answer("⛔ Hanya admin.", show_alert=True)
        return

    orders = context.user_data.get("riwayat_orders")
    if not orders:
        await query.edit_message_text("⚠️ Data riwayat sudah kedaluwarsa. Ketik /riwayat untuk memuat ulang.")
        return

    page = int(query.data.replace("riwayat_", ""))
    total = len(orders)
    total_pages = (total + RIWAYAT_PER_PAGE - 1) // RIWAYAT_PER_PAGE

    if page < 0 or page >= total_pages:
        return

    text = _format_riwayat_page(orders, page, total)
    kb = _riwayat_pagination_kb(page, total)

    await query.edit_message_text(text, parse_mode="HTML", reply_markup=kb)


# ================================================================
# 🆘 SUPPORT
# ================================================================
async def support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tampilkan tombol untuk menghubungi admin di Telegram."""
    if not SUPPORT_USERNAME:
        await update.message.reply_text(
            "🆘 <b>Support</b>\n\n"
            "⚠️ Kontak support belum dikonfigurasi oleh admin.",
            parse_mode="HTML",
        )
        return

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "💬 Hubungi Admin",
            url=f"https://t.me/{SUPPORT_USERNAME}",
        )],
    ])
    await update.message.reply_text(
        "🆘 <b>Support</b>\n\n"
        "Ada kendala atau pertanyaan? Klik tombol di bawah untuk "
        "menghubungi admin langsung. 👇",
        parse_mode="HTML",
        reply_markup=kb,
    )


async def beli_to_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await support(update, context)
    return ConversationHandler.END

async def beli_to_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await daftar_produk(update, context)
    return ConversationHandler.END

# ================================================================
# 📦 DAFTAR PRODUK (Fetch dari API)
# ================================================================
async def daftar_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch daftar produk dari ProdSeller API dan tampilkan sebagai daftar bernomor + keyboard angka (pagination)."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ Akses ditolak. Menu ini khusus Admin.")
        return
    loading = await update.message.reply_text("⏳ Mengambil daftar produk...")

    result = api.get_products()

    if "error" in result:
        await loading.edit_text(
            f"❌ <b>Gagal mengambil daftar produk</b>\n\n{result['error']}",
            parse_mode="HTML",
        )
        return

    products = result if isinstance(result, list) else result.get("data", result.get("products", []))

    if not products:
        await loading.edit_text("📭 Tidak ada produk tersedia saat ini.")
        return

    # Simpan daftar produk ke user_data
    context.user_data["produk_list"] = products
    context.user_data["awaiting_produk_nomor"] = True
    context.user_data["produk_page"] = 0  # mulai dari halaman 1 (index 0)

    await loading.delete()
    await _tampilkan_halaman_produk(update, context, page=0)

async def _tampilkan_halaman_produk(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int):
    """Tampilkan satu halaman daftar produk (maksimal 10 per halaman)."""
    products = context.user_data.get("produk_list", [])
    per_page = PRODUK_PER_PAGE
    total = len(products)
    total_pages = (total + per_page - 1) // per_page

    start = page * per_page
    end = min(start + per_page, total)

    text = "📦 <b>Daftar Produk</b>\n\n"
    for i in range(start, end):
        p = products[i]
        nama = p.get("name", p.get("productName", "Tanpa Nama"))
        stok = p.get("stock", p.get("inStock", "-"))

        if isinstance(stok, (int, float)):
            stok_str = str(int(stok))
        elif isinstance(stok, str) and stok.isdigit():
            stok_str = stok
        else:
            stok_str = str(stok) if stok != "-" else "?"

        text += f"<b>[{i + 1}]</b> {nama} ( {stok_str} )\n"

    text += f"\n📄 Halaman {page + 1}/{total_pages}"
    text += "\n<i>Ketuk nomor produk di keyboard bawah untuk membeli.</i>"

    kb = produk_nomor_keyboard(total, page)

    # Gunakan message.reply_text untuk pesan baru
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=kb,
    )

async def produk_prev(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigasi ke halaman sebelumnya daftar produk."""
    if not context.user_data.get("awaiting_produk_nomor"):
        return

    page = context.user_data.get("produk_page", 0)
    if page > 0:
        page -= 1
        context.user_data["produk_page"] = page
        await _tampilkan_halaman_produk(update, context, page)

async def produk_next(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Navigasi ke halaman berikutnya daftar produk."""
    if not context.user_data.get("awaiting_produk_nomor"):
        return

    products = context.user_data.get("produk_list", [])
    total = len(products)
    total_pages = (total + PRODUK_PER_PAGE - 1) // PRODUK_PER_PAGE
    page = context.user_data.get("produk_page", 0)

    if page < total_pages - 1:
        page += 1
        context.user_data["produk_page"] = page
        await _tampilkan_halaman_produk(update, context, page)

async def produk_kembali_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kembali ke menu utama dari daftar produk."""
    uid = update.effective_user.id
    context.user_data.pop("awaiting_produk_nomor", None)
    context.user_data.pop("produk_list", None)
    context.user_data.pop("produk_page", None)

    await update.message.reply_text(
        "🏠 Kembali ke menu utama.",
        reply_markup=get_keyboard(uid),
    )

async def pilih_produk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User ketuk nomor produk di keyboard → cari produk → minta jumlah."""
    uid = update.effective_user.id

    # Hanya proses jika sedang dalam state memilih nomor produk
    if not context.user_data.get("awaiting_produk_nomor"):
        return  # Bukan dalam state pilih produk → lewati

    text = update.message.text.strip()

    # Validasi: harus angka
    if not text.isdigit():
        await update.message.reply_text("❌ Masukkan nomor produk yang valid dari daftar.")
        return

    idx = int(text) - 1  # Convert ke 0-based index

    products = context.user_data.get("produk_list", [])

    if idx < 0 or idx >= len(products):
        await update.message.reply_text(
            f"❌ Nomor tidak valid. Pilih 1 sampai {len(products)}."
        )
        return

    produk = products[idx]

    pid = produk.get("id", "")
    nama = produk.get("name", produk.get("productName", "Tanpa Nama"))
    harga = produk.get("price", produk.get("amount", "-"))

    # Simpan produk yang dipilih ke user_data
    context.user_data["selected_product_id"] = pid
    context.user_data["selected_product_name"] = nama
    # Bersihkan state pilih nomor produk
    context.user_data.pop("awaiting_produk_nomor", None)

    # Ambil harga jual sesuai role
    if is_admin(uid):
        if harga != "-":
            harga_idr = currency.usd_to_idr(harga)
            info = (
                f"🛒 <b>Beli — {nama}</b>\n\n"
                f"💲 Harga API: <b>{currency.format_idr(harga_idr)}</b> <i>(≈ ${harga})</i>\n\n"
                f"🔢 Masukkan jumlah yang ingin dibeli:\n"
                f"<i>(ketik angka, contoh: 1, 5, 10)</i>"
            )
        else:
            info = (
                f"🛒 <b>Beli — {nama}</b>\n\n"
                f"🔢 Masukkan jumlah yang ingin dibeli:\n"
                f"<i>(ketik angka, contoh: 1, 5, 10)</i>"
            )
    elif db.is_reseller(uid):
        harga_jual = db.get_reseller_price(uid, PRICE_PER_UNIT)
        info = (
            f"🛒 <b>Beli — {nama}</b>\n\n"
            f"💵 Harga per unit: <b>{currency.format_idr(harga_jual)}</b>\n\n"
            f"🔢 Masukkan jumlah yang ingin dibeli:\n"
            f"<i>(ketik angka, contoh: 1, 5, 10)</i>"
        )
    else:
        harga_jual = db.get_general_price(PRICE_PER_UNIT)
        info = (
            f"🛒 <b>Beli — {nama}</b>\n\n"
            f"💵 Harga per unit: <b>{currency.format_idr(harga_jual)}</b>\n\n"
            f"🔢 Masukkan jumlah yang ingin dibeli:\n"
            f"<i>(ketik angka, contoh: 1, 5, 10)</i>"
        )

    await update.message.reply_text(
        info,
        parse_mode="HTML",
        reply_markup=jumlah_keyboard(),
    )
    return INPUT_QTY

# ================================================================
# SETUP BOT COMMANDS
# ================================================================
async def set_bot_commands(app: Application):
    commands = [
        BotCommand("start", "Mulai bot & tampilkan menu"),
        BotCommand("saldo", "Cek saldo akun"),
        BotCommand("beli", "Beli produk/layanan"),
        BotCommand("produk", "Lihat daftar produk"),
        BotCommand("info", "Info akun Anda"),
        BotCommand("riwayat", "Riwayat pembelian"),
        BotCommand("support", "Hubungi admin"),
    ]
    await app.bot.set_my_commands(commands)


# ================================================================
# MAIN
# ================================================================
async def main():
    print("=" * 50)
    print("🤖 Redjaa Digital Bot")
    print("=" * 50)

    if not TELEGRAM_BOT_TOKEN:
        print("❌ ERROR: Isi TELEGRAM_BOT_TOKEN di .env")
        return
    if not ADMIN_ID:
        print("⚠️  WARNING: ADMIN_ID belum diisi di .env")
        print("   Jalankan bot, klik Info Akun untuk lihat ID Anda,")
        print("   lalu isi ADMIN_ID di .env dan restart bot.")

    request_kwargs = {
        "connection_pool_size": 8,
        "connect_timeout": 60.0,
        "read_timeout": 60.0,
        "write_timeout": 60.0,
        "pool_timeout": 30.0,
    }
    if PROXY_URL:
        request_kwargs["proxy"] = PROXY_URL

    request = HTTPXRequest(**request_kwargs)
    get_updates_request = HTTPXRequest(**request_kwargs)

    app = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .request(request)
        .get_updates_request(get_updates_request)
        .build()
    )

    # --- ConversationHandler: /start (registrasi guest) ---
    start_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Regex("^📝 Daftar Reseller$"), daftar_reseller_user),
        ],
        states={
            REGISTER_CODE: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Batal$"),
                    start_input_code,
                ),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Batal$"), start_batal),
            CommandHandler("start", start),
        ],
    )

    # --- ConversationHandler: BELI ---
    beli_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🛒 Gemini$"), beli_start),
            CommandHandler("beli", beli_start),
            MessageHandler(filters.Regex("^[0-9]+$"), pilih_produk),
        ],
        states={
            INPUT_QTY: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Batal$")
                    & ~filters.Regex("^💰 Cek Saldo$") & ~filters.Regex("^👤 Info Akun$")
                    & ~filters.Regex("^🔑 Buat Kode Reseller$") & ~filters.Regex("^📋 Daftar Reseller$")
                    & ~filters.Regex("^🆘 Support$") & ~filters.Regex("^📜 Riwayat$")
                    & ~filters.Regex("^📦 Products$")
                    & ~filters.Regex("^⬅️ Prev$") & ~filters.Regex("^➡️ Next$")
                    & ~filters.Regex("^🏠 Kembali ke Menu Utama$")
                   ,
                    beli_qty,
                ),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Batal$"), beli_batal),
            MessageHandler(filters.Regex("^⬅️ Prev$"), produk_prev),
            MessageHandler(filters.Regex("^➡️ Next$"), produk_next),
            MessageHandler(filters.Regex("^🏠 Kembali ke Menu Utama$"), produk_kembali_menu),
            MessageHandler(filters.Regex("^💰 Cek Saldo$"), beli_to_saldo),
            MessageHandler(filters.Regex("^👤 Info Akun$"), beli_to_info),
            MessageHandler(filters.Regex("^📋 Daftar Reseller$"), beli_to_daftar_reseller),
            MessageHandler(filters.Regex("^🆘 Support$"), beli_to_support),
            MessageHandler(filters.Regex("^📜 Riwayat$"), beli_to_riwayat),
            MessageHandler(filters.Regex("^🛒 Gemini$"), beli_start),
            MessageHandler(filters.Regex("^📦 Products$"), beli_to_produk),
            CommandHandler("start", beli_to_start),
            CommandHandler("saldo", beli_to_saldo),
            CommandHandler("info", beli_to_info),
            CommandHandler("support", beli_to_support),
            CommandHandler("beli", beli_start),
        ],
    )

    # --- ConversationHandler: BUAT KODE RESELLER (pilih harga) ---
    kode_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex("^🔑 Buat Kode Reseller$"), buat_kode_reseller),
        ],
        states={
            INPUT_CUSTOM_PRICE: [
                CallbackQueryHandler(genkode_preset, pattern="^genprice_preset$"),
                CallbackQueryHandler(genkode_custom_prompt, pattern="^genprice_custom$"),
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND & ~filters.Regex("^❌ Batal$")
                    & ~filters.Regex("^🛒 Gemini$") & ~filters.Regex("^💰 Cek Saldo$")
                    & ~filters.Regex("^👤 Info Akun$") & ~filters.Regex("^📋 Daftar Reseller$")
                    & ~filters.Regex("^🆘 Support$") & ~filters.Regex("^📜 Riwayat$")
                    & ~filters.Regex("^📦 Products$")
                    & ~filters.Regex("^⬅️ Prev$") & ~filters.Regex("^➡️ Next$")
                    & ~filters.Regex("^🏠 Kembali ke Menu Utama$")
                   ,
                    genkode_custom_input,
                ),
            ],
        },
        fallbacks=[
            MessageHandler(filters.Regex("^❌ Batal$"), genkode_batal),
            MessageHandler(filters.Regex("^⬅️ Prev$"), produk_prev),
            MessageHandler(filters.Regex("^➡️ Next$"), produk_next),
            MessageHandler(filters.Regex("^🏠 Kembali ke Menu Utama$"), produk_kembali_menu),
            MessageHandler(filters.Regex("^🛒 Gemini$"), beli_to_start),
            MessageHandler(filters.Regex("^📦 Products$"), beli_to_produk),
            MessageHandler(filters.Regex("^💰 Cek Saldo$"), beli_to_saldo),
            MessageHandler(filters.Regex("^👤 Info Akun$"), beli_to_info),
            MessageHandler(filters.Regex("^📋 Daftar Reseller$"), beli_to_daftar_reseller),
            MessageHandler(filters.Regex("^🆘 Support$"), beli_to_support),
            MessageHandler(filters.Regex("^📜 Riwayat$"), beli_to_riwayat),
            MessageHandler(filters.Regex("^🔑 Buat Kode Reseller$"), buat_kode_reseller),
            CommandHandler("start", beli_to_start),
            CommandHandler("saldo", beli_to_saldo),
            CommandHandler("info", beli_to_info),
            CommandHandler("support", beli_to_support),
            CommandHandler("beli", beli_to_start),
        ],
    )

    # --- Daftarkan Handlers (urutan penting!) ---
    # Handler input harga (harus sebelum conversation handler agar teks tertangkap)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_price_input),
        group=-1,
    )
    # Handler foto bukti transfer (mode manual) — standalone, cek pending_order_id
    app.add_handler(
        MessageHandler(filters.PHOTO, reseller_kirim_bukti),
        group=-1,
    )
    app.add_handler(start_handler)
    app.add_handler(beli_handler)
    app.add_handler(kode_handler)
    app.add_handler(CommandHandler("saldo", cek_saldo))
    app.add_handler(CommandHandler("info", info_akun))
    app.add_handler(MessageHandler(filters.Regex("^💰 Cek Saldo$"), cek_saldo))
    app.add_handler(MessageHandler(filters.Regex("^👤 Info Akun$"), info_akun))
    app.add_handler(MessageHandler(filters.Regex("^📋 Daftar Reseller$"), daftar_reseller))
    app.add_handler(MessageHandler(filters.Regex("^📜 Riwayat$"), riwayat_pembelian))
    app.add_handler(CommandHandler("riwayat", riwayat_pembelian))
    app.add_handler(CommandHandler("produk", daftar_produk))
    app.add_handler(CommandHandler("support", support))
    app.add_handler(MessageHandler(filters.Regex("^🆘 Support$"), support))
    app.add_handler(MessageHandler(filters.Regex("^🏷️ Atur Harga$"), atur_harga_start))
    app.add_handler(MessageHandler(filters.Regex("^📦 Products$"), daftar_produk))
    app.add_handler(MessageHandler(filters.Regex("^⬅️ Prev$"), produk_prev))
    app.add_handler(MessageHandler(filters.Regex("^➡️ Next$"), produk_next))
    app.add_handler(MessageHandler(filters.Regex("^🏠 Kembali ke Menu Utama$"), produk_kembali_menu))
    app.add_handler(MessageHandler(filters.Regex("^❌ Batal$"), beli_batal))

    # --- Callback Handlers (pembayaran & konfirmasi) ---
    app.add_handler(CallbackQueryHandler(reseller_batal_order, pattern="^cancel_"))
    app.add_handler(CallbackQueryHandler(admin_approve_order, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(admin_reject_order, pattern="^reject_"))
    app.add_handler(CallbackQueryHandler(riwayat_pagination, pattern="^riwayat_"))
    app.add_handler(CallbackQueryHandler(cek_pembayaran, pattern="^cekpay_"))
    app.add_handler(CallbackQueryHandler(pilih_metode, pattern="^metode_"))
    app.add_handler(CallbackQueryHandler(atur_harga_umum_prompt, pattern="^setharga_umum$"))
    app.add_handler(CallbackQueryHandler(atur_harga_reseller_pilih, pattern="^setharga_reseller$"))
    app.add_handler(CallbackQueryHandler(atur_harga_reseller_prompt, pattern="^setharga_r_"))

    print("✅ Bot berjalan! Tekan Ctrl+C untuk berhenti.")

    async with app:
        await app.initialize()
        await set_bot_commands(app)
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)

        stop_event = asyncio.Event()
        try:
            await stop_event.wait()
        except (KeyboardInterrupt, SystemExit):
            pass
        finally:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n👋 Bot dihentikan.")
