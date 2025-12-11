# bot.py
import telebot
from config import logger, BOT_TOKEN
from api_client import APIClient
from handlers import MessageHandlers
from keyboards import create_main_keyboard

def setup_bot() -> telebot.TeleBot:
    """Настройка и запуск бота"""
    logger.info("bot_setup_started")
    
    # Инициализация бота
    bot = telebot.TeleBot(BOT_TOKEN)
    logger.info("bot_initialized")
    
    # Инициализация API клиента
    api = APIClient()
    logger.info("api_client_initialized")
    
    # Проверка доступности API
    if not api.health_check():
        logger.warning("api_not_available")
        print("⚠️  Внимание: API сервер недоступен!")
    else:
        logger.info("api_available")
    
    # Инициализация обработчиков
    handlers = MessageHandlers(bot, api)
    logger.info("handlers_initialized")
    
    # Регистрация обработчиков команд
    @bot.message_handler(commands=['start', 'help'])
    def start_wrapper(message):
        handlers.start_command(message)
    
    @bot.message_handler(commands=['new'])
    def new_note_wrapper(message):
        handlers.new_note_command(message)
    
    @bot.message_handler(commands=['notes'])
    def notes_wrapper(message):
        handlers.list_notes_command(message)
    
    @bot.message_handler(commands=['graph'])
    def graph_wrapper(message):
        handlers.graph_command(message)
    
    # Обработчик всех сообщений
    @bot.message_handler(func=lambda message: True)
    def all_messages_wrapper(message):
        handlers.handle_all_messages(message)
    
    # Обработчик callback-запросов (простой пример)
    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        logger.info("callback_received",
                   user_id=call.from_user.id,
                   data=call.data)
        
        if call.data == "text_tree":
            bot.answer_callback_query(call.id, "Текстовое дерево")
            # TODO: реализовать логику
        elif call.data == "image_graph":
            bot.answer_callback_query(call.id, "Граф в виде изображения")
            # TODO: реализовать логику
    
    logger.info("bot_setup_completed")
    return bot

def main():
    """Основная функция запуска"""
    try:
        logger.info("bot_starting")
        
        bot = setup_bot()
        
        print("=" * 50)
        print("🤖 Zettelkasten Bot запущен!")
        print(f"📡 API сервер: {APIClient().base_url}")
        print(f"📝 Уровень логирования: {logger._logger.level}")
        print("=" * 50)
        
        # Запуск бота
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
        
    except telebot.apihelper.ApiTelegramException as e:
        logger.critical("bot_token_error", error=str(e))
        print(f"❌ Ошибка токена: {e}")
    except KeyboardInterrupt:
        logger.info("bot_stopped_by_user")
        print("\n👋 Бот остановлен пользователем")
    except Exception as e:
        logger.critical("bot_fatal_error", error=str(e), exc_info=True)
        print(f"❌ Фатальная ошибка: {e}")
        raise

if __name__ == "__main__":
    main()