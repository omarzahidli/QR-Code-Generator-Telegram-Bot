from typing import Final
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from io import BytesIO
import qrcode

TOKEN: Final = "YOUR_TELEGRAM_BOT_TOKEN_HERE"

# --- Helper functions ---
def main_menu_keyboard(lang: str):
    texts = {
        "az": ["Wifi QR yaratmaq", "Link QR yaratmaq"],
        "en": ["Wi-Fi QR", "Link QR"],
        "ru": ["Wi-Fi QR", "Ссылка QR"]
    }
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(texts[lang][0], callback_data='wifi_qr')],
        [InlineKeyboardButton(texts[lang][1], callback_data='link_qr')]
    ])

def language_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Azərbaycan 🇦🇿", callback_data='lang_az')],
        [InlineKeyboardButton("English 🇬🇧", callback_data='lang_en')],
        [InlineKeyboardButton("Русский 🇷🇺", callback_data='lang_ru')]
    ])

# --- Language strings ---
STRINGS = {
    "az": {
        "wifi_ssid": "📶 Zəhmət olmasa Wi-Fi SSID-ni daxil edin:",
        "wifi_pass": "📶 Zəhmət olmasa Wi-Fi Şifrəsini daxil edin (min 8 simvol):",
        "link_qr": "🔗 Zəhmət olmasa linki daxil edin (https://...):",
        "cancel": "İşlə bağlı əməliyyat ləğv olundu.",
        "short_password": "Şifrə ən az 8 simvol olmalıdır. Yenidən cəhd edin.",
        "main_menu": "Başlamaq üçün menyudan seçim edin:",
        "qr_done": "✅ QR kodunuz hazırdır!",
        "loading": "⏳ QR kod yaradılır..."
    },
    "en": {
        "wifi_ssid": "📶 Please enter the Wi-Fi SSID:",
        "wifi_pass": "📶 Please enter the Wi-Fi password (min 8 characters):",
        "link_qr": "🔗 Please enter the link (https://...):",
        "cancel": "Operation cancelled.",
        "short_password": "Password must be at least 8 characters. Try again.",
        "main_menu": "Select an option from the menu:",
        "qr_done": "✅ QR code generated!",
        "loading": "⏳ Generating QR..."
    },
    "ru": {
        "wifi_ssid": "📶 Пожалуйста, введите SSID Wi-Fi:",
        "wifi_pass": "📶 Пожалуйста, введите пароль Wi-Fi (минимум 8 символов):",
        "link_qr": "🔗 Пожалуйста, введите ссылку (https://...):",
        "cancel": "Операция отменена.",
        "short_password": "Пароль должен содержать минимум 8 символов. Попробуйте снова.",
        "main_menu": "Выберите опцию из меню:",
        "qr_done": "✅ QR код готов!",
        "loading": "⏳ Создание QR..."
    }
}

# --- Commands ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🇦🇿 Salam! Dilinizi seçin:\n🇬🇧 Hello! Please select your language:\n🇷🇺 Привет! Пожалуйста, выберите язык:",
        reply_markup=language_keyboard()
    )

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop('mode', None)
    context.user_data.pop('ssid', None)
    lang = context.user_data.get("lang", "az")
    await update.message.reply_text(STRINGS[lang]["cancel"], reply_markup=main_menu_keyboard(lang))

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Clean prompt for language selection
    await update.message.reply_text(
        "🇦🇿 Zəhmət olmasa dilinizi seçin:\n🇬🇧 Please select your language:\n🇷🇺 Пожалуйста, выберите язык:",
        reply_markup=language_keyboard()
    )

# --- Button handler ---
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = context.user_data.get("lang", "az")

    # Language selection
    if query.data.startswith("lang_"):
        lang_code = query.data.split("_")[1]
        context.user_data["lang"] = lang_code
        await query.message.reply_text(
            STRINGS[lang_code]["main_menu"],
            reply_markup=main_menu_keyboard(lang_code)
        )
        return

    # QR menu
    if query.data == 'wifi_qr':
        context.user_data["mode"] = "wifi_ssid"
        await query.message.reply_text(STRINGS[lang]["wifi_ssid"])
        return
    if query.data == 'link_qr':
        context.user_data['mode'] = 'link_qr_input'
        await query.message.reply_text(STRINGS[lang]["link_qr"])
        return

# --- QR generator with loading ---
async def send_qr(update: Update, context: ContextTypes.DEFAULT_TYPE, qr_data: str):
    lang = context.user_data.get("lang", "az")
    loading_msg = await update.message.reply_text(STRINGS[lang]["loading"])
    img = qrcode.make(qr_data)
    bio = BytesIO()
    bio.name = "qr.png"
    img.save(bio, 'PNG')
    bio.seek(0)
    await loading_msg.delete()
    caption = STRINGS[lang]["qr_done"]
    await update.message.reply_photo(photo=bio, caption=caption)

# --- Handle messages ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mode = context.user_data.get("mode")
    lang = context.user_data.get("lang", "az")
    if not mode:
        await update.message.reply_text(STRINGS[lang]["main_menu"], reply_markup=main_menu_keyboard(lang))
        return

    text = update.message.text.strip()

    # Wi-Fi SSID
    if mode == "wifi_ssid":
        context.user_data["ssid"] = text
        context.user_data["mode"] = "wifi_pass"
        await update.message.reply_text(STRINGS[lang]["wifi_pass"])
        return

    # Wi-Fi Password
    if mode == "wifi_pass":
        if len(text) < 8:
            await update.message.reply_text(STRINGS[lang]["short_password"])
            return
        ssid = context.user_data.get("ssid")
        password = text
        qr_data = f"WIFI:T:WPA;S:{ssid};P:{password};;"
        await send_qr(update, context, qr_data)
        context.user_data.pop("mode")
        context.user_data.pop("ssid")
        await update.message.reply_text(STRINGS[lang]["main_menu"], reply_markup=main_menu_keyboard(lang))
        return

    # Link QR (including image URLs)
    if mode == "link_qr_input":
        if not text.startswith("http://") and not text.startswith("https://"):
            text = "http://" + text
        await send_qr(update, context, text)
        context.user_data.pop("mode")
        await update.message.reply_text(STRINGS[lang]["main_menu"], reply_markup=main_menu_keyboard(lang))
        return

# --- Main ---
if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("language", language))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is running...")
    app.run_polling(poll_interval=3)
