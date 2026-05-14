#!/usr/bin/env python3
"""
Telegram-бот для управления каналом
"""

import os
import json
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Хранилище данных (в реальном проекте лучше использовать БД)
DATA_FILE = "bot_data.json"

def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "channels": {},  # {user_id: channel_id}
            "spam_tasks": {}  # {user_id: {"active": False, "channel_id": None}}
        }

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

data = load_data()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие и помощь"""
    await update.message.reply_text(
        "👋 Привет! Я бот для управления каналом.\n\n"
        "Команды:\n"
        "/setchannel @канал - привязать канал\n"
        "/send текст - отправить текст в канал\n"
        "/sendfile - отправить файл в канал (после команды пришли файл)\n"
        "/spam @канал - начать спам 'о нет фимоз'\n"
        "/stopspam - остановить спам\n"
        "/status - показать статус"
    )

async def set_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Привязка канала к пользователю"""
    user_id = str(update.effective_user.id)
    
    if not context.args:
        await update.message.reply_text("❌ Укажи канал: /setchannel @канал")
        return
    
    channel = context.args[0]
    if not channel.startswith("@"):
        channel = "@" + channel
    
    data["channels"][user_id] = channel
    save_data(data)
    await update.message.reply_text(f"✅ Канал {channel} привязан!")

async def send_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка текста в канал"""
    user_id = str(update.effective_user.id)
    
    if user_id not in data["channels"]:
        await update.message.reply_text("❌ Сначала привяжи канал: /setchannel @канал")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Напиши текст после команды: /send Привет!")
        return
    
    text = " ".join(context.args)
    channel = data["channels"][user_id]
    
    try:
        await context.bot.send_message(chat_id=channel, text=text)
        await update.message.reply_text(f"✅ Отправлено в {channel}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def send_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка файла в канал"""
    user_id = str(update.effective_user.id)
    
    if user_id not in data["channels"]:
        await update.message.reply_text("❌ Сначала привяжи канал: /setchannel @канал")
        return
    
    # Проверяем, есть ли файл в сообщении
    if not update.message.reply_to_message or not update.message.reply_to_message.document:
        await update.message.reply_text("❌ Ответь на сообщение с файлом командой /sendfile")
        return
    
    channel = data["channels"][user_id]
    file = update.message.reply_to_message.document
    
    try:
        await context.bot.send_document(chat_id=channel, document=file.file_id)
        await update.message.reply_text(f"✅ Файл отправлен в {channel}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус"""
    user_id = str(update.effective_user.id)
    channel = data["channels"].get(user_id, "не привязан")
    spam = data["spam_tasks"].get(user_id, {})
    spam_status = "активен" if spam.get("active") else "остановлен"
    
    await update.message.reply_text(
        f"📊 Статус:\n"
        f"Канал: {channel}\n"
        f"Спам: {spam_status}"
    )

async def spam_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запуск спама"""
    user_id = str(update.effective_user.id)
    
    # Определяем канал
    if context.args:
        channel = context.args[0]
        if not channel.startswith("@"):
            channel = "@" + channel
    elif user_id in data["channels"]:
        channel = data["channels"][user_id]
    else:
        await update.message.reply_text("❌ Привяжи канал: /setchannel @канал или укажи: /spam @канал")
        return
    
    data["spam_tasks"][user_id] = {"active": True, "channel": channel}
    save_data(data)
    
    await update.message.reply_text(f"🚀 Спам запущен в {channel}! /stopspam для остановки")
    
    # Запускаем спам в фоне
    async def spam_loop():
        while data.get("spam_tasks", {}).get(user_id, {}).get("active"):
            try:
                await context.bot.send_message(chat_id=channel, text="о нет фимоз 😱")
                await asyncio.sleep(1)  # Пауза 1 секунда между сообщениями
            except Exception as e:
                print(f"Spam error: {e}")
                break
        if user_id in data["spam_tasks"]:
            data["spam_tasks"][user_id]["active"] = False
            save_data(data)
    
    asyncio.create_task(spam_loop())

async def spam_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Остановка спама"""
    user_id = str(update.effective_user.id)
    
    if user_id in data["spam_tasks"]:
        data["spam_tasks"][user_id]["active"] = False
        save_data(data)
        await update.message.reply_text("🛑 Спам остановлен!")
    else:
        await update.message.reply_text("❌ Спам не был запущен")

def main():
    BOT_TOKEN = os.environ.get("BOT_TOKEN")
    
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN не указан!")
        return
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setchannel", set_channel))
    app.add_handler(CommandHandler("send", send_message))
    app.add_handler(CommandHandler("sendfile", send_file))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("spam", spam_start))
    app.add_handler(CommandHandler("stopspam", spam_stop))
    
    print("🤖 Бот запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
