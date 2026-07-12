"""Lightweight 3-language (uz/ru/en) message catalogue for the bot.

Language is derived from the Telegram user's `language_code` on every update,
so no state is stored. Reply-keyboard buttons are localized; handlers match a
button by the set of all its translations (see `variants`).
"""
from __future__ import annotations

Lang = str
LANGS: tuple[Lang, ...] = ("uz", "ru", "en")

TR: dict[Lang, dict[str, str]] = {
    "uz": {
        "service_down": "⚠️ Xizmat vaqtincha ishlamayapti. Birozdan so'ng urinib ko'ring.",
        "data_error": "⚠️ Ma'lumotlarni olishda xatolik. Keyinroq urinib ko'ring.",
        "send_start": "Avval /start buyrug'ini yuboring.",
        # menu buttons
        "btn_connect": "🚀 VPN'ni ulash",
        "btn_plans": "💎 Tariflar",
        "btn_profile": "👤 Profil",
        "btn_servers": "🌍 Serverlar",
        "btn_help": "🆘 Yordam",
        # start
        "greeting": (
            "Salom, <b>{name}</b>! 👋\n\n"
            "🔐 Tezkor va xavfsiz VPN xizmatiga xush kelibsiz.\n\n"
            "• 🚀 <b>VPN'ni ulash</b> — obunangizni istalgan kliyentga ulang\n"
            "• 💎 <b>Tariflar</b> — obuna sotib olish yoki uzaytirish\n"
            "• 👤 <b>Profil</b> — obuna holati va qolgan kunlar\n\n"
            "Boshlash uchun quyidagi menyudan foydalaning 👇"
        ),
        "connect_msg": (
            "🚀 <b>VPN'ni ulash</b>\n\n"
            "Quyidagi tugma orqali Mini App'ni oching — subscription URL, QR kod va "
            "qurilmangiz uchun ilovalar ro'yxati o'sha yerda."
        ),
        "connect_btn": "🚀 VPN'ni ulash",
        "plans_msg": (
            "💎 <b>Tariflar</b>\n\nTarifni tanlab, Telegram Stars yoki bank kartasi bilan to'lang."
        ),
        "plans_btn": "💎 Tariflarni ochish",
        "help_msg": (
            "🆘 <b>Yordam</b>\n\n"
            "1️⃣ Tarif sotib oling («💎 Tariflar»)\n"
            "2️⃣ «🚀 VPN'ni ulash» orqali subscription URL yoki QR kodni oling\n"
            "3️⃣ Happ, v2rayNG, Streisand yoki sing-box kliyentiga qo'shing\n\n"
            "Buyruqlar: /start /help /profile /subscription /servers /support\n\n"
            "Savollar bo'lsa: {support}"
        ),
        "support_msg": (
            "🆘 Qo'llab-quvvatlash: {support}\nMurojaatingizga imkon qadar tez javob beramiz."
        ),
        "profile_title": "👤 <b>Profil</b>\n",
        "profile_name": "Ism: {name}",
        "profile_username": "Username: @{username}",
        "profile_username_none": "Username: —",
        "profile_plan": "💎 Tarif: <b>{plan}</b>",
        "profile_status_active": "Holat: ✅ FAOL — {days} kun qoldi",
        "profile_expires": "Tugash sanasi: {date}",
        "profile_devices": "Qurilmalar (tavsiya): {n} tagacha",
        "profile_no_sub": "Holat: ❌ Faol obuna yo'q",
        "profile_open_btn": "👤 Profilni ochish",
        "sub_active": (
            "💎 <b>{plan}</b> — ✅ faol\n"
            "⏳ Qolgan: <b>{days} kun</b> (tugaydi {date})\n\n"
            "🔗 Ulanish uchun Mini App'dagi «VPN'ni ulash» ekranidan URL yoki QR kodni oling."
        ),
        "sub_connect_btn": "🚀 VPN'ni ulash",
        "sub_none": "❌ Faol obuna yo'q.\n💎 Tarif tanlab, VPN'ni bir daqiqada ulang!",
        "sub_plans_btn": "💎 Tariflarni ko'rish",
        "invite_msg": (
            "🎁 <b>Do'stlaringizni taklif qiling!</b>\n\n"
            "Taklif qilgan do'stingiz birinchi marta obuna sotib olsa, "
            "sizga bonus kunlar qo'shiladi.\n\n"
            "Shaxsiy havolangiz:\n<code>{link}</code>"
        ),
        "servers_title": "🌍 <b>Serverlar</b>\n",
        "servers_fetch_error": "⚠️ Server ro'yxatini olishda xatolik.",
        "servers_empty": "Hozircha serverlar qo'shilmagan.",
        # stars
        "stars_none": (
            "⭐ Hozircha Stars bilan to'lanadigan tariflar yo'q.\n"
            "💎 Tariflar bo'limidan bank kartasi orqali to'lashingiz mumkin."
        ),
        "stars_choose": "⭐ <b>Telegram Stars bilan to'lash</b>\nTarifni tanlang:",
        "stars_plan_btn": "⭐ {name} — {stars} Stars",
        "stars_not_found": "Tarif topilmadi",
        "stars_bad_payload": "Noto'g'ri to'lov ma'lumoti",
        "stars_plan_gone": "Tarif endi mavjud emas",
        "stars_invoice_title": "VPN — {name}",
        "stars_invoice_desc": "{days} kunlik VPN obuna",
        "stars_paid": (
            "✅ <b>To'lov muvaffaqiyatli!</b>\n\n"
            "Obunangiz faollashtirildi. «🚀 VPN'ni ulash» tugmasi orqali ulaning."
        ),
        "stars_report_fail": (
            "⚠️ To'lov qabul qilindi, lekin faollashtirishda xatolik yuz berdi. "
            "Bir necha daqiqada avtomatik hal bo'ladi; bo'lmasa yordamga yozing."
        ),
    },
    "ru": {
        "service_down": "⚠️ Сервис временно недоступен. Попробуйте чуть позже.",
        "data_error": "⚠️ Ошибка при получении данных. Попробуйте позже.",
        "send_start": "Сначала отправьте команду /start.",
        "btn_connect": "🚀 Подключить VPN",
        "btn_plans": "💎 Тарифы",
        "btn_profile": "👤 Профиль",
        "btn_servers": "🌍 Серверы",
        "btn_help": "🆘 Помощь",
        "greeting": (
            "Привет, <b>{name}</b>! 👋\n\n"
            "🔐 Добро пожаловать в быстрый и безопасный VPN-сервис.\n\n"
            "• 🚀 <b>Подключить VPN</b> — подключите подписку в любом клиенте\n"
            "• 💎 <b>Тарифы</b> — купить или продлить подписку\n"
            "• 👤 <b>Профиль</b> — статус подписки и остаток дней\n\n"
            "Начните с меню ниже 👇"
        ),
        "connect_msg": (
            "🚀 <b>Подключить VPN</b>\n\n"
            "Откройте Mini App по кнопке ниже — там subscription URL, QR-код и "
            "список приложений для вашего устройства."
        ),
        "connect_btn": "🚀 Подключить VPN",
        "plans_msg": (
            "💎 <b>Тарифы</b>\n\nВыберите тариф и оплатите через Telegram Stars или банковской картой."
        ),
        "plans_btn": "💎 Открыть тарифы",
        "help_msg": (
            "🆘 <b>Помощь</b>\n\n"
            "1️⃣ Купите тариф («💎 Тарифы»)\n"
            "2️⃣ Через «🚀 Подключить VPN» получите subscription URL или QR-код\n"
            "3️⃣ Добавьте в клиент Happ, v2rayNG, Streisand или sing-box\n\n"
            "Команды: /start /help /profile /subscription /servers /support\n\n"
            "Вопросы: {support}"
        ),
        "support_msg": "🆘 Поддержка: {support}\nОтветим как можно быстрее.",
        "profile_title": "👤 <b>Профиль</b>\n",
        "profile_name": "Имя: {name}",
        "profile_username": "Username: @{username}",
        "profile_username_none": "Username: —",
        "profile_plan": "💎 Тариф: <b>{plan}</b>",
        "profile_status_active": "Статус: ✅ АКТИВНА — осталось {days} дней",
        "profile_expires": "Действует до: {date}",
        "profile_devices": "Устройства (реком.): до {n}",
        "profile_no_sub": "Статус: ❌ Нет активной подписки",
        "profile_open_btn": "👤 Открыть профиль",
        "sub_active": (
            "💎 <b>{plan}</b> — ✅ активна\n"
            "⏳ Осталось: <b>{days} дней</b> (до {date})\n\n"
            "🔗 Для подключения откройте экран «Подключить VPN» в Mini App и возьмите URL или QR-код."
        ),
        "sub_connect_btn": "🚀 Подключить VPN",
        "sub_none": "❌ Нет активной подписки.\n💎 Выберите тариф и подключите VPN за минуту!",
        "sub_plans_btn": "💎 Посмотреть тарифы",
        "invite_msg": (
            "🎁 <b>Пригласите друзей!</b>\n\n"
            "Когда приглашённый друг впервые купит подписку, вам начислятся бонусные дни.\n\n"
            "Ваша персональная ссылка:\n<code>{link}</code>"
        ),
        "servers_title": "🌍 <b>Серверы</b>\n",
        "servers_fetch_error": "⚠️ Не удалось получить список серверов.",
        "servers_empty": "Серверы пока не добавлены.",
        "stars_none": (
            "⭐ Пока нет тарифов, оплачиваемых через Stars.\n"
            "💎 Вы можете оплатить банковской картой в разделе «Тарифы»."
        ),
        "stars_choose": "⭐ <b>Оплата через Telegram Stars</b>\nВыберите тариф:",
        "stars_plan_btn": "⭐ {name} — {stars} Stars",
        "stars_not_found": "Тариф не найден",
        "stars_bad_payload": "Неверные данные платежа",
        "stars_plan_gone": "Тариф больше недоступен",
        "stars_invoice_title": "VPN — {name}",
        "stars_invoice_desc": "VPN-подписка на {days} дней",
        "stars_paid": (
            "✅ <b>Оплата успешна!</b>\n\n"
            "Подписка активирована. Подключитесь по кнопке «🚀 Подключить VPN»."
        ),
        "stars_report_fail": (
            "⚠️ Оплата принята, но при активации произошла ошибка. "
            "Обычно решается автоматически за пару минут; если нет — напишите в поддержку."
        ),
    },
    "en": {
        "service_down": "⚠️ Service is temporarily unavailable. Please try again shortly.",
        "data_error": "⚠️ Failed to load data. Please try again later.",
        "send_start": "Send /start first.",
        "btn_connect": "🚀 Connect VPN",
        "btn_plans": "💎 Plans",
        "btn_profile": "👤 Profile",
        "btn_servers": "🌍 Servers",
        "btn_help": "🆘 Help",
        "greeting": (
            "Hi, <b>{name}</b>! 👋\n\n"
            "🔐 Welcome to a fast and secure VPN service.\n\n"
            "• 🚀 <b>Connect VPN</b> — use your subscription in any client\n"
            "• 💎 <b>Plans</b> — buy or extend a subscription\n"
            "• 👤 <b>Profile</b> — subscription status and days left\n\n"
            "Use the menu below to get started 👇"
        ),
        "connect_msg": (
            "🚀 <b>Connect VPN</b>\n\n"
            "Open the Mini App with the button below — subscription URL, QR code and "
            "the app list for your device are all there."
        ),
        "connect_btn": "🚀 Connect VPN",
        "plans_msg": (
            "💎 <b>Plans</b>\n\nPick a plan and pay with Telegram Stars or a bank card."
        ),
        "plans_btn": "💎 Open plans",
        "help_msg": (
            "🆘 <b>Help</b>\n\n"
            "1️⃣ Buy a plan (“💎 Plans”)\n"
            "2️⃣ Get the subscription URL or QR via “🚀 Connect VPN”\n"
            "3️⃣ Add it to Happ, v2rayNG, Streisand or sing-box\n\n"
            "Commands: /start /help /profile /subscription /servers /support\n\n"
            "Questions: {support}"
        ),
        "support_msg": "🆘 Support: {support}\nWe'll reply as soon as possible.",
        "profile_title": "👤 <b>Profile</b>\n",
        "profile_name": "Name: {name}",
        "profile_username": "Username: @{username}",
        "profile_username_none": "Username: —",
        "profile_plan": "💎 Plan: <b>{plan}</b>",
        "profile_status_active": "Status: ✅ ACTIVE — {days} days left",
        "profile_expires": "Expires: {date}",
        "profile_devices": "Devices (rec.): up to {n}",
        "profile_no_sub": "Status: ❌ No active subscription",
        "profile_open_btn": "👤 Open profile",
        "sub_active": (
            "💎 <b>{plan}</b> — ✅ active\n"
            "⏳ Left: <b>{days} days</b> (until {date})\n\n"
            "🔗 To connect, open the “Connect VPN” screen in the Mini App and grab the URL or QR code."
        ),
        "sub_connect_btn": "🚀 Connect VPN",
        "sub_none": "❌ No active subscription.\n💎 Pick a plan and connect the VPN in a minute!",
        "sub_plans_btn": "💎 View plans",
        "invite_msg": (
            "🎁 <b>Invite your friends!</b>\n\n"
            "When an invited friend buys their first subscription, you get bonus days.\n\n"
            "Your personal link:\n<code>{link}</code>"
        ),
        "servers_title": "🌍 <b>Servers</b>\n",
        "servers_fetch_error": "⚠️ Failed to fetch the server list.",
        "servers_empty": "No servers added yet.",
        "stars_none": (
            "⭐ No Stars-payable plans yet.\n"
            "💎 You can pay by bank card in the Plans section."
        ),
        "stars_choose": "⭐ <b>Pay with Telegram Stars</b>\nChoose a plan:",
        "stars_plan_btn": "⭐ {name} — {stars} Stars",
        "stars_not_found": "Plan not found",
        "stars_bad_payload": "Invalid payment data",
        "stars_plan_gone": "Plan no longer available",
        "stars_invoice_title": "VPN — {name}",
        "stars_invoice_desc": "{days}-day VPN subscription",
        "stars_paid": (
            "✅ <b>Payment successful!</b>\n\n"
            "Your subscription is active. Connect via the “🚀 Connect VPN” button."
        ),
        "stars_report_fail": (
            "⚠️ Payment received, but activation failed. "
            "It usually resolves automatically within a few minutes; otherwise contact support."
        ),
    },
}


def lang_of(code: str | None) -> Lang:
    """Map a Telegram language_code to one of our supported languages."""
    c = (code or "").lower()
    if c.startswith("ru"):
        return "ru"
    if c.startswith("en"):
        return "en"
    return "uz"


def t(lang: Lang, key: str, **kw: object) -> str:
    text = TR.get(lang, TR["uz"]).get(key) or TR["uz"].get(key, key)
    return text.format(**kw) if kw else text


def variants(key: str) -> set[str]:
    """All translations of a button label, for language-agnostic F.text matching."""
    return {TR[l][key] for l in LANGS if key in TR[l]}
