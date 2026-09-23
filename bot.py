import asyncio
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from aiogram import Bot, Dispatcher
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
    0: ("09:00", "09:35"),
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
    0: {  # Понедельник
        "both": {
            0: "Разговоры о важном — Корпус 2, каб. 11",
            1: "МДК 04.01 Внедрение и поддержка компьютерных систем\nКетов Д.В. — Корпус 2, каб. 11",
            2: "Иностранный язык в профессиональной деятельности\nКороленко А.Н. — Корпус 1, каб. 17",
            3: "История\nБатовская Д.А. — Корпус 1, каб. 7",
        }
    },
    1: {  # Вторник
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
    2: {  # Среда
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
    3: {  # Четверг
        "both": {
            1: "Физика\nДемиденко А.В. — Корпус 2, каб. 26",
            2: "Математика\nГапонов А.И. — Корпус 1, каб. 12",
            3: "Физическая культура\nКузьменко А.П. — Корпус 1",
            4: "Деловой русский язык и культура речи\nЧернышенко Н.В. — Корпус 1, каб. 14",
        }
    },
    4: {  # Пятница
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

# ====================== АВТОБУСЫ (по данным tutu.ru) ======================

# Почтовое → АС Западная (утро)
BUSES_TO = [
    ("06:39", "07:05"),
    ("07:09", "07:30"),
    ("08:21", "08:38"),   # самый удобный
    ("08:35", "08:55"),
]

# АС Западная → Почтовое (обратно)
BUSES_BACK = [
    "12:30", "12:45",
    "13:20", "13:30", "13:50",
    "14:35", "14:47",
    "15:15", "15:30",
    "16:00", "16:42",
    "17:20", "17:35",
    "18:00", "18:30", "19:00", "19:25"
]

WALK_MINUTES = 5
BUFFER_MINUTES = 12
ARRIVE_BY = time(8, 42)

# ====================== ФУНКЦИИ ======================

def get_week_type() -> str:
    known_red_week = datetime(2026, 9, 21, tzinfo=TZ)
    today = datetime.now(TZ)
    delta_weeks = (today - known_red_week).days // 7
    return "red" if delta_weeks % 2 == 0 else "blue"

def get_today_schedule() -> dict:
    weekday = datetime.now(TZ).weekday()
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
            lines.append(f"<b>Классный час</b>\n{start}–{end}\n{subject}")
        else:
            lines.append(f"<b>{pair_num} пара</b> ({start}–{end})\n{subject}")
    return "\n\n".join(lines)

def find_best_bus_to():
    target = datetime.combine(datetime.now(TZ).date(), ARRIVE_BY, tzinfo=TZ)
    best = None
    for dep_str, arr_str in BUSES_TO:
        dep = datetime.combine(datetime.now(TZ).date(), datetime.strptime(dep_str, "%H:%M").time(), tzinfo=TZ)
        arr = datetime.combine(datetime.now(TZ).date(), datetime.strptime(arr_str, "%H:%M").time(), tzinfo=TZ)
        leave = dep - timedelta(minutes=WALK_MINUTES + BUFFER_MINUTES)
        if arr <= target and (best is None or leave > best[0]):
            best = (leave, dep_str, arr_str)
    if best:
        return best[0].strftime("%H:%M"), best[1], best[2]
    dep_str, arr_str = BUSES_TO[0]
    leave = datetime.combine(datetime.now(TZ).date(), datetime.strptime(dep_str, "%H:%M").time(), tzinfo=TZ) - timedelta(minutes=WALK_MINUTES + BUFFER_MINUTES)
    return leave.strftime("%H:%M"), dep_str, arr_str

def find_nearest_bus_back(after_time: datetime) -> str:
    for bus_str in BUSES_BACK:
        bus_time = datetime.combine(after_time.date(), datetime.strptime(bus_str, "%H:%M").time(), tzinfo=TZ)
        if bus_time > after_time + timedelta(minutes=8):
            return bus_str
    return BUSES_BACK[-1]

# ====================== НАПОМИНАНИЯ ======================

async def send_pair_reminder(pair_num: int, subject: str, start: str):
    text = (
        f"⏰ <b>Через 5 минут начинается пара!</b>\n\n"
        f"<b>{pair_num} пара</b> ({start})\n"
        f"{subject}"
    )
    await bot.send_message(ADMIN_ID, text, parse_mode="HTML")

async def send_end_of_day(last_end: str):
    end_dt = datetime.combine(datetime.now(TZ).date(), datetime.strptime(last_end, "%H:%M").time(), tzinfo=TZ)
    bus = find_nearest_bus_back(end_dt)
    text = (
        f"✅ <b>Пары закончились</b> ({last_end})\n\n"
        f"🚌 Ближайший автобус с АС Западная → Почтовое:\n"
        f"<b>{bus}</b>"
    )
    await bot.send_message(ADMIN_ID, text, parse_mode="HTML")

def schedule_today_reminders():
    schedule = get_today_schedule()
    if not schedule:
        return

    weekday = datetime.now(TZ).weekday()
    times = MONDAY_TIMES if weekday == 0 else STANDARD_TIMES
    now = datetime.now(TZ)
    last_end = None

    for pair_num in sorted(schedule.keys()):
        start_str, end_str = times.get(pair_num, (None, None))
        if not start_str:
            continue

        start_dt = datetime.combine(now.date(), datetime.strptime(start_str, "%H:%M").time(), tzinfo=TZ)
        remind_dt = start_dt - timedelta(minutes=5)

        if remind_dt > now:
            scheduler.add_job(
                send_pair_reminder,
                "date",
                run_date=remind_dt,
                args=[pair_num, schedule[pair_num], start_str],
                id=f"pair_{pair_num}_{now.date()}",
                replace_existing=True
            )
        last_end = end_str

    if last_end:
        end_dt = datetime.combine(now.date(), datetime.strptime(last_end, "%H:%M").time(), tzinfo=TZ)
        if end_dt > now:
            scheduler.add_job(
                send_end_of_day,
                "date",
                run_date=end_dt + timedelta(minutes=1),
                args=[last_end],
                id=f"end_{now.date()}",
                replace_existing=True
            )

async def send_daily_message():
    now = datetime.now(TZ)
    weekday = now.weekday()
    week_type = get_week_type()
    week_name = "🔴 Красная" if week_type == "red" else "🔵 Синяя"
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    schedule = get_today_schedule()
    leave, bus_dep, bus_arr = find_best_bus_to()

    text = (
        f"📅 <b>{day_names[weekday]}</b> ({week_name} неделя)\n\n"
        f"{format_schedule(schedule, weekday == 0)}\n\n"
        f"🚌 <b>Выходи из дома в {leave}</b>\n"
        f"Автобус {bus_dep} → АС Западная {bus_arr}"
    )
    await bot.send_message(ADMIN_ID, text, parse_mode="HTML")
    schedule_today_reminders()

# ====================== КОМАНДЫ ======================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    week = "🔴 Красная" if get_week_type() == "red" else "🔵 Синяя"
    await message.answer(
        f"Привет! Сейчас {week} неделя.\n\n"
        "Команды:\n"
        "/today — расписание + время выхода\n"
        "/week — какая неделя\n"
        "/buses — автобусы"
    )
    schedule_today_reminders()

@dp.message(Command("today"))
async def cmd_today(message: Message):
    now = datetime.now(TZ)
    weekday = now.weekday()
    week_type = get_week_type()
    week_name = "🔴 Красная" if week_type == "red" else "🔵 Синяя"
    day_names = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]

    schedule = get_today_schedule()
    leave, bus_dep, bus_arr = find_best_bus_to()

    text = (
        f"📅 <b>{day_names[weekday]}</b> ({week_name})\n\n"
        f"{format_schedule(schedule, weekday == 0)}\n\n"
        f"🚌 Выходи в <b>{leave}</b>\n"
        f"Автобус {bus_dep} → АС Западная {bus_arr}"
    )
    await message.answer(text, parse_mode="HTML")
    schedule_today_reminders()

@dp.message(Command("week"))
async def cmd_week(message: Message):
    week = "🔴 Красная" if get_week_type() == "red" else "🔵 Синяя"
    await message.answer(f"Сейчас {week} неделя")

@dp.message(Command("buses"))
async def cmd_buses(message: Message):
    lines = ["🚌 <b>Туда (Почтовое → АС Западная)</b>"]
    for dep, arr in BUSES_TO:
        lines.append(f"{dep} → {arr}")
    lines.append("\n🚌 <b>Обратно (АС Западная → Почтовое)</b>")
    lines.append(", ".join(BUSES_BACK))
    await message.answer("\n".join(lines), parse_mode="HTML")

# ====================== ЗАПУСК ======================

async def main():
    scheduler.add_job(send_daily_message, "cron", hour=7, minute=0)
    schedule_today_reminders()
    scheduler.start()
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
