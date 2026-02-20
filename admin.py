from aiogram import F, Dispatcher
from aiogram.types import *
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

from db import *
import aiosqlite
import asyncio

ADMIN_USERNAMES = ["danabila07",
    "Dutka_O", "Kuznitsov_V"]


def is_admin(user):
    return user.username in ADMIN_USERNAMES


class AdminForm(StatesGroup):
    comment = State()


def register_admin_handlers(dp: Dispatcher):

    # ---------- МЕНЮ ----------
    @dp.message(F.text == "/admin")
    async def admin_menu(m: Message):
        if not is_admin(m.from_user):
            return

        kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="🔍 Модерація анкет")],
                [KeyboardButton(text="📊 Статистика")]
            ],
            resize_keyboard=True
        )

        await m.answer("👮 Адмін панель", reply_markup=kb)

    # ---------- СТАТИСТИКА ----------
    @dp.message(F.text == "📊 Статистика")
    async def stats(m: Message):
        if not is_admin(m.from_user):
            return

        async with aiosqlite.connect("dating.db") as db:
            cur = await db.execute("SELECT COUNT(*) FROM profiles")
            users = (await cur.fetchone())[0]

            cur = await db.execute("SELECT COUNT(*) FROM bans")
            bans = (await cur.fetchone())[0]

        matches = await get_matches_count()

        await m.answer(
            f"👥 Анкет: {users}\n"
            f"❤️ Матчів: {matches}\n"
            f"🚫 Заблоковано: {bans}"
        )

    # ---------- МОДЕРАЦІЯ (ПОКАЗАТИ ВСІ ПІДРЯД) ----------
    @dp.message(F.text == "🔍 Модерація анкет")
    async def mod(m: Message):
        if not is_admin(m.from_user):
            return

        profiles = await get_all_profiles()

        if not profiles:
            return await m.answer("Анкет нема")

        await m.answer(f"Знайдено анкет: {len(profiles)}\nПоказую всі ↓")

        for i, p in enumerate(profiles, start=1):

            username_text = f"@{p[7]}" if p[7] else "Немає username"

            kb = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🗑 Видалити",
                        callback_data=f"del_{p[0]}"
                    ),
                    InlineKeyboardButton(
                        text="🚫 Бан",
                        callback_data=f"ban_{p[0]}"
                    )
                ]
            ])

            text = (
                f"#{i}\n"
                f"{p[1]}, {p[2]}\n"
                f"{p[4]} см\n"
                f"{p[5]}\n\n"
                f"Username: {username_text}"
            )

            await m.answer_photo(
                p[6],
                caption=text,
                reply_markup=kb
            )

            # Якщо анкет багато — ставимо паузу
            if len(profiles) > 100:
                await asyncio.sleep(0.4)
            else:
                await asyncio.sleep(0.1)

    # ---------- ВИДАЛЕННЯ ----------
    @dp.callback_query(F.data.startswith("del_"))
    async def delete_start(c: CallbackQuery, state: FSMContext):
        uid = int(c.data.split("_")[1])
        await state.update_data(target=uid, action="delete")
        await c.message.answer("✍ Напиши причину видалення:")
        await state.set_state(AdminForm.comment)
        await c.answer()

    # ---------- БАН ----------
    @dp.callback_query(F.data.startswith("ban_"))
    async def ban_start(c: CallbackQuery, state: FSMContext):
        uid = int(c.data.split("_")[1])
        await state.update_data(target=uid, action="ban")
        await c.message.answer("✍ Напиши причину бану:")
        await state.set_state(AdminForm.comment)
        await c.answer()

    # ---------- ОБРОБКА КОМЕНТАРЯ ----------
    @dp.message(AdminForm.comment)
    async def finish(m: Message, state: FSMContext):
        if not is_admin(m.from_user):
            return

        data = await state.get_data()
        uid = data["target"]
        action = data["action"]
        reason = m.text

        if action == "delete":
            await delete_profile(uid)

            try:
                await m.bot.send_message(
                    uid,
                    f"❌ Твою анкету видалено.\nПричина:\n{reason}"
                )
            except:
                pass

            await m.answer("✅ Анкету видалено")

        if action == "ban":
            await delete_profile(uid)
            await ban_user(uid, reason)

            try:
                await m.bot.send_message(
                    uid,
                    f"🚫 Ти заблокований.\nПричина:\n{reason}"
                )
            except:
                pass

            await m.answer("🚫 Користувача заблоковано")

        await state.clear()
