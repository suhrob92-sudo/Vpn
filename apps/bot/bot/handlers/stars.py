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
from bot.keyboards import stars_plans_keyboard

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("stars"))
async def cmd_stars(message: Message) -> None:
    plans = await api_client.get_plans()
    xtr = [p for p in plans if p["currency"] == "XTR"]
    if not xtr:
        await message.answer(
            "⭐ Hozircha Stars bilan to'lanadigan tariflar yo'q.\n"
            "💎 Tariflar bo'limidan kripto orqali to'lashingiz mumkin."
        )
        return
    await message.answer(
        "⭐ <b>Telegram Stars bilan to'lash</b>\nTarifni tanlang:",
        reply_markup=stars_plans_keyboard(xtr),
    )


@router.callback_query(F.data.startswith("stars:"))
async def stars_invoice(callback: CallbackQuery) -> None:
    plan_id = int(callback.data.split(":", 1)[1])
    plans = {p["id"]: p for p in await api_client.get_plans()}
    plan = plans.get(plan_id)
    if plan is None or plan["currency"] != "XTR":
        await callback.answer("Tarif topilmadi", show_alert=True)
        return
    await callback.message.answer_invoice(
        title=f"VPN — {plan['name']}",
        description=plan.get("description") or f"{plan['duration_days']} kunlik VPN obuna",
        payload=f"plan:{plan_id}",
        currency="XTR",
        prices=[LabeledPrice(label=plan["name"], amount=int(float(plan["price"])))],
    )
    await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery) -> None:
    plans = {p["id"]: p for p in await api_client.get_plans()}
    try:
        plan_id = int(query.invoice_payload.split(":", 1)[1])
    except (ValueError, IndexError):
        await query.answer(ok=False, error_message="Noto'g'ri to'lov ma'lumoti")
        return
    if plan_id not in plans:
        await query.answer(ok=False, error_message="Tarif endi mavjud emas")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
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
        await message.answer(
            "⚠️ To'lov qabul qilindi, lekin faollashtirishda xatolik yuz berdi. "
            "Bir necha daqiqada avtomatik hal bo'ladi; bo'lmasa yordamga yozing."
        )
        return
    await message.answer(
        "✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
        "Obunangiz faollashtirildi. «🚀 VPN'ni ulash» tugmasi orqali ulaning.",
    )
