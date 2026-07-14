"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { getTg } from "@/lib/telegram";

export type Lang = "uz" | "ru" | "en";
export const LANGS: { code: Lang; label: string; flag: string }[] = [
  { code: "uz", label: "O'zbek", flag: "🇺🇿" },
  { code: "ru", label: "Русский", flag: "🇷🇺" },
  { code: "en", label: "English", flag: "🇬🇧" },
];

type Dict = Record<string, string>;

const uz: Dict = {
  welcome: "Xush kelibsiz 👋",
  guest: "Mehmon",
  premium: "◆ PREMIUM",
  free: "FREE",
  subscription: "Obuna",
  active: "● FAOL",
  expired: "● TUGAGAN",
  none: "● YO'Q",
  days: "kun",
  until: "gacha",
  no_sub_home: "Faol obuna yo'q — tarif tanlab VPN'ni bir daqiqada ulang.",
  orb_connect_1: "VPN'ni",
  orb_connect_2: "ulash",
  orb_buy_1: "Tarif",
  orb_buy_2: "olish",
  hint_connect: "Ulanish uchun bosing",
  hint_choose: "Boshlash uchun tarif tanlang",
  net_quality: "Tarmoq sifati",
  excellent: "A'lo",
  devices: "Qurilmalar",
  up_to: "tagacha",
  server_locations: "Server lokatsiyalari",
  view_all_servers: "Barcha serverlarni ko'rish",

  plans_title: "Tariflar",
  plans_sub_card: "Karta (Sber, Mir, СБП) yoki Telegram Stars.",
  plans_sub_stars: "Telegram Stars orqali.",
  plans_sub_tail: "To'lovdan so'ng obuna avtomatik faollashadi.",
  your_balance: "Balansingiz",
  popular: "★ ENG MASHHUR",
  traffic: "trafik",
  unlimited: "Cheksiz",
  pay_card: "Karta",
  pay_stars: "Stars",
  pay_balance: "Balansdan",
  opening: "Ochilmoqda…",
  paying: "To'lanmoqda…",
  buy_balance_confirm: "tarifini balansdan sotib olasizmi?",

  profile_title: "Profil",
  remaining: "Qolgan",
  plan: "Tarif",
  valid: "Amal qiladi",
  no_active_sub: "Faol obuna yo'q.",
  invite_title: "Do'stlarni taklif qiling",
  invite_desc: "Do'stingiz birinchi obunasini sotib olsa — sizga bonus kunlar.",
  copy_link: "📋 Havolani nusxalash",
  copied: "✓ Nusxalandi",
  renew: "♻️ Obunani uzaytirish",
  renewing: "Invoice yaratilmoqda…",
  reconnect: "🚀 VPN'ni qayta ulash",
  buy_plan: "💎 Tarif sotib olish",
  language: "Til",

  servers_title: "Serverlar",
  servers_sub: "Global tezkor tarmoq",
  online: "Onlayn",
  maintenance: "Texnik ishlar",
  offline: "O'chiq",
  servers_footer: "Obunangiz barcha onlayn serverlarni o'z ichiga oladi — ilovada istalganini tanlang.",
  no_servers: "Serverlar hali qo'shilmagan.",

  connect_title: "VPN'ni ulash",
  connect_sub: "Obunangiz faol — ilovaga ulang",
  your_device: "📱 Sizning qurilmangiz",
  device_hint: "uchun ilovani o'rnating, so'ng «Import» bosing (yoki URL'ni nusxalab ilovaga qo'ying).",
  install: "O'rnatish",
  import: "Import",
  url_copy: "URL nusxa",
  universal_url: "1. Universal URL",
  universal_desc: "Har qanday kliyentda ishlaydi: Happ, v2rayNG, Streisand, sing-box.",
  copy_url: "📋 URL'ni nusxalash",
  qr_title: "2. QR kod",
  qr_desc: "Kliyent ilovasida QR orqali import qiling",
  one_tap: "3. Bir bosishda ochish",
  uploaded: "⬆️ Yuklangan",
  downloaded: "⬇️ Yuklab olingan",
  no_sub_title: "Faol obuna yo'q",
  no_sub_desc: "VPN'ni ulash uchun avval tarif sotib oling.",
  view_plans: "💎 Tariflarni ko'rish",

  pay_verifying: "To'lov tasdiqlanmoqda…",
  pay_verifying_desc: "Odatda bir necha soniya. Obuna tasdiqlangach avtomatik faollashadi.",
  pay_activated: "Obuna faollashtirildi!",
  pay_activated_desc: "Endi VPN'ni istalgan qurilmaga ulashingiz mumkin.",
  pay_connect: "🚀 VPN'ni ulash",
  pay_back_home: "Asosiyga qaytish",
  pay_slow: "To'lov hali tasdiqlanmadi",
  pay_slow_desc: "Tarmoq tasdiqlashi kechikishi mumkin. Bir necha daqiqadan so'ng profilni tekshiring.",
  pay_go_profile: "👤 Profilga o'tish",
};

const ru: Dict = {
  welcome: "Добро пожаловать 👋",
  guest: "Гость",
  premium: "◆ PREMIUM",
  free: "FREE",
  subscription: "Подписка",
  active: "● АКТИВНА",
  expired: "● ИСТЕКЛА",
  none: "● НЕТ",
  days: "дней",
  until: "до",
  no_sub_home: "Нет активной подписки — выберите тариф и подключите VPN за минуту.",
  orb_connect_1: "Подключить",
  orb_connect_2: "VPN",
  orb_buy_1: "Купить",
  orb_buy_2: "тариф",
  hint_connect: "Нажмите для подключения",
  hint_choose: "Выберите тариф, чтобы начать",
  net_quality: "Качество сети",
  excellent: "Отлично",
  devices: "Устройства",
  up_to: "до",
  server_locations: "Локации серверов",
  view_all_servers: "Посмотреть все серверы",

  plans_title: "Тарифы",
  plans_sub_card: "Карта (Sber, Mir, СБП) или Telegram Stars.",
  plans_sub_stars: "Через Telegram Stars.",
  plans_sub_tail: "После оплаты подписка активируется автоматически.",
  your_balance: "Ваш баланс",
  popular: "★ ПОПУЛЯРНЫЙ",
  traffic: "трафик",
  unlimited: "Безлимит",
  pay_card: "Картой",
  pay_stars: "Stars",
  pay_balance: "С баланса",
  opening: "Открываем…",
  paying: "Оплата…",
  buy_balance_confirm: "— купить с баланса?",

  profile_title: "Профиль",
  remaining: "Осталось",
  plan: "Тариф",
  valid: "Действует",
  no_active_sub: "Нет активной подписки.",
  invite_title: "Пригласите друзей",
  invite_desc: "Друг купит первую подписку — вам бонусные дни.",
  copy_link: "📋 Скопировать ссылку",
  copied: "✓ Скопировано",
  renew: "♻️ Продлить подписку",
  renewing: "Создаём счёт…",
  reconnect: "🚀 Переподключить VPN",
  buy_plan: "💎 Купить тариф",
  language: "Язык",

  servers_title: "Серверы",
  servers_sub: "Глобальная быстрая сеть",
  online: "Онлайн",
  maintenance: "Тех. работы",
  offline: "Выключен",
  servers_footer: "Ваша подписка включает все онлайн-серверы — выберите любой в приложении.",
  no_servers: "Серверы пока не добавлены.",

  connect_title: "Подключить VPN",
  connect_sub: "Подписка активна — подключите приложение",
  your_device: "📱 Ваше устройство",
  device_hint: "— установите приложение, затем нажмите «Импорт» (или скопируйте URL в приложение).",
  install: "Установить",
  import: "Импорт",
  url_copy: "Копир. URL",
  universal_url: "1. Универсальный URL",
  universal_desc: "Работает в любом клиенте: Happ, v2rayNG, Streisand, sing-box.",
  copy_url: "📋 Скопировать URL",
  qr_title: "2. QR-код",
  qr_desc: "Импортируйте по QR в клиентском приложении",
  one_tap: "3. Открыть в один тап",
  uploaded: "⬆️ Отправлено",
  downloaded: "⬇️ Загружено",
  no_sub_title: "Нет активной подписки",
  no_sub_desc: "Чтобы подключить VPN, сначала купите тариф.",
  view_plans: "💎 Посмотреть тарифы",

  pay_verifying: "Проверяем оплату…",
  pay_verifying_desc: "Обычно несколько секунд. После подтверждения подписка активируется.",
  pay_activated: "Подписка активирована!",
  pay_activated_desc: "Теперь можно подключить VPN на любом устройстве.",
  pay_connect: "🚀 Подключить VPN",
  pay_back_home: "На главную",
  pay_slow: "Оплата ещё не подтверждена",
  pay_slow_desc: "Подтверждение сети может занять время. Проверьте профиль через пару минут.",
  pay_go_profile: "👤 Перейти в профиль",
};

const en: Dict = {
  welcome: "Welcome 👋",
  guest: "Guest",
  premium: "◆ PREMIUM",
  free: "FREE",
  subscription: "Subscription",
  active: "● ACTIVE",
  expired: "● EXPIRED",
  none: "● NONE",
  days: "days",
  until: "until",
  no_sub_home: "No active plan — pick one and connect the VPN in a minute.",
  orb_connect_1: "Connect",
  orb_connect_2: "VPN",
  orb_buy_1: "Get a",
  orb_buy_2: "plan",
  hint_connect: "Tap to connect",
  hint_choose: "Choose a plan to start",
  net_quality: "Network quality",
  excellent: "Excellent",
  devices: "Devices",
  up_to: "up to",
  server_locations: "Server locations",
  view_all_servers: "View all servers",

  plans_title: "Plans",
  plans_sub_card: "Card (Sber, Mir, SBP) or Telegram Stars.",
  plans_sub_stars: "Via Telegram Stars.",
  plans_sub_tail: "Your subscription activates automatically after payment.",
  your_balance: "Your balance",
  popular: "★ MOST POPULAR",
  traffic: "traffic",
  unlimited: "Unlimited",
  pay_card: "Card",
  pay_stars: "Stars",
  pay_balance: "Balance",
  opening: "Opening…",
  paying: "Paying…",
  buy_balance_confirm: "— buy from balance?",

  profile_title: "Profile",
  remaining: "Remaining",
  plan: "Plan",
  valid: "Valid",
  no_active_sub: "No active subscription.",
  invite_title: "Invite friends",
  invite_desc: "When a friend buys their first plan — you get bonus days.",
  copy_link: "📋 Copy link",
  copied: "✓ Copied",
  renew: "♻️ Renew subscription",
  renewing: "Creating invoice…",
  reconnect: "🚀 Reconnect VPN",
  buy_plan: "💎 Buy a plan",
  language: "Language",

  servers_title: "Servers",
  servers_sub: "Global high-speed network",
  online: "Online",
  maintenance: "Maintenance",
  offline: "Offline",
  servers_footer: "Your subscription includes every online server — pick any in the client app.",
  no_servers: "No servers added yet.",

  connect_title: "Connect VPN",
  connect_sub: "Subscription active — connect your app",
  your_device: "📱 Your device",
  device_hint: "— install the app, then tap “Import” (or copy the URL into the app).",
  install: "Install",
  import: "Import",
  url_copy: "Copy URL",
  universal_url: "1. Universal URL",
  universal_desc: "Works in any client: Happ, v2rayNG, Streisand, sing-box.",
  copy_url: "📋 Copy URL",
  qr_title: "2. QR code",
  qr_desc: "Import via QR in the client app",
  one_tap: "3. One-tap open",
  uploaded: "⬆️ Uploaded",
  downloaded: "⬇️ Downloaded",
  no_sub_title: "No active subscription",
  no_sub_desc: "Buy a plan first to connect the VPN.",
  view_plans: "💎 View plans",

  pay_verifying: "Verifying payment…",
  pay_verifying_desc: "Usually a few seconds. Your subscription activates once confirmed.",
  pay_activated: "Subscription activated!",
  pay_activated_desc: "You can now connect the VPN on any device.",
  pay_connect: "🚀 Connect VPN",
  pay_back_home: "Back home",
  pay_slow: "Payment not confirmed yet",
  pay_slow_desc: "Network confirmation can take a moment. Check your profile in a few minutes.",
  pay_go_profile: "👤 Go to profile",
};

const DICTS: Record<Lang, Dict> = { uz, ru, en };

function detectLang(): Lang {
  if (typeof window === "undefined") return "uz";
  const saved = localStorage.getItem("lang") as Lang | null;
  if (saved && DICTS[saved]) return saved;
  const tg = getTg()?.initDataUnsafe?.user as { language_code?: string } | undefined;
  const code = (tg?.language_code || navigator.language || "").slice(0, 2);
  if (code === "ru") return "ru";
  if (code === "en") return "en";
  if (code === "uz") return "uz";
  return "uz";
}

interface Ctx {
  lang: Lang;
  setLang: (l: Lang) => void;
  t: (key: keyof typeof uz) => string;
}
const I18nContext = createContext<Ctx>({ lang: "uz", setLang: () => {}, t: (k) => uz[k] ?? String(k) });

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("uz");
  useEffect(() => setLangState(detectLang()), []);
  const setLang = (l: Lang) => {
    setLangState(l);
    if (typeof window !== "undefined") localStorage.setItem("lang", l);
  };
  const t = (key: keyof typeof uz) => DICTS[lang][key] ?? uz[key] ?? String(key);
  return <I18nContext.Provider value={{ lang, setLang, t }}>{children}</I18nContext.Provider>;
}

export const useI18n = () => useContext(I18nContext);

export function LangSwitch({ compact = false }: { compact?: boolean }) {
  const { lang, setLang } = useI18n();
  return (
    <div className={`flex gap-1 ${compact ? "" : "w-full"}`}>
      {LANGS.map((l) => (
        <button
          key={l.code}
          onClick={() => setLang(l.code)}
          className={`flex items-center justify-center gap-1 rounded-xl transition ${
            compact ? "px-2 py-1 text-sm" : "flex-1 py-2.5 text-sm"
          } ${
            lang === l.code
              ? "bg-gradient-to-r from-primary/30 to-secondary/25 border border-white/15 text-txt"
              : "bg-white/[0.04] border border-transparent text-muted"
          }`}
        >
          <span>{l.flag}</span>
          {!compact && <span className="font-medium">{l.label}</span>}
        </button>
      ))}
    </div>
  );
}
