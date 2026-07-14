"""Fully in-bot, inline-driven UX: menu, plans, purchase, connect, profile,
servers, help and language — everything without leaving Telegram."""
import io
import logging

import qrcode
from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot import api_client
from bot.config import get_settings
from bot.i18n import Lang, lang_of, t
from bot.keyboards import (
    back_inline,
    connect_inline,
    lang_inline,
    main_menu_inline,
    plan_pay_inline,
    plans_inline,
)
from bot.state import LANG_CACHE, resolve_lang

logger = logging.getLogger(__name__)
router = Router()

COUNTRY_FLAGS = {
    "DE": "🇩🇪", "NL": "🇳🇱", "FI": "🇫🇮", "US": "🇺🇸", "TR": "🇹🇷",
    "AT": "🇦🇹", "SE": "🇸🇪", "GB": "🇬🇧", "FR": "🇫🇷", "PL": "🇵🇱",
}
STATUS_ICONS = {"ONLINE": "🟢", "MAINTENANCE": "🟡", "OFFLINE": "🔴"}


def _lang(tg_id: int, tg_code: str | None) -> Lang:
    return resolve_lang(tg_id, tg_code)


def _tg_user_dict(message: Message) -> dict:
    u = message.from_user
    return {
        "id": u.id,
        "username": u.username,
        "first_name": u.first_name,
        "last_name": u.last_name,
        "language_code": u.language_code,
    }


def _make_qr(data: str) -> bytes:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


async def _edit_or_send(cb: CallbackQuery, text: str, markup) -> None:
    """Navigate in place: edit the current text message, or (if it's a photo /
    can't be edited) delete it and send a fresh one."""
    try:
        await cb.message.edit_text(text, reply_markup=markup)
    except TelegramBadRequest:
        try:
            await cb.message.delete()
        except TelegramBadRequest:
            pass
        await cb.message.answer(text, reply_markup=markup)


# ── /start + core commands ───────────────────────────────────────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject) -> None:
    tg_id = message.from_user.id
    lang = _lang(tg_id, message.from_user.language_code)
    start_param = command.args if command and command.args else None
    try:
        user = await api_client.upsert_user(_tg_user_dict(message), start_param)
        if user and user.get("language_code"):
            lang = lang_of(user["language_code"])
            LANG_CACHE[tg_id] = lang
    except Exception:
        logger.exception("upsert on /start failed")
        await message.answer(t(lang, "service_down"))
        return
    await message.answer(t(lang, "menu_title"), reply_markup=main_menu_inline(lang))


@router.message(Command("menu"))
async def cmd_menu(message: Message) -> None:
    lang = _lang(message.from_user.id, message.from_user.language_code)
    await message.answer(t(lang, "menu_title"), reply_markup=main_menu_inline(lang))


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    lang = _lang(message.from_user.id, message.from_user.language_code)
    await message.answer(
        t(lang, "help_msg", support=get_settings().support_contact),
        reply_markup=back_inline(lang),
    )


@router.message(Command("support"))
async def cmd_support(message: Message) -> None:
    lang = _lang(message.from_user.id, message.from_user.language_code)
    await message.answer(t(lang, "support_msg", support=get_settings().support_contact))


# ── Inline menu navigation ───────────────────────────────────────────────────

@router.callback_query(F.data == "m:home")
async def nav_home(cb: CallbackQuery) -> None:
    lang = _lang(cb.from_user.id, cb.from_user.language_code)
    await _edit_or_send(cb, t(lang, "menu_title"), main_menu_inline(lang))
    await cb.answer()


@router.callback_query(F.data == "m:help")
async def nav_help(cb: CallbackQuery) -> None:
    lang = _lang(cb.from_user.id, cb.from_user.language_code)
    await _edit_or_send(cb, t(lang, "help_msg", support=get_settings().support_contact), back_inline(lang))
    await cb.answer()


@router.callback_query(F.data == "m:lang")
async def nav_lang(cb: CallbackQuery) -> None:
    lang = _lang(cb.from_user.id, cb.from_user.language_code)
    await _edit_or_send(cb, t(lang, "lang_choose"), lang_inline(lang))
    await cb.answer()


@router.callback_query(F.data.startswith("lang:"))
async def set_lang(cb: CallbackQuery) -> None:
    new = cb.data.split(":", 1)[1]
    if new not in ("uz", "ru", "en"):
        await cb.answer()
        return
    LANG_CACHE[cb.from_user.id] = new
    try:
        await api_client.set_language(cb.from_user.id, new)
    except Exception:
        logger.exception("set_language failed")
    await cb.answer(t(new, "lang_saved"))
    await _edit_or_send(cb, t(new, "menu_title"), main_menu_inline(new))


@router.callback_query(F.data == "m:servers")
async def nav_servers(cb: CallbackQuery) -> None:
    lang = _lang(cb.from_user.id, cb.from_user.language_code)
    try:
        servers = await api_client.get_servers()
    except Exception:
        logger.exception("servers fetch failed")
        await cb.answer(t(lang, "servers_fetch_error"), show_alert=True)
        return
    if not servers:
        await _edit_or_send(cb, t(lang, "servers_empty"), back_inline(lang))
        await cb.answer()
        return
    lines = [t(lang, "servers_title")]
    for s in servers:
        flag = COUNTRY_FLAGS.get(s["country"], "🌐")
        icon = STATUS_ICONS.get(s["status"], "⚪")
        city = f", {s['city']}" if s.get("city") else ""
        lines.append(f"{flag} {s['country']}{city} — {icon} {s['status']}")
    await _edit_or_send(cb, "\n".join(lines), back_inline(lang))
    await cb.answer()


@router.callback_query(F.data == "m:profile")
@router.message(Command("profile"))
async def nav_profile(event) -> None:
    is_cb = isinstance(event, CallbackQuery)
    user_tg = event.from_user
    lang = _lang(user_tg.id, user_tg.language_code)
    profile = await _load_profile(event, lang)
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
    text = "\n".join(lines)
    if is_cb:
        await _edit_or_send(event, text, back_inline(lang))
        await event.answer()
    else:
        await event.answer(text, reply_markup=back_inline(lang))


@router.message(Command("servers"))
async def cmd_servers(message: Message) -> None:
    lang = _lang(message.from_user.id, message.from_user.language_code)
    try:
        servers = await api_client.get_servers()
    except Exception:
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
    await message.answer("\n".join(lines), reply_markup=back_inline(lang))


@router.message(Command("invite"))
async def cmd_invite(message: Message) -> None:
    lang = _lang(message.from_user.id, message.from_user.language_code)
    profile = await _load_profile(message, lang)
    if profile is None:
        return
    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start={profile['user']['referral_code']}"
    await message.answer(t(lang, "invite_msg", link=link), reply_markup=back_inline(lang))


# ── Plans + purchase ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "m:plans")
async def nav_plans(cb: CallbackQuery) -> None:
    lang = _lang(cb.from_user.id, cb.from_user.language_code)
    plans = await api_client.get_plans()
    if not plans:
        await cb.answer(t(lang, "connect_no_sub"), show_alert=True)
        return
    await _edit_or_send(cb, t(lang, "plans_pick"), plans_inline(plans, lang))
    await cb.answer()


@router.callback_query(F.data.startswith("buy:"))
async def buy_plan(cb: CallbackQuery) -> None:
    lang = _lang(cb.from_user.id, cb.from_user.language_code)
    plan_id = int(cb.data.split(":", 1)[1])
    plans = {p["id"]: p for p in await api_client.get_plans()}
    plan = plans.get(plan_id)
    if plan is None:
        await cb.answer(t(lang, "stars_not_found"), show_alert=True)
        return
    balance = 0.0
    try:
        profile = await api_client.get_profile(cb.from_user.id)
        balance = float((profile or {}).get("user", {}).get("balance", 0) or 0)
    except Exception:
        pass
    text = t(
        lang,
        "plan_card_title",
        name=plan["name"],
        desc=plan.get("description") or "",
        days=plan["duration_days"],
        devices=plan["device_hint"],
    )
    await _edit_or_send(cb, text, plan_pay_inline(plan, lang, balance))
    await cb.answer()


@router.callback_query(F.data.startswith("bal:"))
async def pay_balance(cb: CallbackQuery) -> None:
    lang = _lang(cb.from_user.id, cb.from_user.language_code)
    plan_id = int(cb.data.split(":", 1)[1])
    try:
        result = await api_client.buy_from_balance(cb.from_user.id, plan_id)
    except api_client.BackendError as exc:
        msg = "balance_insufficient" if "402" in str(exc) else "balance_error"
        await cb.answer(t(lang, msg), show_alert=True)
        return
    await cb.answer()
    await _edit_or_send(
        cb, t(lang, "balance_paid", plan=result.get("plan", "")), main_menu_inline(lang)
    )


# ── Connect (QR + URL, fully in-bot) ─────────────────────────────────────────

@router.callback_query(F.data == "m:connect")
async def nav_connect(cb: CallbackQuery) -> None:
    lang = _lang(cb.from_user.id, cb.from_user.language_code)
    info = await api_client.get_connect(cb.from_user.id)
    if info is None:
        await _edit_or_send(cb, t(lang, "connect_no_sub"), back_inline(lang))
        await cb.answer()
        return
    url = info["subscription_url"]
    qr = BufferedInputFile(_make_qr(url), filename="vpn-qr.png")
    try:
        await cb.message.delete()
    except TelegramBadRequest:
        pass
    await cb.message.answer_photo(
        qr,
        caption=t(lang, "connect_ready", url=url),
        reply_markup=connect_inline(lang),
    )
    await cb.answer()


async def _load_profile(event, lang: Lang) -> dict | None:
    answer = event.message.answer if isinstance(event, CallbackQuery) else event.answer
    try:
        profile = await api_client.get_profile(event.from_user.id)
    except Exception:
        logger.exception("profile fetch failed")
        await answer(t(lang, "data_error"))
        return None
    if profile is None:
        await answer(t(lang, "send_start"))
        return None
    return profile
