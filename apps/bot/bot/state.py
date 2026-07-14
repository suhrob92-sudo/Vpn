"""Shared in-process state for the bot (single polling process)."""
from bot.i18n import Lang, lang_of

# telegram_id -> chosen language; seeded on /start, updated on language switch.
LANG_CACHE: dict[int, Lang] = {}


def resolve_lang(tg_id: int, tg_code: str | None) -> Lang:
    return LANG_CACHE.get(tg_id) or lang_of(tg_code)
