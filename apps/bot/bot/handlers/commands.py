"""Core bot commands and menu buttons."""
import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message

from bot import api_client
from bot.config import get_settings
from bot.keyboards import main_menu, open_app_button

logger = logging.getLogger(__name__)
router = Router()

COUNTRY_FLAGS = {"DE": "🇩🇪", "NL": "🇳🇱", "FI": "🇫🇮", "US": "🇺🇸", "TR": "🇹🇷"}
STATUS_ICONS = {"ONLINE": "🟢", "MAINTENANCE": "🟡", "OFFLINE": "🔴"}


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
    # /start <referral_code> — deep-link referral tracking (reward logic post-MVP)
    start_param = command.args if command and command.args else None
    try:
        await api_client.upsert_user(_tg_user_dict(message), start_param)
    except Exception:
        logger.exception("upsert on /start failed")
        await message.answer("⚠️ Xizmat vaqtincha ishlamayapti. Birozdan so'ng urinib ko'ring.")
        return

    await message.answer(
        f"Salom, <b>{message.from_user.first_name}</b>! 👋\n\n"
        "🔐 Tezkor va xavfsiz VPN xizmatiga xush kelibsiz.\n\n"
        "• 🚀 <b>VPN'ni ulash</b> — obunangizni istalgan kliyentga ulang\n"
        "• 💎 <b>Tariflar</b> — obuna sotib olish yoki uzaytirish\n"
        "• 👤 <b>Profil</b> — obuna holati va qolgan kunlar\n\n"
        "Boshlash uchun quyidagi menyudan foydalaning 👇",
        reply_markup=main_menu(),
    )


# Reply-keyboard web_app buttons don't pass initData on some Telegram builds,
# so the menu buttons are plain text and we hand out inline web_app buttons here.
@router.message(F.text == "🚀 VPN'ni ulash")
async def btn_connect(message: Message) -> None:
    await message.answer(
        "🚀 <b>VPN'ni ulash</b>\n\n"
        "Quyidagi tugma orqali Mini App'ni oching — subscription URL, QR kod va "
        "qurilmangiz uchun ilovalar ro'yxati o'sha yerda.",
        reply_markup=open_app_button("🚀 VPN'ni ulash", "/connect"),
    )


@router.message(F.text == "💎 Tariflar")
async def btn_plans(message: Message) -> None:
    await message.answer(
        "💎 <b>Tariflar</b>\n\n"
        "Tarifni tanlab, Telegram Stars yoki bank kartasi bilan to'lang.",
        reply_markup=open_app_button("💎 Tariflarni ochish", "/plans"),
    )


@router.message(Command("help"))
@router.message(F.text == "🆘 Yordam")
async def cmd_help(message: Message) -> None:
    support = get_settings().support_contact
    await message.answer(
        "🆘 <b>Yordam</b>\n\n"
        "1️⃣ Tarif sotib oling («💎 Tariflar»)\n"
        "2️⃣ «🚀 VPN'ni ulash» orqali subscription URL yoki QR kodni oling\n"
        "3️⃣ Happ, v2rayNG, Streisand yoki sing-box kliyentiga qo'shing\n\n"
        "Buyruqlar: /start /help /profile /subscription /servers /support\n\n"
        f"Savollar bo'lsa: {support}"
    )


@router.message(Command("support"))
async def cmd_support(message: Message) -> None:
    await message.answer(
        f"🆘 Qo'llab-quvvatlash: {get_settings().support_contact}\n"
        "Murojaatingizga imkon qadar tez javob beramiz."
    )


@router.message(Command("profile"))
@router.message(F.text == "👤 Profil")
async def cmd_profile(message: Message) -> None:
    profile = await _load_profile(message)
    if profile is None:
        return
    user = profile["user"]
    sub = profile.get("subscription")
    lines = [
        "👤 <b>Profil</b>\n",
        f"Ism: {user.get('first_name') or '—'}",
        f"Username: @{user['username']}" if user.get("username") else "Username: —",
    ]
    if sub and sub["status"] == "ACTIVE":
        plan = sub["plan"]
        lines += [
            "",
            f"💎 Tarif: <b>{plan['name']}</b>",
            f"Holat: ✅ FAOL — {profile['days_left']} kun qoldi",
            f"Tugash sanasi: {sub['expires_at'][:10]}",
            f"Qurilmalar (tavsiya): {plan['device_hint']} tagacha",
        ]
    else:
        lines += ["", "Holat: ❌ Faol obuna yo'q"]
    await message.answer("\n".join(lines), reply_markup=open_app_button("👤 Profilni ochish", "/profile"))


@router.message(Command("subscription"))
async def cmd_subscription(message: Message) -> None:
    profile = await _load_profile(message)
    if profile is None:
        return
    sub = profile.get("subscription")
    if sub and sub["status"] == "ACTIVE":
        await message.answer(
            f"💎 <b>{sub['plan']['name']}</b> — ✅ faol\n"
            f"⏳ Qolgan: <b>{profile['days_left']} kun</b> (tugaydi {sub['expires_at'][:10]})\n\n"
            "🔗 Ulanish uchun Mini App'dagi «VPN'ni ulash» ekranidan URL yoki QR kodni oling.",
            reply_markup=open_app_button("🚀 VPN'ni ulash", "/connect"),
        )
    else:
        await message.answer(
            "❌ Faol obuna yo'q.\n💎 Tarif tanlab, VPN'ni bir daqiqada ulang!",
            reply_markup=open_app_button("💎 Tariflarni ko'rish", "/plans"),
        )


@router.message(Command("invite"))
async def cmd_invite(message: Message) -> None:
    profile = await _load_profile(message)
    if profile is None:
        return
    me = await message.bot.get_me()
    link = f"https://t.me/{me.username}?start={profile['user']['referral_code']}"
    await message.answer(
        "🎁 <b>Do'stlaringizni taklif qiling!</b>\n\n"
        "Taklif qilgan do'stingiz birinchi marta obuna sotib olsa, "
        "sizga bonus kunlar qo'shiladi.\n\n"
        f"Shaxsiy havolangiz:\n<code>{link}</code>"
    )


@router.message(Command("servers"))
@router.message(F.text == "🌍 Serverlar")
async def cmd_servers(message: Message) -> None:
    try:
        servers = await api_client.get_servers()
    except Exception:
        logger.exception("servers fetch failed")
        await message.answer("⚠️ Server ro'yxatini olishda xatolik.")
        return
    if not servers:
        await message.answer("Hozircha serverlar qo'shilmagan.")
        return
    lines = ["🌍 <b>Serverlar</b>\n"]
    for s in servers:
        flag = COUNTRY_FLAGS.get(s["country"], "🌐")
        icon = STATUS_ICONS.get(s["status"], "⚪")
        city = f", {s['city']}" if s.get("city") else ""
        lines.append(f"{flag} {s['country']}{city} — {icon} {s['status']}")
    await message.answer("\n".join(lines))


async def _load_profile(message: Message) -> dict | None:
    try:
        profile = await api_client.get_profile(message.from_user.id)
    except Exception:
        logger.exception("profile fetch failed")
        await message.answer("⚠️ Ma'lumotlarni olishda xatolik. Keyinroq urinib ko'ring.")
        return None
    if profile is None:
        await message.answer("Avval /start buyrug'ini yuboring.")
        return None
    return profile
