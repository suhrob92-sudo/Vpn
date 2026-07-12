from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
)

from bot.config import get_settings
from bot.i18n import Lang, t


def main_menu(lang: Lang) -> ReplyKeyboardMarkup:
    # Plain text buttons only: reply-keyboard web_app buttons launch the Mini App
    # WITHOUT initData on some Telegram Android builds, breaking auth. The text
    # handlers reply with an inline web_app button instead, which (like the bot
    # Menu Button) always provides initData.
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text=t(lang, "btn_connect"))],
            [
                KeyboardButton(text=t(lang, "btn_plans")),
                KeyboardButton(text=t(lang, "btn_profile")),
            ],
            [
                KeyboardButton(text=t(lang, "btn_servers")),
                KeyboardButton(text=t(lang, "btn_help")),
            ],
        ],
    )


def open_app_button(text: str, path: str = "") -> InlineKeyboardMarkup:
    miniapp = get_settings().miniapp_url
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=f"{miniapp}{path}"))]
        ]
    )


def stars_plans_keyboard(plans: list[dict], lang: Lang) -> InlineKeyboardMarkup:
    """Inline buttons for plans payable with Telegram Stars (price_stars > 0)."""
    rows = [
        [
            InlineKeyboardButton(
                text=t(lang, "stars_plan_btn", name=p["name"], stars=int(p["price_stars"])),
                callback_data=f"stars:{p['id']}",
            )
        ]
        for p in plans
        if p.get("price_stars", 0) > 0
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
