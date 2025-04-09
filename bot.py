from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import sqlite3
import asyncio

bot = Bot(token="7783266131:AAFMGTIwsxyAw5ELqCLGnRXJDpXE6RNUTZE")
dp = Dispatcher()  

conn = sqlite3.connect('bookings.db', check_same_thread=False)
cursor = conn.cursor()

cursor.execute('''
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    check_in TEXT,
    check_out TEXT
)
''')
conn.commit()

user_data = {}

def generate_calendar(year=None, month=None, selected_dates=None):
    """Генерує графічний календар"""
    if year is None or month is None:
        today = datetime.now()
        year, month = today.year, today.month
    
    first_day = datetime(year, month, 1)
    days_in_month = (datetime(year, month + 1, 1) - timedelta(days=1)).day
    start_weekday = first_day.weekday()  
    
    keyboard = []
    
    month_name = first_day.strftime("%B %Y")
    keyboard.append([InlineKeyboardButton(text=month_name, callback_data="ignore")])
    
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
    keyboard.append([InlineKeyboardButton(text=day, callback_data="ignore") for day in week_days])
    
    row = []
    for _ in range(start_weekday):
        row.append(InlineKeyboardButton(text=" ", callback_data="ignore"))
    
    for day in range(1, days_in_month + 1):
        date = datetime(year, month, day).date()
        date_str = date.strftime("%Y-%m-%d")
        
        cursor.execute("SELECT * FROM bookings WHERE ? BETWEEN check_in AND check_out", (date_str,))
        busy = cursor.fetchone()
        
        if busy:
            btn = InlineKeyboardButton(text="❌", callback_data=f"busy_{date_str}")
        elif selected_dates and date in selected_dates:
            btn = InlineKeyboardButton(text="🔵", callback_data=f"sel_{date_str}")
        else:
            btn = InlineKeyboardButton(text=str(day), callback_data=f"day_{date_str}")
        
        row.append(btn)
        if len(row) == 7:
            keyboard.append(row)
            row = []
    
    if row: 
        keyboard.append(row)
    
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    nav_buttons = [
        InlineKeyboardButton(text="⬅️", callback_data=f"nav_{prev_year}_{prev_month}"),
        InlineKeyboardButton(text="➡️", callback_data=f"nav_{next_year}_{next_month}")
    ]
    keyboard.append(nav_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    """Обробник команди /start"""
    await message.answer(
        "🏨 Вітаю в системі бронювання! Оберіть дату заїзду:",
        reply_markup=generate_calendar()
    )

@dp.callback_query(lambda c: c.data.startswith('day_'))
async def process_day_selection(callback_query: types.CallbackQuery):
    """Обробник вибору дати"""
    user_id = callback_query.from_user.id
    date_str = callback_query.data.split('_')[1]
    selected_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    
    if user_id not in user_data:
        user_data[user_id] = {"check_in": None, "check_out": None}
    
    if not user_data[user_id]["check_in"]:
        user_data[user_id]["check_in"] = selected_date
        await callback_query.message.edit_text(
            f"✅ Заїзд: {selected_date.strftime('%d.%m.%Y')}\nОберіть дату виїзду:",
            reply_markup=generate_calendar(
                selected_date.year,
                selected_date.month,
                selected_dates=[selected_date]
            )
        )
    else:
        if selected_date > user_data[user_id]["check_in"]:
            user_data[user_id]["check_out"] = selected_date
            cursor.execute(
                "INSERT INTO bookings (user_id, check_in, check_out) VALUES (?, ?, ?)",
                (user_id, 
                 user_data[user_id]["check_in"].strftime("%Y-%m-%d"),
                 user_data[user_id]["check_out"].strftime("%Y-%m-%d"))
            )
            conn.commit()
            
            await callback_query.message.edit_text(
                f"🎉 Бронювання успішне!\n"
                f"Заїзд: {user_data[user_id]['check_in'].strftime('%d.%m.%Y')}\n"
                f"Виїзд: {user_data[user_id]['check_out'].strftime('%d.%m.%Y')}"
            )
            del user_data[user_id]
        else:
            await callback_query.answer("Дата виїзду повинна бути після дати заїзду!", show_alert=True)

@dp.callback_query(lambda c: c.data.startswith('nav_'))
async def navigate_month(callback_query: types.CallbackQuery):
    """Обробник навігації по місяцях"""
    _, year, month = callback_query.data.split('_')
    user_id = callback_query.from_user.id
    
    selected_dates = []
    if user_id in user_data:
        if user_data[user_id]["check_in"]:
            selected_dates.append(user_data[user_id]["check_in"])
    
    await callback_query.message.edit_reply_markup(
        reply_markup=generate_calendar(
            int(year),
            int(month),
            selected_dates=selected_dates
        )
    )

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())