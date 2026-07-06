from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from bot.config import get_settings


def main_menu() -> ReplyKeyboardMarkup:
    miniapp = get_settings().miniapp_url
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="🚀 VPN'ni ulash", web_app=WebAppInfo(url=f"{miniapp}/connect"))],
            [
                KeyboardButton(text="💎 Tariflar", web_app=WebAppInfo(url=f"{miniapp}/plans")),
                KeyboardButton(text="👤 Profil"),
            ],
            [
                KeyboardButton(text="🌍 Serverlar"),
                KeyboardButton(text="🆘 Yordam"),
            ],
        ],
    )


def open_app_button(text: str = "🚀 Mini App'ni ochish", path: str = "") -> InlineKeyboardMarkup:
    miniapp = get_settings().miniapp_url
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=f"{miniapp}{path}"))]
        ]
    )


def stars_plans_keyboard(plans: list[dict]) -> InlineKeyboardMarkup:
    """Inline buttons for plans payable with Telegram Stars (price_stars > 0)."""
    rows = [
        [
            InlineKeyboardButton(
                text=f"⭐ {p['name']} — {int(p['price_stars'])} Stars",
                callback_data=f"stars:{p['id']}",
            )
        ]
        for p in plans
        if p.get("price_stars", 0) > 0
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
