"""
╔══════════════════════════════════════════════╗
║   🎮  TELEGRAM RPG BOT  — Хроники Заории    ║
║   Совместим с python-telegram-bot==21.10     ║
╚══════════════════════════════════════════════╝

УСТАНОВКА:
    pip install python-telegram-bot==21.10

ЗАПУСК:
    python telegram_rpg_bot.py

ПЕРЕМЕННАЯ ОКРУЖЕНИЯ (Railway / хостинг):
    BOT_TOKEN=ваш_токен
"""

import os
import random
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    PreCheckoutQueryHandler, MessageHandler, filters, ContextTypes
)

# ════════════════════════════════════════════════════════════
#  ⚙️  КОНФИГУРАЦИЯ
# ════════════════════════════════════════════════════════════
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════
#  💾  ХРАНИЛИЩЕ ИГРОКОВ
# ════════════════════════════════════════════════════════════
PLAYERS: dict[int, dict] = {}


def get_player(uid: int) -> dict:
    if uid not in PLAYERS:
        PLAYERS[uid] = {
            "name": "Герой",
            "hp": 100, "max_hp": 100,
            "attack": 12, "defense": 5,
            "gold": 60, "level": 1, "exp": 0,
            "location": "village",
            "inventory": [],
            "gems": 0,
            "kills": 0,
            "quests_done": 0,
            "current_fight": None,
        }
    return PLAYERS[uid]


def status_bar(p: dict) -> str:
    hp_pct = p["hp"] / p["max_hp"]
    filled = int(hp_pct * 10)
    bar = "█" * filled + "░" * (10 - filled)
    exp_needed = p["level"] * 100
    return (
        f"👤 *{p['name']}* — Уровень {p['level']}\n"
        f"❤️ [{bar}] {p['hp']}/{p['max_hp']}\n"
        f"⚔️ ATK: {p['attack']}  🛡 DEF: {p['defense']}\n"
        f"🪙 Золото: {p['gold']}  💎 Кристаллы: {p['gems']}\n"
        f"⭐ Опыт: {p['exp']}/{exp_needed}  💀 Убийств: {p['kills']}"
    )


# ════════════════════════════════════════════════════════════
#  👹  МОНСТРЫ
# ════════════════════════════════════════════════════════════
MONSTERS = {
    "rat":    {"name": "🐀 Гигантская крыса",  "hp": 20,  "attack": 5,  "defense": 1,  "gold": 8,   "exp": 10},
    "wolf":   {"name": "🐺 Серый волк",         "hp": 40,  "attack": 10, "defense": 3,  "gold": 20,  "exp": 30},
    "goblin": {"name": "👺 Гоблин-разбойник",   "hp": 35,  "attack": 8,  "defense": 4,  "gold": 25,  "exp": 25},
    "orc":    {"name": "👹 Орк-воин",           "hp": 70,  "attack": 16, "defense": 7,  "gold": 50,  "exp": 70},
    "troll":  {"name": "🧌 Болотный тролль",    "hp": 100, "attack": 20, "defense": 10, "gold": 80,  "exp": 100},
    "dragon": {"name": "🐉 Дракон Скорг",       "hp": 200, "attack": 35, "defense": 18, "gold": 300, "exp": 500},
}

LOCATION_MONSTERS = {
    "forest":  ["rat", "wolf", "goblin"],
    "swamp":   ["rat", "goblin", "troll"],
    "dungeon": ["orc", "troll"],
    "volcano": ["orc", "troll", "dragon"],
}

# ════════════════════════════════════════════════════════════
#  🏪  МАГАЗИН
# ════════════════════════════════════════════════════════════
SHOP_ITEMS = {
    "potion":     {"name": "🧪 Зелье здоровья",     "gold": 30,  "gems": 0, "type": "consumable", "effect": {"hp": 50},              "desc": "Восстанавливает 50 HP"},
    "big_potion": {"name": "💊 Большое зелье",       "gold": 70,  "gems": 0, "type": "consumable", "effect": {"hp": 120},             "desc": "Восстанавливает 120 HP"},
    "sword1":     {"name": "🗡 Железный меч",        "gold": 80,  "gems": 0, "type": "weapon",     "effect": {"attack": 5},           "desc": "+5 к атаке"},
    "sword2":     {"name": "⚔️ Стальной меч",        "gold": 180, "gems": 0, "type": "weapon",     "effect": {"attack": 12},          "desc": "+12 к атаке"},
    "shield1":    {"name": "🛡 Деревянный щит",      "gold": 60,  "gems": 0, "type": "armor",      "effect": {"defense": 4},          "desc": "+4 к защите"},
    "armor1":     {"name": "🪖 Кольчуга",            "gold": 150, "gems": 0, "type": "armor",      "effect": {"defense": 10},         "desc": "+10 к защите"},
    "gem_sword":  {"name": "💠 Магический клинок",   "gold": 0,   "gems": 5, "type": "weapon",     "effect": {"attack": 25},          "desc": "+25 к атаке | Только за 💎"},
    "gem_armor":  {"name": "🔮 Зачарованный доспех", "gold": 0,   "gems": 5, "type": "armor",      "effect": {"defense": 20},         "desc": "+20 к защите | Только за 💎"},
    "gem_elixir": {"name": "✨ Эликсир силы",        "gold": 0,   "gems": 3, "type": "consumable", "effect": {"attack": 5, "defense": 3, "max_hp": 30}, "desc": "+5 ATK, +3 DEF, +30 MaxHP | Только за 💎"},
}

# ════════════════════════════════════════════════════════════
#  🗺️  ЛОКАЦИИ
# ════════════════════════════════════════════════════════════
LOCATIONS = {
    "village": {"name": "🏘 Деревня Заря",      "desc": "Тихий посёлок у подножия гор. Здесь можно отдохнуть и снарядиться.",      "min_level": 1},
    "forest":  {"name": "🌲 Тёмный лес",        "desc": "Дремучий лес, полный волков и гоблинов. Опасно, но щедро на награды.",    "min_level": 1},
    "swamp":   {"name": "🌿 Гнилое болото",      "desc": "Туманное болото с кровожадными тварями. Нужно хорошее снаряжение.",       "min_level": 3},
    "dungeon": {"name": "🏰 Подземелье Черепа",  "desc": "Древнее подземелье с орками. Только для опытных героев.",                 "min_level": 5},
    "volcano": {"name": "🌋 Вулкан Смерти",      "desc": "Огненные пещеры — обитель дракона Скорга. Крайне опасно!",               "min_level": 8},
}


# ════════════════════════════════════════════════════════════
#  ⚔️  БОЕВАЯ СИСТЕМА
# ════════════════════════════════════════════════════════════
def simulate_fight(player: dict, monster_key: str) -> tuple[str, bool]:
    m = dict(MONSTERS[monster_key])
    m_hp = m["hp"]
    log_lines = [f"⚔️ *БИТВА: {player['name']} vs {m['name']}*", "─" * 28]
    round_n = 1

    while player["hp"] > 0 and m_hp > 0 and round_n <= 20:
        crit = random.random() < 0.15
        p_dmg = max(1, player["attack"] - m["defense"] + random.randint(-2, 5))
        if crit:
            p_dmg = int(p_dmg * 1.8)
        m_hp -= p_dmg
        crit_tag = " 💥*КРИТ!*" if crit else ""
        log_lines.append(f"Раунд {round_n}: Ты → {p_dmg} урона{crit_tag} | HP врага: {max(0, m_hp)}")

        if m_hp <= 0:
            break

        m_dmg = max(1, m["attack"] - player["defense"] + random.randint(-3, 4))
        player["hp"] = max(0, player["hp"] - m_dmg)
        log_lines.append(f"  {m['name']} → {m_dmg} урона | Твой HP: {player['hp']}")
        round_n += 1

    if player["hp"] > 0:
        gold_bonus = m["gold"] + random.randint(0, m["gold"] // 3)
        player["gold"] += gold_bonus
        player["exp"] += m["exp"]
        player["kills"] += 1

        lvl_msg = ""
        if player["exp"] >= player["level"] * 100:
            player["exp"] -= player["level"] * 100
            player["level"] += 1
            player["attack"] += 3
            player["defense"] += 1
            player["max_hp"] += 25
            player["hp"] = min(player["hp"] + 25, player["max_hp"])
            lvl_msg = f"\n\n🎉 *ПОВЫШЕНИЕ УРОВНЯ!* Теперь ты {player['level']} уровня!\n+3 ATK | +1 DEF | +25 MaxHP"

        log_lines.append(f"\n✅ *Победа!* +{gold_bonus} 🪙 золота, +{m['exp']} ⭐ опыта{lvl_msg}")
        return "\n".join(log_lines), True
    else:
        penalty = min(30, player["gold"])
        player["gold"] -= penalty
        player["hp"] = player["max_hp"] // 2
        log_lines.append(f"\n💀 *Ты пал в бою!* Потерял {penalty} 🪙 золота.\nВоскрешён с {player['hp']} HP.")
        return "\n".join(log_lines), False


# ════════════════════════════════════════════════════════════
#  🎛️  ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ════════════════════════════════════════════════════════════
def make_kb(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t, callback_data=d) for t, d in row]
        for row in rows
    ])


def village_kb() -> InlineKeyboardMarkup:
    return make_kb([
        [("⚔️ Идти в лес", "go_forest"), ("🏪 Магазин", "shop")],
        [("🏥 Таверна — отдохнуть (20🪙)", "heal")],
        [("🗺 Карта мира", "map"), ("📊 Профиль", "profile")],
        [("💎 Поддержать игру (Донат)", "donate_menu")],
        [("🏆 Таблица героев", "leaderboard")],
    ])


def location_kb() -> InlineKeyboardMarkup:
    return make_kb([
        [("⚔️ Атаковать монстра!", "fight"), ("🔍 Исследовать", "explore")],
        [("🗺 Карта мира", "map"), ("📊 Профиль", "profile")],
        [("🏘 Деревня", "go_village")],
    ])


# ════════════════════════════════════════════════════════════
#  📨  КОМАНДЫ
# ════════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    p = get_player(uid)
    p["name"] = update.effective_user.first_name or "Герой"
    text = (
        "╔═══════════════════════════╗\n"
        "║  ⚔️  ХРОНИКИ ЗАОРИИ  ⚔️  ║\n"
        "╚═══════════════════════════╝\n\n"
        f"Добро пожаловать, *{p['name']}*\\!\n\n"
        "Ты стоишь у ворот деревни Заря\\. Впереди — тёмные леса, "
        "болота и древние подземелья\\. Слава ждёт смельчаков\\!\n\n"
        + status_bar(p)
    )
    await update.message.reply_text(text, parse_mode="MarkdownV2", reply_markup=village_kb())


async def cmd_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    p = get_player(uid)
    loc = LOCATIONS[p["location"]]
    kb = village_kb() if p["location"] == "village" else location_kb()
    await update.message.reply_text(
        f"*{loc['name']}*\n\n{loc['desc']}\n\n{status_bar(p)}",
        parse_mode="Markdown", reply_markup=kb
    )


# ════════════════════════════════════════════════════════════
#  🎮  CALLBACK-ХЕНДЛЕР
# ════════════════════════════════════════════════════════════
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    p = get_player(uid)
    data = query.data

    if data == "main_menu":
        loc = LOCATIONS[p["location"]]
        kb = village_kb() if p["location"] == "village" else location_kb()
        await query.edit_message_text(
            f"*{loc['name']}*\n\n{loc['desc']}\n\n{status_bar(p)}",
            parse_mode="Markdown", reply_markup=kb
        )

    elif data == "profile":
        inv = ", ".join(p["inventory"]) if p["inventory"] else "пусто"
        await query.edit_message_text(
            f"📋 *ПРОФИЛЬ ГЕРОЯ*\n{'─'*28}\n\n{status_bar(p)}\n\n"
            f"🎒 Инвентарь: {inv}\n"
            f"🗺 Локация: {LOCATIONS[p['location']]['name']}\n"
            f"📜 Квестов: {p['quests_done']}",
            parse_mode="Markdown",
            reply_markup=make_kb([[("🔙 Меню", "main_menu")]])
        )

    elif data == "map":
        lines = []
        for lid, ldata in LOCATIONS.items():
            locked = p["level"] < ldata["min_level"]
            mark = "🔒" if locked else ("📍" if lid == p["location"] else "  ")
            lines.append(f"{mark} {ldata['name']}  \\(мин\\. ур\\. {ldata['min_level']}\\)")

        buttons = []
        for lid, ldata in LOCATIONS.items():
            if lid != p["location"] and p["level"] >= ldata["min_level"]:
                buttons.append([(f"➡️ {ldata['name']}", f"travel_{lid}")])
        buttons.append([("🔙 Назад", "main_menu")])

        await query.edit_message_text(
            "🗺 *КАРТА МИРА*\n\n" + "\n".join(lines) + "\n\n📍 \\= ты сейчас  🔒 \\= закрыто",
            parse_mode="MarkdownV2",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t, callback_data=d) for t, d in row]
                for row in buttons
            ])
        )

    elif data.startswith("travel_"):
        dest = data[7:]
        if dest not in LOCATIONS:
            await query.edit_message_text("❌ Неизвестная локация.", reply_markup=make_kb([[("🔙", "map")]]))
            return
        req = LOCATIONS[dest]["min_level"]
        if p["level"] < req:
            await query.edit_message_text(
                f"🔒 *Требуется {req} уровень\\!*\nТвой уровень: {p['level']}",
                parse_mode="MarkdownV2",
                reply_markup=make_kb([[("🗺 Карта", "map")]])
            )
            return
        p["location"] = dest
        loc = LOCATIONS[dest]
        await query.edit_message_text(
            f"✈️ Ты прибыл в *{loc['name']}*!\n\n{loc['desc']}\n\n{status_bar(p)}",
            parse_mode="Markdown",
            reply_markup=location_kb()
        )

    elif data == "go_village":
        p["location"] = "village"
        loc = LOCATIONS["village"]
        await query.edit_message_text(
            f"🏘 *{loc['name']}*\n\n{loc['desc']}\n\n{status_bar(p)}",
            parse_mode="Markdown", reply_markup=village_kb()
        )

    elif data == "go_forest":
        p["location"] = "forest"
        loc = LOCATIONS["forest"]
        await query.edit_message_text(
            f"🌲 *{loc['name']}*\n\n{loc['desc']}\n\n{status_bar(p)}",
            parse_mode="Markdown", reply_markup=location_kb()
        )

    elif data == "fight":
        loc = p["location"]
        if loc not in LOCATION_MONSTERS:
            await query.edit_message_text("⚠️ Здесь нет монстров.", reply_markup=make_kb([[("🔙", "main_menu")]]))
            return
        mk = random.choice(LOCATION_MONSTERS[loc])
        m = MONSTERS[mk]
        p["current_fight"] = mk
        await query.edit_message_text(
            f"👁 *Появился {m['name']}!*\n\n"
            f"❤️ HP: {m['hp']}  ⚔️ ATK: {m['attack']}  🛡 DEF: {m['defense']}\n"
            f"🏅 Награда: {m['gold']} 🪙 и {m['exp']} ⭐\n\n"
            f"Что делаешь?",
            parse_mode="Markdown",
            reply_markup=make_kb([
                [("⚔️ В атаку!", "do_fight"), ("🏃 Убежать", "flee")],
            ])
        )

    elif data == "do_fight":
        mk = p.get("current_fight")
        if not mk:
            await query.edit_message_text("Нет активного боя.", reply_markup=make_kb([[("🔙", "main_menu")]]))
            return
        p["current_fight"] = None
        log, won = simulate_fight(p, mk)
        await query.edit_message_text(
            log, parse_mode="Markdown",
            reply_markup=make_kb([
                [("⚔️ Ещё битва", "fight"), ("📊 Профиль", "profile")],
                [("🔙 Меню", "main_menu")],
            ])
        )

    elif data == "flee":
        p["current_fight"] = None
        dmg = random.randint(3, 12)
        p["hp"] = max(1, p["hp"] - dmg)
        await query.edit_message_text(
            f"🏃 Ты убежал! Получил {dmg} урона при бегстве.\nHP: {p['hp']}",
            reply_markup=make_kb([[("🔙 Меню", "main_menu")]])
        )

    elif data == "explore":
        events = [
            ("💰 Ты нашёл спрятанный сундук!", "gold", random.randint(10, 50)),
            ("🌿 Нашёл лечебные травы!", "hp", random.randint(15, 35)),
            ("📜 Нашёл свиток с мудростью.", "exp", random.randint(20, 50)),
            ("🪨 Ничего интересного... только камни.", None, 0),
            ("👻 Призрак напугал тебя!", "hp", -random.randint(5, 15)),
            ("🍄 Съел подозрительный гриб.", "hp", -random.randint(3, 10)),
            ("💎 Нашёл крошечный кристалл!", "gems", 1),
        ]
        ev_text, ev_type, ev_val = random.choice(events)
        result = ""
        if ev_type == "gold":
            p["gold"] += ev_val
            result = f" *+{ev_val} 🪙*"
        elif ev_type == "hp":
            p["hp"] = max(1, min(p["max_hp"], p["hp"] + ev_val))
            result = f" *{'+' if ev_val >= 0 else ''}{ev_val} ❤️*"
        elif ev_type == "exp":
            p["exp"] += ev_val
            result = f" *+{ev_val} ⭐*"
        elif ev_type == "gems":
            p["gems"] += ev_val
            result = f" *+{ev_val} 💎*"

        await query.edit_message_text(
            f"🔍 *Исследование...*\n\n{ev_text}{result}\n\n{status_bar(p)}",
            parse_mode="Markdown",
            reply_markup=make_kb([
                [("🔍 Ещё раз", "explore"), ("⚔️ Бой", "fight")],
                [("🔙 Меню", "main_menu")],
            ])
        )

    elif data == "heal":
        cost = 20
        if p["hp"] == p["max_hp"]:
            await query.edit_message_text(
                "✅ Ты полностью здоров! Незачем тратить золото.",
                reply_markup=make_kb([[("🔙 Меню", "main_menu")]])
            )
            return
        if p["gold"] < cost:
            await query.edit_message_text(
                f"❌ Недостаточно золота!\nНужно 20 🪙, у тебя {p['gold']} 🪙.",
                reply_markup=make_kb([[("🔙 Меню", "main_menu")]])
            )
            return
        p["gold"] -= cost
        p["hp"] = p["max_hp"]
        await query.edit_message_text(
            f"🍺 *Таверна «Пьяный дракон»*\n\nТы поел и отдохнул.\n❤️ HP полностью восстановлен!\n\n{status_bar(p)}",
            parse_mode="Markdown",
            reply_markup=make_kb([[("🔙 Меню", "main_menu")]])
        )

    elif data == "shop":
        lines = []
        for iid, item in SHOP_ITEMS.items():
            price = f"💎 {item['gems']} кристаллов" if item["gems"] > 0 else f"🪙 {item['gold']} золота"
            lines.append(f"• *{item['name']}* — {price}\n  _{item['desc']}_")

        text = f"🏪 *МАГАЗИН*\n{'─'*28}\n\n" + "\n\n".join(lines) + f"\n\n{'─'*28}\n{status_bar(p)}"

        buttons = []
        row = []
        for iid, item in SHOP_ITEMS.items():
            emoji = item["name"].split()[0]
            row.append((f"{emoji} Купить", f"buy_{iid}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([("🔙 Закрыть", "main_menu")])

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(t, callback_data=d) for t, d in row]
                for row in buttons
            ])
        )

    elif data.startswith("buy_"):
        iid = data[4:]
        item = SHOP_ITEMS.get(iid)
        if not item:
            await query.edit_message_text("❌ Предмет не найден.", reply_markup=make_kb([[("🔙", "shop")]]))
            return

        if item["gems"] > 0:
            if p["gems"] < item["gems"]:
                await query.edit_message_text(
                    f"❌ *Нужно {item['gems']} 💎 кристаллов!*\nЕсть: {p['gems']} 💎\n\nПополни в разделе Донат!",
                    parse_mode="Markdown",
                    reply_markup=make_kb([[("💎 Донат", "donate_menu"), ("🔙 Магазин", "shop")]])
                )
                return
            p["gems"] -= item["gems"]
        else:
            if p["gold"] < item["gold"]:
                await query.edit_message_text(
                    f"❌ *Нужно {item['gold']} 🪙 золота!*\nЕсть: {p['gold']} 🪙",
                    parse_mode="Markdown",
                    reply_markup=make_kb([[("🔙 Магазин", "shop")]])
                )
                return
            p["gold"] -= item["gold"]

        for stat, val in item["effect"].items():
            if stat == "hp":
                p["hp"] = min(p["max_hp"], p["hp"] + val)
            elif stat == "max_hp":
                p["max_hp"] += val
                p["hp"] += val
            else:
                p[stat] = p.get(stat, 0) + val

        if item["type"] != "consumable":
            p["inventory"].append(item["name"])

        await query.edit_message_text(
            f"✅ Куплено: *{item['name']}*!\n_{item['desc']}_\n\n{status_bar(p)}",
            parse_mode="Markdown",
            reply_markup=make_kb([[("🏪 Ещё в магазине", "shop"), ("🔙 Меню", "main_menu")]])
        )

    elif data == "donate_menu":
        text = (
            "💎 *ПОДДЕРЖКА РАЗРАБОТЧИКА*\n"
            "─────────────────────────\n\n"
            "Спасибо, что играешь! Твоя поддержка помогает развивать игру.\n\n"
            "За донат ты получаешь *Кристаллы* — особую валюту для покупки "
            "уникальных предметов в магазине.\n\n"
            "📦 *Пакеты кристаллов:*\n"
            "  ▸ 💎×5 — 1 ⭐ Telegram Star\n"
            "  ▸ 💎×15 — 3 ⭐ Telegram Stars\n"
            "  ▸ 💎×40 — 7 ⭐ Telegram Stars\n"
            "  ▸ 💎×100 — 15 ⭐ Telegram Stars\n\n"
            "_Telegram Stars — встроенная платёжная система Telegram, безопасно и без сторонних сервисов._"
        )
        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_kb([
                [("💎×5 за 1⭐", "donate_1"), ("💎×15 за 3⭐", "donate_3")],
                [("💎×40 за 7⭐", "donate_7"), ("💎×100 за 15⭐", "donate_15")],
                [("🔙 Назад", "main_menu")],
            ])
        )

    elif data in ("donate_1", "donate_3", "donate_7", "donate_15"):
        packages = {
            "donate_1":  (1,  5,   "5 кристаллов"),
            "donate_3":  (3,  15,  "15 кристаллов"),
            "donate_7":  (7,  40,  "40 кристаллов"),
            "donate_15": (15, 100, "100 кристаллов"),
        }
        stars, gems, label = packages[data]
        await ctx.bot.send_invoice(
            chat_id=uid,
            title=f"💎 {label}",
            description=f"Получи {gems} кристаллов для игры в «Хрониках Заории»!",
            payload=f"gems_{gems}_{uid}",
            provider_token="",
            currency="XTR",
            prices=[LabeledPrice(label=f"{gems} кристаллов", amount=stars)],
        )

    elif data == "leaderboard":
        if not PLAYERS:
            text = "🏆 *Таблица героев пуста*\nСтань первым!"
        else:
            top = sorted(PLAYERS.values(), key=lambda x: (x["level"], x["kills"]), reverse=True)[:10]
            medals = ["🥇", "🥈", "🥉"] + ["🔸"] * 7
            lines = [f"{medals[i]} *{pp['name']}* — Ур.{pp['level']} | 💀{pp['kills']} убийств" for i, pp in enumerate(top)]
            text = "🏆 *ТОП ГЕРОЕВ*\n─────────────\n" + "\n".join(lines)

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=make_kb([[("🔙 Меню", "main_menu")]])
        )


# ════════════════════════════════════════════════════════════
#  💳  ПЛАТЁЖНАЯ СИСТЕМА
# ════════════════════════════════════════════════════════════
async def pre_checkout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    payload = update.message.successful_payment.invoice_payload
    try:
        _, gems_str, _ = payload.split("_", 2)
        gems = int(gems_str)
    except Exception:
        gems = 0

    p = get_player(uid)
    p["gems"] += gems

    await update.message.reply_text(
        f"🎉 *Огромное спасибо за поддержку!*\n\n"
        f"Тебе зачислено *{gems} 💎 кристаллов*!\n"
        f"Всего кристаллов: {p['gems']} 💎\n\n"
        f"Трать их в магазине на уникальные предметы!",
        parse_mode="Markdown",
        reply_markup=make_kb([
            [("🏪 В магазин", "shop"), ("🔙 Главное меню", "main_menu")]
        ])
    )


# ════════════════════════════════════════════════════════════
#  🚀  ЗАПУСК
# ════════════════════════════════════════════════════════════
def main():
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("\n" + "═" * 50)
        print("❌  ОШИБКА: Токен бота не задан!")
        print("   Задай переменную окружения: BOT_TOKEN=...")
        print("═" * 50 + "\n")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))

    logger.info("🎮 Бот «Хроники Заории» запущен!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
