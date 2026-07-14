from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.i18n import LANGS, Lang, t

HAPP_URL = "https://play.google.com/store/search?q=happ%20proxy&c=apps"
V2RAYNG_URL = "https://play.google.com/store/apps/details?id=com.v2ray.ang"


def main_menu_inline(lang: Lang) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=t(lang, "btn_connect"), callback_data="m:connect")],
            [
                InlineKeyboardButton(text=t(lang, "btn_plans"), callback_data="m:plans"),
                InlineKeyboardButton(text=t(lang, "btn_profile"), callback_data="m:profile"),
            ],
            [
                InlineKeyboardButton(text=t(lang, "btn_servers"), callback_data="m:servers"),
                InlineKeyboardButton(text=t(lang, "btn_help"), callback_data="m:help"),
            ],
            [InlineKeyboardButton(text=t(lang, "m_lang"), callback_data="m:lang")],
        ]
    )


def back_inline(lang: Lang) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=t(lang, "back"), callback_data="m:home")]]
    )


def plans_inline(plans: list[dict], lang: Lang) -> InlineKeyboardMarkup:
    rows = []
    for p in plans:
        star = " ⭐" if p.get("is_popular") else ""
        price = f"{float(p['price']):g} {'₽' if p['currency'] == 'RUB' else p['currency']}"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{p['name']} · {price}{star}", callback_data=f"buy:{p['id']}"
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="m:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def plan_pay_inline(plan: dict, lang: Lang, balance: float) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if plan.get("price_stars", 0) > 0:
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "pay_stars_btn", stars=int(plan["price_stars"])),
                    callback_data=f"stars:{plan['id']}",
                )
            ]
        )
    if balance >= float(plan["price"]):
        rows.append(
            [
                InlineKeyboardButton(
                    text=t(lang, "pay_balance_btn", price=f"{float(plan['price']):g}"),
                    callback_data=f"bal:{plan['id']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text=t(lang, "back"), callback_data="m:plans")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def connect_inline(lang: Lang) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=t(lang, "install_happ"), url=HAPP_URL),
                InlineKeyboardButton(text=t(lang, "install_v2rayng"), url=V2RAYNG_URL),
            ],
            [InlineKeyboardButton(text=t(lang, "back"), callback_data="m:home")],
        ]
    )


def lang_inline(current: Lang) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=("✅ " if l.code == current else "") + f"{l.flag} {l.label}",
                callback_data=f"lang:{l.code}",
            )
        ]
        for l in LANGS
    ]
    rows.append([InlineKeyboardButton(text=t(current, "back"), callback_data="m:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def stars_plans_keyboard(plans: list[dict], lang: Lang) -> InlineKeyboardMarkup:
    """Legacy /stars command list (kept for the standalone command)."""
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
