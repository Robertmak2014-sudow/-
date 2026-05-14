#!/usr/bin/env python3
"""
Telegram-бот с историей разговора через G4F API
"""

import asyncio
import json
from collections import defaultdict
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Твой API-ключ от G4F
API_KEY = "g4f_u_mp5mv7_015c65bee8d10be2bb793e6c368a895619bc9bb8afb6f6a4_02ee448a"
API_URL = "https://g4f.space/v1/chat/completions"
MODEL = "gpt-oss-120b"

# Хранилище истории разговоров
# Формат: {user_id: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
conversations = defaultdict(list)

# Системный промпт (можно изменить)
SYSTEM_PROMPT = "Ты полезный ассистент. Отвечай кратко и по делу."

async def query_g4f(messages: list[dict]) -> str:
    """Отправляет запрос к G4F API и получает ответ"""
    import aiohttp
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    # Добавляем системный промпт в начало
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    
    payload = {
        "model": MODEL,
        "messages": full_messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(API_URL, headers=headers, json=payload) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return f"❌ Ошибка API: {resp.status}"
    except Exception as e:
        return f"❌ Ошибка: {str(e)}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    conversations[user_id] = []  # Очищаем историю при старте
    await update.message.reply_text(
        "👋 Привет! Я бот с историей разговора.\n"
        "Просто напиши мне что-нибудь, и я запомню контекст.\n\n"
        "Команды:\n"
        "/start - начать новый разговор\n"
        "/clear - очистить историю\n"
        "/history - показать историю\n"
        "/model - показать текущую модель"
    )

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Очистка истории"""
    user_id = update.effective_user.id
    conversations[user_id] = []
    await update.message.reply_text("🧹 История разговора очищена!")

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает историю разговора"""
    user_id = update.effective_user.id
    history = conversations.get(user_id, [])
    
    if not history:
        await update.message.reply_text("📭 История пуста.")
        return
    
    text = "📜 *История разговора:*\n\n"
    for i, msg in enumerate(history, 1):
        role = "👤 Вы" if msg["role"] == "user" else "🤖 Бот"
        content = msg["content"][:100] + ("..." if len(msg["content"]) > 100 else "")
        text += f"{i}. {role}: {content}\n"
    
    if len(text) > 4000:
        text = text[:4000] + "\n... (обрезано)"
    
    await update.message.reply_text(text, parse_mode="Markdown")

async def show_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает текущую модель"""
    await update.message.reply_text(f"🧠 Текущая модель: *{MODEL}*", parse_mode="Markdown")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Показываем, что бот печатает
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    
    # Добавляем сообщение пользователя в историю
    conversations[user_id].append({"role": "user", "content": user_message})
    
    # Ограничиваем историю последними 20 сообщениями (10 пар вопрос-ответ)
    if len(conversations[user_id]) > 20:
        conversations[user_id] = conversations[user_id][-20:]
    
    # Отправляем запрос к G4F
    response = await query_g4f(conversations[user_id])
    
    # Добавляем ответ бота в историю
    conversations[user_id].append({"role": "assistant", "content": response})
    
    # Отправляем ответ пользователю
    await update.message.reply_text(response)

def main():
    """Запуск бота"""
    import os
    
    # Получаем токен из переменных окружения (секреты GitHub)
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    
    if not BOT_TOKEN:
        print("❌ Ошибка: Не указан BOT_TOKEN в переменных окружения!")
        return
    
    # Создаём приложение
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear))
    app.add_handler(CommandHandler("history", show_history))
    app.add_handler(CommandHandler("model", show_model))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    print("🤖 Бот запущен!")
    
    # Запускаем бота
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
