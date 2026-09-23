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
TZ = ZoneInfo("Europe/Simferopol")  # Крым

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TZ)

# ====================== РАСПИСАНИЕ ======================

# Понедельник (из фото)
MONDAY = {
    "Классный час": ("09:00", "09:35"),
    "1 пара": ("09:40", "11:00"),
    "2 пара": ("11:10", "12:30"),
    "Обед": ("12:30", "13:00"),
    "3 пара": ("13:00", "14:20"),
    "4 пара": ("14:30", "15:50"),
}

# Остальные дни (начало 9:00, пары 1ч20м, перемены 10м, большая 30м после 2-й)
STANDARD = {
    "1 пара": ("09:00", "10:20"),
    "2 пара": ("10:30", "11:50"),
    "Обед (большая перемена)": ("11:50", "12:20"),
    "3 пара": ("12:20", "13:40"),
    "4 пара": ("13:50", "15:10"),
}

# Автобусы Почтовое → АС Западная (примерные утренние, обновляй по необходимости)
# (время отправления, время прибытия, время в пути)
BUSES = [
    ("07:00", "07:25", 25),
    ("07:20", "07:40", 20),
    ("07:40", "08:00", 20),
    ("08:00", "08:20", 20),
    ("08:21", "08:38", 17),   # самый удобный
    ("08:35", "08:55", 20),
]

WALK_MINUTES = 5          # до остановки
BUFFER_MINUTES = 12       # запас (опоздания автобуса + дойти от АС)
ARRIVE_BY = time(8, 42)   # хочешь быть на АС Западная к 8:40-45

# ====================== ФУНКЦИИ ======================

def get_today_schedule() -> dict:
    now = datetime.now(TZ)
    if now.weekday() == 0:  # понедельник
        return MONDAY
    return STANDARD

def format_schedule(schedule: dict) -> str:
    lines = []
    for name, (start, end) in schedule.items():
        lines.append(f"<b>{name}</b>\n{start} – {end}")
    return "\n\n".join(lines)

def find_best_bus() -> tuple[str, str, str]:
    """Возвращает: время выхода из дома, время автобуса, время прибытия"""
    target = datetime.combine(datetime.now(TZ).date(), ARRIVE_BY, tzinfo=TZ)
    
    best = None
    for dep_str, arr_str, travel in BUSES:
        dep = datetime.combine(datetime.now(TZ).date(), 
                               datetime.strptime(dep_str, "%H:%M").time(), tzinfo=TZ)
        arr = datetime.combine(datetime.now(TZ).date(), 
                               datetime.strptime(arr_str, "%H:%M").time(), tzinfo=TZ)
        
        # время выхода = отправление - 5 мин ходьбы - запас
        leave = dep - timedelta(minutes=WALK_MINUTES + BUFFER_MINUTES)
        
        if arr <= target and (best is None or leave > best[0]):
            best = (leave, dep_str, arr_str)
    
    if best:
        leave_str = best[0].strftime("%H:%M")
        return leave_str, best[1], best[2]
    
    # если ничего не нашли — берём самый ранний
    dep_str, arr_str, _ = BUSES[0]
    leave = datetime.combine(datetime.now(TZ).date(), 
                             datetime.strptime(dep_str, "%H:%M").time(), tzinfo=TZ) \
            - timedelta(minutes=WALK_MINUTES + BUFFER_MINUTES)
    return leave.strftime("%H:%M"), dep_str, arr_str

async def send_daily_message():
    schedule = get_today_schedule()
    day_name = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"][datetime.now(TZ).weekday()]
    
    leave, bus_dep, bus_arr = find_best_bus()
    
    text = (
        f"📅 <b>Расписание на {day_name}</b>\n\n"
        f"{format_schedule(schedule)}\n\n"
        f"🚌 <b>Когда выходить:</b>\n"
        f"Выходи из дома в <b>{leave}</b>\n"
        f"Автобус в <b>{bus_dep}</b> → АС Западная в <b>{bus_arr}</b>\n"
        f"(5 мин до остановки + запас)\n\n"
        f"Нужно быть на АС Западная к 8:40–8:45"
    )
    
    await bot.send_message(ADMIN_ID, text, parse_mode="HTML")

# ====================== КОМАНДЫ ======================

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Привет! Я бот твоего расписания.\n\n"
        "Команды:\n"
        "/today — расписание на сегодня + когда выходить\n"
        "/schedule — полное расписание\n"
        "/buses — список автобусов\n"
        "/help — помощь"
    )

@dp.message(Command("today"))
async def cmd_today(message: Message):
    schedule = get_today_schedule()
    leave, bus_dep, bus_arr = find_best_bus()
    
    text = (
        f"📅 <b>Сегодня</b>\n\n"
        f"{format_schedule(schedule)}\n\n"
        f"🚌 Выходи в <b>{leave}</b>\n"
        f"Автобус {bus_dep} → АС Западная {bus_arr}"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("schedule"))
async def cmd_schedule(message: Message):
    text = (
        "<b>ПОНЕДЕЛЬНИК</b>\n" + format_schedule(MONDAY) + "\n\n"
        "<b>ВТОРНИК–СУББОТА</b>\n" + format_schedule(STANDARD)
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("buses"))
async def cmd_buses(message: Message):
    lines = ["🚌 <b>Автобусы Почтовое → АС Западная</b>\n"]
    for dep, arr, travel in BUSES:
        lines.append(f"{dep} → {arr} ({travel} мин)")
    await message.answer("\n".join(lines), parse_mode="HTML")

@dp.message(Command("help"))
async def cmd_help(message: Message):
    await message.answer(
        "Бот каждый день в 7:00 присылает расписание и время выхода.\n\n"
        "Если автобусы изменились — напиши мне новые времена, я обновлю код."
    )

# ====================== ЗАПУСК ======================

async def main():
    # Ежедневная рассылка в 7:00
    scheduler.add_job(send_daily_message, "cron", hour=7, minute=0)
    scheduler.start()
    
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
