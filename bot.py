import asyncio
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))
TZ = ZoneInfo("Europe/Simferopol")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TZ)

# ====================== ВРЕМЕНА ПАР ======================

MONDAY_TIMES = {
    0: ("09:00", "09:35"),   # Классный час / Разговоры о важном
    1: ("09:40", "11:00"),
    2: ("11:10", "12:30"),
    3: ("13:00", "14:20"),
    4: ("14:30", "15:50"),
}

STANDARD_TIMES = {
    1: ("09:00", "10:20"),
    2: ("10:30", "11:50"),
    3: ("12:20", "13:40"),
    4: ("13:50", "15:10"),
}

# ====================== РАСПИСАНИЕ ======================

SCHEDULE = {
    # Понедельник (одинаковый)
    0: {  # 0 = понедельник
        "both": {
            0: "Разговоры о важном — Корпус 2, каб. 11",
            1: "МДК 04.01 Внедрение и поддержка компьютерных систем\nКетов Д.В. — Корпус 2, каб. 11",
            2: "Иностранный язык в профессиональной деятельности\nКороленко А.Н. — Корпус 1, каб. 17",
            3: "История\nБатовская Д.А. — Корпус 1, каб. 7",
        }
    },

    # Вторник
    1: {
        "blue": {
            1: "Архитектура АС\nМелентьева О.Н. — Корпус 2, каб. 40",
            2: "МДК 04.02\nКогут В.И. — Корпус 2, каб. 40",
            3: "Компьютерные сети\nКогут В.И. — Корпус 2, каб. 40",
            4: "Деловой русский язык\nЧернышенко Н.В. — Корпус 1, каб. 14",
        },
        "red": {
            1: "Учебная практика\nКитаев А.В. — Корпус 2, каб. 40",
            2: "Учебная практика\nКитаев А.В. — Корпус 2, каб. 40",
            3: "Учебная практика\nКитаев А.В. — Корпус 2, каб. 40",
        }
    },

    # Среда
    2: {
        "blue": {
            1: "Архитектура аппаратных средств\nМелентьева О.Н. — Корпус 2, каб. 45",
            2: "Дискретная математика\nКарев Д.В. — Корпус 1, каб. 38",
            3: "МДК 04.02\nКогут В.И. — Корпус 2, каб. 40",
        },
        "red": {
            1: "Архитектура аппаратных средств\nМелентьева О.Н. — Корпус 2, каб. 45",
            2: "Дискретная математика\nКарев Д.В. — Корпус 1, каб. 38",
            3: "МДК 04.02\nКогут В.И. — Корпус 2, каб. 40",
            4: "Физика\nДемиденко А.В. — Корпус 2, каб. 26",
        }
    },

    # Четверг (одинаковый)
    3: {
        "both": {
            1: "Физика\nДемиденко А.В. — Корпус 2, каб. 26",
            2: "Математика\nГапонов А.И. — Корпус 1, каб. 12",
            3: "Физическая культура\nКузьменко А.П. — Корпус 1",
            4: "Деловой русский язык и культура речи\nЧернышенко Н.В. — Корпус 1, каб. 14",
        }
    },

    # Пятница
    4: {
        "blue": {
            1: "Компьютерные сети\nКогут В.И. — Корпус 2, каб. 40",
            2: "МДК 04.01 Внедрение и поддержка компьютерных систем\nКетов Д.В. — Корпус 2, каб. 11",
            3: "МДК 04.02\nКогут В.И. — Корпус 2, каб. 40",
            4: "Математика\nГапонов А.И. — Корпус 1, каб. 12",
        },
        "red": {
            1: "Компьютерные сети\nКогут В.И. — Корпус 2, каб. 40",
            2: "МДК 04.01 Внедрение и поддержка компьютерных систем\nКетов Д.В. — Корпус 2, каб. 11",
            3: "История России\nВакансия — Корпус 1, каб. 7",
            4: "Математика\nГапонов А.И. — Корпус 1, каб. 12",
        }
    },
}

# ====================== АВТОБУСЫ ======================

BUSES = [
    ("07:00", "07:25", 25),
    ("07:20", "07:40", 20),
    ("07:40", "08:00", 20),
    ("08:00", "08:20", 20),
    ("08:21", "08:38", 17),
    ("08:35", "08:55", 20),
]

WALK_MINUTES = 5
BUFFER_MINUTES = 12
ARRIVE_BY = time(8, 42)

# ====================== ФУНКЦИИ ======================

def get_week_type() -> str:
    """Определяет красная или синяя неделя"""
    # На 23.09.2026 — красная неделя (ты сказал)
    # Будем считать от этой даты
    known_red_week = datetime(2026, 9, 21, tzinfo=TZ)  # понедельник красной недели
    today = datetime.now(TZ)
    delta_weeks = (today - known_red_week).days // 7
    return "red" if delta_weeks % 2 == 0 else "blue"

def get_today_schedule() -> dict:
    now = datetime.now(TZ)
    weekday = now.weekday()  # 0 = пн ... 4 = пт
    week_type = get_week_type()

    if weekday not in SCHEDULE:
        return {}

    day_data = SCHEDULE[weekday]

    if "both" in day_data:
        return day_data["both"]
    return day_data.get(week_type, {})

def format_schedule(schedule: dict, is_monday: bool = False) -> str:
    if not schedule:
        return "Сегодня пар нет 🎉"

    times = MONDAY_TIMES if is_monday else STANDARD_TIMES
    lines = []

    for pair_num in sorted(schedule.keys()):
        start, end = times.get(pair_num, ("??:??", "??:??"))
        subject = schedule[pair_num]
        if pair_num == 0:
            lines.append(f"<b>Классный час / Разговоры о важном</b>\n{start}–{end}\n{subject}")
        else:
            lines.append(f"<b>{pair_num} пара</b> ({start}–{end})\n{subject}")

    return "\n\n".join(lines)

def find_best_bus():
    target = datetime.combine(datetime.now(TZ).date(), ARRIVE_BY, tzinfo=TZ)
    best = None

    for dep_str, arr_str, travel in BUSES:
        dep = datetime.combine(datetime.now(TZ).date(), datetime.strptime(dep_str, "%H:%M").time(), tzinfo=TZ)
        arr = datetime.combine(datetime.now(TZ).date(), datetime.strptime(arr_str, "%H:%M").time(), tzinfo=TZ)
        leave = dep - timedelta(minutes=WALK_MINUTES + BUFFER_MINUTES)

        if arr <= target and (best is None or leave > best[0]):
            best = (leave, dep_str, arr_str)

    if best:
        return best[0].strftime("%H:%M"), best[1], best[2]

    dep_str, arr_str, _ = BUSES[0]
    leave = datetime.combine(datetime.now(TZ).date(), datetime.strptime(dep_str, "%H:%M").time(), tzinfo=TZ) - timedelta(minutes=WALK_MINUTES + BUFFER_MINUTES)
    return leave.strftime("%H:%M"), dep_str, arr_str

async def send_daily_message():
    now = datetime.now(TZ)
    weekday = now.weekday()
    week_type = get_week_type()
    week_name = "🔴 Красная" if week_type == "red" else "🔵 Синяя"
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    schedule = get_today_schedule()
    is_monday = weekday == 0

    leave, bus_dep, bus_arr = find_best_bus()

    text = (
        f"📅 <b>{day_names[weekday]}</b> ({week_name} неделя)\n\n"
        f"{format_schedule(schedule, is_monday)}\n\n"
        f"🚌 <b>Выходи из дома в {leave}</b>\n"
        f"Автобус {bus_dep} → АС Западная {bus_arr}"
    )

    await bot.send_message(ADMIN_ID, text, parse_mode="HTML")

# ====================== КОМАНДЫ ======================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    week = "🔴 Красная" if get_week_type() == "red" else "🔵 Синяя"
    await message.answer(
        f"Привет! Сейчас {week} неделя.\n\n"
        "Команды:\n"
        "/today — расписание на сегодня + время выхода\n"
        "/week — какая сейчас неделя\n"
        "/buses — автобусы"
    )

@dp.message(Command("today"))
async def cmd_today(message: Message):
    now = datetime.now(TZ)
    weekday = now.weekday()
    week_type = get_week_type()
    week_name = "🔴 Красная" if week_type == "red" else "🔵 Синяя"
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    schedule = get_today_schedule()
    leave, bus_dep, bus_arr = find_best_bus()

    text = (
        f"📅 <b>{day_names[weekday]}</b> ({week_name})\n\n"
        f"{format_schedule(schedule, weekday == 0)}\n\n"
        f"🚌 Выходи в <b>{leave}</b>\n"
        f"Автобус {bus_dep} → АС Западная {bus_arr}"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("week"))
async def cmd_week(message: Message):
    week = "🔴 Красная" if get_week_type() == "red" else "🔵 Синяя"
    await message.answer(f"Сейчас {week} неделя")

@dp.message(Command("buses"))
async def cmd_buses(message: Message):
    lines = ["🚌 <b>Автобусы Почтовое → АС Западная</b>\n"]
    for dep, arr, travel in BUSES:
        lines.append(f"{dep} → {arr} ({travel} мин)")
    await message.answer("\n".join(lines), parse_mode="HTML")

# ====================== ЗАПУСК ======================

async def main():
    scheduler.add_job(send_daily_message, "cron", hour=7, minute=0)
    scheduler.start()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
