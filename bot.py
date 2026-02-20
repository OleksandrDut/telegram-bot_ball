import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.types import *
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from db import *
from admin import register_admin_handlers

TOKEN = "7709082743:AAGtPsOFAZbZED9OOjrPpQzNdT2_kcZKibE"

logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher()

# ---------- FSM ----------

class Form(StatesGroup):
    name = State()
    age = State()
    gender = State()
    height = State()
    bio = State()
    photo = State()

# ---------- КНОПКИ ----------

menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Створити анкету")],
        [KeyboardButton(text="Шукаю партнерку"),
         KeyboardButton(text="Шукаю партнера")],
        [KeyboardButton(text="Моя анкета"),
         KeyboardButton(text="Видалити анкету")]
    ],
    resize_keyboard=True
)

gender_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Хлопець"),
               KeyboardButton(text="Дівчина")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

# ---------- START ----------

@dp.message(F.text == "/start")
async def start(m: Message):
    await m.answer("Твоя ідеальна пара для балу вже чекає десь поруч! Заповнюй коротку анкету та знаходь партнера, з яким цей вечір стане по-справжньому магічним і незабутнім.", reply_markup=menu)

# ---------- СТВОРЕННЯ АНКЕТИ ----------

@dp.message(F.text == "Створити анкету")
async def create(m: Message, state: FSMContext):

    if await is_banned(m.from_user.id):
        return await m.answer("🚫 Ти заблокований.")
    await m.answer("Як тебе звати?")
    await state.set_state(Form.name)

@dp.message(Form.name)
async def name(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Скільки тобі років?")
    await state.set_state(Form.age)

@dp.message(Form.age)
async def age(m: Message, state: FSMContext):
    await state.update_data(age=m.text)
    await m.answer("Стать:", reply_markup=gender_kb)
    await state.set_state(Form.gender)

@dp.message(Form.gender)
async def gender(m: Message, state: FSMContext):
    await state.update_data(gender=m.text)
    await m.answer("Зріст:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(Form.height)

@dp.message(Form.height)
async def height(m: Message, state: FSMContext):
    await state.update_data(height=m.text)
    await m.answer("Коротко про себе:")
    await state.set_state(Form.bio)

@dp.message(Form.bio)
async def bio(m: Message, state: FSMContext):
    await state.update_data(bio=m.text)
    await m.answer("Надішли фото 📸")
    await state.set_state(Form.photo)

@dp.message(Form.photo, F.photo)
async def photo(m: Message, state: FSMContext):
    data = await state.get_data()

    await save_profile((
        m.from_user.id,
        data["name"],
        data["age"],
        data["gender"],
        data["height"],
        data["bio"],
        m.photo[-1].file_id,
        m.from_user.username
    ))

    await m.answer("✅ Анкету збережено!", reply_markup=menu)
    await state.clear()

# ---------- МОЯ АНКЕТА ----------

@dp.message(F.text == "Моя анкета")
async def my(m: Message):
    p = await get_profile(m.from_user.id)

    if not p:
        return await m.answer("Анкети нема")

    txt = f"{p[1]}, {p[2]} років\n{p[4]} см\n{p[5]}"
    await m.answer_photo(p[6], caption=txt)

# ---------- ПОШУК ----------

async def show(m: Message, gender):
    p = await random_profile(gender, m.from_user.id)

    if not p:
        return await m.answer("Нікого нема 😢")

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍",
                                 callback_data=f"like_{p[0]}_{gender}"),
            InlineKeyboardButton(text="➡️",
                                 callback_data=f"next_{gender}")
        ]
    ])

    txt = f"{p[1]}, {p[2]} років\n{p[4]} см\n{p[5]}"
    await m.answer_photo(p[6], caption=txt, reply_markup=kb)

@dp.message(F.text == "Шукаю партнерку")
async def fg(m: Message):
    await show(m,"Дівчина")

@dp.message(F.text == "Шукаю партнера")
async def fb(m: Message):
    await show(m,"Хлопець")

# ---------- ЛАЙК ----------

@dp.callback_query(F.data.startswith("like_"))
async def like(c: CallbackQuery):
    data = c.data.split("_")
    target = int(data[1])
    gender = data[2]

    await add_like(c.from_user.id, target)

    liker = await get_profile(c.from_user.id)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👍 Прийняти",
                                 callback_data=f"accept_{c.from_user.id}"),
            InlineKeyboardButton(text="👎",
                                 callback_data="decline")
        ]
    ])

    txt = f"{liker[1]}, {liker[2]} років\n{liker[4]} см\n{liker[5]}"
    await bot.send_photo(target, liker[6],
                         caption=txt, reply_markup=kb)

    await c.message.edit_reply_markup(reply_markup=None)
    await show(c.message, gender)
    await c.answer()

# ---------- ACCEPT ----------

@dp.callback_query(F.data.startswith("accept_"))
async def accept(c: CallbackQuery):
    uid = int(c.data.split("_")[1])

    await add_like(c.from_user.id, uid)
    await send_match(c.from_user.id, uid)

    await c.answer("Матч! 🎉")

@dp.callback_query(F.data == "decline")
async def decline(c: CallbackQuery):
    await c.message.delete()
    await c.answer()

# ---------- МАТЧ ----------

async def send_match(uid1, uid2):
    p1 = await get_profile(uid1)
    p2 = await get_profile(uid2)

    link1 = f"@{p1[7]}" if p1[7] else f"tg://user?id={uid1}"
    link2 = f"@{p2[7]}" if p2[7] else f"tg://user?id={uid2}"

    await bot.send_photo(uid1, p2[6],
        caption=f"🎉 У вас МЕТЧ!\nПиши: {link2}")

    await bot.send_photo(uid2, p1[6],
        caption=f"🎉 У вас МЕТЧ!\nПиши: {link1}")

# ---------- NEXT ----------

@dp.callback_query(F.data.startswith("next_"))
async def next_(c: CallbackQuery):
    gender = c.data.split("_")[1]
    await c.message.edit_reply_markup(reply_markup=None)
    await show(c.message, gender)
    await c.answer()

# ---------- DELETE ----------

@dp.message(F.text == "Видалити анкету")
async def delp(m: Message):
    await delete_profile(m.from_user.id)
    await m.answer("Анкету видалено")

# ---------- MAIN ----------

async def main():
    await init_db()

    register_admin_handlers(dp)  # ПІДКЛЮЧАЄМО АДМІНКУ

    print("✅ BOT STARTED")
    await dp.start_polling(bot)

asyncio.run(main())
