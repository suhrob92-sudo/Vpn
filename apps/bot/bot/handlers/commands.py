"""Core bot commands and menu buttons."""
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from bot import api_client
from bot.config import get_settings
from bot.i18n import Lang, lang_of, t, variants
from bot.keyboards import main_menu, open_app_button

logger = logging.getLogger(__name__)
router = Router()

COUNTRY_FLAGS = {
    "DE": "🇩🇪", "NL": "🇳🇱", "FI": "🇫🇮", "US": "🇺🇸", "TR": "🇹🇷",
    "AT": "🇦🇹", "SE": "🇸🇪", "GB": "🇬🇧", "FR": "🇫🇷", "PL": "🇵🇱",
}
STATUS_ICONS = {"ONLINE": "🟢", "MAINTENANCE": "🟡", "OFFLINE": "🔴"}


def _lang(message: Message) -> Lang:
    return lang_of(message.from_user.language_code if message.from_user else None)


def _tg_user_dict(message: Message) -> dict:
    u = message.from_user
    return {
        "id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "language_code": u.language_code,
    }


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    lang = _lang(message)
    start_param = command.args if command and command.args else None
    try:
        await api_client.upsert_user(_tg_user_dict(message), start_param)
    except Exception:
        logger.exception("upsert on /start failed")
        await message.answer(t(lang, "service_down"))
        return

    await message.answer(
        t(lang, "greeting", name=message.from_user.first_name),
        reply_markup=main_menu(lang),
    )


@router.message(Command("help"))
@router.message(F.text.in_(variants("btn_help")))
async def cmd_help(message: Message) -> None:
    lang = _lang(message)
    await message.answer(t(lang, "help_msg", support=get_settings().support_contact))


@router.message(F.text.in_(variants("btn_connect")))
async def btn_connect(message: Message) -> None:
    lang = _lang(message)
    await message.answer(
        t(lang, "connect_msg"),
        reply_markup=open_app_button(t(lang, "connect_btn"), "/connect"),
    )


@router.message(F.text.in_(variants("btn_plans")))
async def btn_plans(message: Message) -> None:
    lang = _lang(message)
    await message.answer(
        t(lang, "plans_msg"),
        reply_markup=open_app_button(t(lang, "plans_btn"), "/plans"),
    )


@router.message(Command("support"))
async def cmd_support(message: Message) -> None:
    lang = _lang(message)
    await message.answer(t(lang, "support_msg", support=get_settings().support_contact))


@router.message(Command("profile"))
@router.message(F.text.in_(variants("btn_profile")))
async def cmd_profile(message: Message) -> None:
    lang = _lang(message)
    profile = await _load_profile(message, lang)
    if profile is None:
        return
    user = profile["user"]
    sub = profile.get("subscription")
    lines = [
        t(lang, "profile_title"),
        t(lang, "profile_name", name=user.get("first_name") or "—"),
        t(lang, "profile_username", username=user["username"])
        if user.get("username")
        else t(lang, "profile_username_none"),
    ]
    if sub and sub["status"] == "ACTIVE":
        plan = sub["plan"]
        lines += [
            "",
            t(lang, "profile_plan", plan=plan["name"]),
            t(lang, "profile_status_active", days=profile["days_left"]),
            t(lang, "profile_expires", date=sub["expires_at"][:10]),
            t(lang, "profile_devices", n=plan["device_hint"]),
        ]
    else:
        lines += ["", t(lang, "profile_no_sub")]
    await message.answer(
        "\n".join(lines),
        reply_markup=open_app_button(t(lang, "profile_open_btn"), "/profile"),
    )


@router.message(Command("subscription"))
async def cmd_subscription(message: Message) -> None:
    lang = _lang(message)
    profile = await _load_profile(message, lang)
    if profile is None:
        return
    sub = profile.get("subscription")
    if sub and sub["status"] == "ACTIVE":
        await message.answer(
            t(lang, "sub_active", plan=sub["plan"]["name"], days=profile["days_left"], date=sub["expires_at"][:10]),
            reply_markup=open_app_button(t(lang, "sub_connect_btn"), "/connect"),
        )
    else:
        await message.answer(
            t(lang, "sub_none"),
            reply_markup=open_app_button(t(lang, "sub_plans_btn"), "/plans"),
        )


@router.message(Command("invite"))
async def cmd_invite(message: Message) -> None:
    lang = _lang(message)
    profile = await _load_profile(message, lang)
    if profile is None:
        return
    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start={profile['user']['referral_code']}"
    await message.answer(t(lang, "invite_msg", link=link))


@router.message(Command("servers"))
@router.message(F.text.in_(variants("btn_servers")))
async def cmd_servers(message: Message) -> None:
    lang = _lang(message)
    try:
        servers = await api_client.get_servers()
    except Exception:
        logger.exception("servers fetch failed")
        await message.answer(t(lang, "servers_fetch_error"))
        return
    if not servers:
        await message.answer(t(lang, "servers_empty"))
        return
    lines = [t(lang, "servers_title")]
    for s in servers:
        flag = COUNTRY_FLAGS.get(s["country"], "🌐")
        icon = STATUS_ICONS.get(s["status"], "⚪")
        city = f", {s['city']}" if s.get("city") else ""
        lines.append(f"{flag} {s['country']}{city} — {icon} {s['status']}")
    await message.answer("\n".join(lines))


async def _load_profile(message: Message, lang: Lang) -> dict | None:
    try:
        profile = await api_client.get_profile(message.from_user.id)
    except Exception:
        logger.exception("profile fetch failed")
        await message.answer(t(lang, "data_error"))
        return None
    if profile is None:
        await message.answer(t(lang, "send_start"))
        return None
    return profile
