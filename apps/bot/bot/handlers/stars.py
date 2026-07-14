"""Telegram Stars (XTR) payments — the alternative provider.

Only plans priced in XTR are payable here; CryptoBot purchases go through the
Mini App. `successful_payment` updates are authenticated by Telegram itself and
reported to the backend, which activates idempotently by charge id.
"""
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from bot import api_client
from bot.i18n import t
from bot.keyboards import stars_plans_keyboard
from bot.state import resolve_lang

logger = logging.getLogger(__name__)
router = Router()


def _lang(u) -> str:
    return resolve_lang(u.id, u.language_code) if u else "uz"


@router.message(Command("stars"))
async def cmd_stars(message: Message) -> None:
    lang = _lang(message.from_user)
    plans = await api_client.get_plans()
    payable = [p for p in plans if p.get("price_stars", 0) > 0]
    if not payable:
        await message.answer(t(lang, "stars_none"))
        return
    await message.answer(t(lang, "stars_choose"), reply_markup=stars_plans_keyboard(payable, lang))


@router.callback_query(F.data.startswith("stars:"))
async def stars_invoice(callback: CallbackQuery) -> None:
    lang = _lang(callback.from_user)
    plan_id = int(callback.data.split(":", 1)[1])
    plans = {p["id"]: p for p in await api_client.get_plans()}
    plan = plans.get(plan_id)
    if plan is None or plan.get("price_stars", 0) <= 0:
        await callback.answer(t(lang, "stars_not_found"), show_alert=True)
        return
    await callback.message.answer_invoice(
        title=t(lang, "stars_invoice_title", name=plan["name"]),
        description=plan.get("description")
        or t(lang, "stars_invoice_desc", days=plan["duration_days"]),
        payload=f"plan:{plan_id}",
        currency="XTR",
        prices=[LabeledPrice(label=plan["name"], amount=int(plan["price_stars"]))],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    lang = _lang(query.from_user)
    plans = {p["id"]: p for p in await api_client.get_plans()}
    try:
        plan_id = int(query.invoice_payload.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.answer(ok=False, error_message=t(lang, "stars_bad_payload"))
        return
    if plan_id not in plans:
        await query.answer(ok=False, error_message=t(lang, "stars_plan_gone"))
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    lang = _lang(message.from_user)
    sp = message.successful_payment
    plan_id = int(sp.invoice_payload.split(":", 1)[1])
    try:
        await api_client.report_stars_payment(
            telegram_id=message.from_user.id,
            plan_id=plan_id,
            charge_id=sp.telegram_payment_charge_id,
            amount=sp.total_amount,
        )
    except Exception:
        logger.exception("stars payment report failed (charge=%s)", sp.telegram_payment_charge_id)
        await message.answer(t(lang, "stars_report_fail"))
        return
    await message.answer(t(lang, "stars_paid"))
