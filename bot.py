import logging
import os
from datetime import date, time
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from wiki_fetcher import get_random_wiki_article
from database import Database

load_dotenv()
TOKEN = os.getenv('TOKEN')
if not TOKEN:
    raise ValueError("Добавь TOKEN в .env!")

db = Database()

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user = update.effective_user
    
    db.add_user(
        chat_id=chat_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    db.log_action(chat_id, 'start')
    
    await update.message.reply_text(
        "👋 Привет! Я буду присылать тебе случайные статьи из Википедии каждый день в 9:00.\n\n"
        "Доступные команды:\n"
        "/start - начать работу\n"
        "/random - случайная статья\n"
        "/history - история статей\n"
        "/stats - статистика\n"
        "/random_from_history - случайная статья из истории\n"
        "/stop_daily - остановить рассылку\n\n"
        "Первая статья:"
    )
    
    article = get_random_wiki_article()
    if article['url']:
        message = f"🎉 **{article['title']}**\n\n{article['summary']}\n\n[Читать полностью]({article['url']})"
    else:
        message = f"🎉 **{article['title']}**\n\n{article['summary']}"
    
    db.add_sent_article(chat_id, article['title'], article['url'], article['summary'])
    
    await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=bool(article['url']))

async def random_article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db.log_action(chat_id, 'random')
    
    article = get_random_wiki_article()
    if article['url']:
        message = f"📖 **{article['title']}**\n\n{article['summary']}\n\n[Читать полностью]({article['url']})"
    else:
        message = f"📖 **{article['title']}**\n\n{article['summary']}"
    
    db.add_sent_article(chat_id, article['title'], article['url'], article['summary'])
    
    await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=bool(article['url']))

async def stop_daily(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    db.log_action(chat_id, 'stop_daily')
    
    with db.conn:
        db.cursor.execute('UPDATE users SET is_active = FALSE WHERE chat_id = ?', (chat_id,))
    
    await update.message.reply_text(
        "🛑 Ежедневная рассылка остановлена. "
        "Чтобы возобновить, напиши /start.\n"
        "Ты по-прежнему можешь использовать /random для случайных статей."
    )

async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать историю отправленных статей"""
    chat_id = update.effective_chat.id
    db.log_action(chat_id, 'history')
    
    history_articles = db.get_sent_articles_history(chat_id, limit=5)
    
    if not history_articles:
        await update.message.reply_text("📝 История пуста. Начните с команды /random!")
        return
    
    message = "📚 **Последние статьи:**\n\n"
    for i, (title, url, sent_date) in enumerate(history_articles, 1):
        message += f"{i}. [{title}]({url}) - {sent_date}\n\n"
    
    await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать статистику"""
    chat_id = update.effective_chat.id
    db.log_action(chat_id, 'stats')
    
    stats_data = db.get_user_stats(chat_id)
    
    message = "📊 **Ваша статистика:**\n\n"
    message += f"📖 Всего статей прочитано: {stats_data['total_articles']}\n"
    message += f"📅 Статей за последнюю неделю: {stats_data['last_week_articles']}\n"
    
    if stats_data['favorite_topic']:
        title, count = stats_data['favorite_topic']
        message += f"⭐ Самая частая тема: \"{title}\" ({count} раз)\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def random_from_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать случайную статью из истории"""
    chat_id = update.effective_chat.id
    db.log_action(chat_id, 'random_from_history')
    
    article = db.get_random_article_from_history(chat_id)
    
    if not article:
        await update.message.reply_text("📝 История пуста. Начните с команды /random!")
        return
    
    title, url, summary = article
    message = f"🔀 **Случайная из истории:**\n\n**{title}**\n\n{summary}\n\n[Читать полностью]({url})"
    
    await update.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=bool(url))

async def send_daily_article(context: ContextTypes.DEFAULT_TYPE):
    with db.conn:
        db.cursor.execute('SELECT chat_id FROM users WHERE is_active = TRUE')
        active_users = db.cursor.fetchall()
    
    for (chat_id,) in active_users:
        if db.was_article_sent_today(chat_id):
            print(f"Уже отправлено сегодня пользователю {chat_id}.")
            continue
        
        article = get_random_wiki_article()
        if article['url']:
            message = f"🌅 **{article['title']}**\n\n{article['summary']}\n\n[Читать полностью]({article['url']})"
        else:
            message = f"🌅 **{article['title']}**\n\n{article['summary']}"
        
        try:
            await context.bot.send_message(
                chat_id=chat_id, 
                text=message, 
                parse_mode='Markdown', 
                disable_web_page_preview=bool(article['url'])
            )
            db.add_sent_article(chat_id, article['title'], article['url'], article['summary'])
            print(f"Отправлено пользователю {chat_id}: {article['title']}")
        except Exception as e:
            print(f"Ошибка отправки пользователю {chat_id}: {e}")

def main():
    if not TOKEN:
        print("Ошибка: TOKEN в .env!")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("random", random_article))
    application.add_handler(CommandHandler("stop_daily", stop_daily))
    application.add_handler(CommandHandler("history", history))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("random_from_history", random_from_history))
    
    application.job_queue.run_daily(send_daily_article, time=time(6, 0))
    
    print("Бот запущен. /start для настройки. Ctrl+C для остановки.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()