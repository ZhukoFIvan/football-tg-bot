"""
Обработчики главного меню бота
"""
from aiogram import Router, F
from aiogram.types import Message

router = Router()


@router.message(F.text == "Привет")
async def hello(message: Message):
    """Ответ на Привет"""
    await message.answer(f"Привет, {message.from_user.first_name}! 👋")


@router.message(F.text == "Как дела?")
async def how_are_you(message: Message):
    """Ответ на Как дела?"""
    await message.answer("Отлично! Спасибо, что спросили! 😊")
