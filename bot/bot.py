# bot.py
import telebot
from config import logger, BOT_TOKEN, API_URL, get_log_level
from api_client import APIClient
from handlers import MessageHandlers
from keyboards import create_main_keyboard, create_note_actions_keyboard

# Глобальная переменная для API клиента
api = None

def setup_bot() -> telebot.TeleBot:
    """Настройка и запуск бота"""
    global api
    
    logger.info("bot_setup_started")
    
    # Инициализация бота
    bot = telebot.TeleBot(BOT_TOKEN)
    logger.info("bot_initialized")
    
    # Инициализация API клиента
    api = APIClient()
    logger.info("api_client_initialized")
    
    # Проверка доступности API
    if not api.health_check():
        logger.warning("api_not_available", api_url=API_URL)
        print(f"⚠️  Внимание: API сервер недоступен! ({API_URL})")
    else:
        logger.info("api_available", api_url=API_URL)
    
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
    
    @bot.message_handler(commands=['search'])
    def search_wrapper(message):
        bot.send_message(
            message.chat.id,
            "🔍 Введите поисковый запрос:",
            reply_markup=create_main_keyboard()
        )
    
    # Обработчик всех сообщений
    @bot.message_handler(func=lambda message: True)
    def all_messages_wrapper(message):
        handlers.handle_all_messages(message)
    
    # Обработчик callback-запросов для заметок и визуализации
    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        logger.info("callback_received",
                   user_id=call.from_user.id,
                   data=call.data)
        
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        
        if call.data == "text_tree":
            bot.answer_callback_query(call.id, "Текстовое дерево")
            send_text_tree(bot, chat_id, user_id)
            
        elif call.data == "image_graph":
            bot.answer_callback_query(call.id, "Граф в виде изображения")
            send_image_graph(bot, chat_id, user_id)
            
        elif call.data.startswith("view_note_"):
            note_id = int(call.data.replace("view_note_", ""))
            bot.answer_callback_query(call.id, f"Просмотр заметки {note_id}")
            show_note_details(bot, chat_id, user_id, note_id, detailed=False)
            
        elif call.data.startswith("detail_note_"):
            note_id = int(call.data.replace("detail_note_", ""))
            bot.answer_callback_query(call.id, f"Подробности заметки {note_id}")
            show_note_details(bot, chat_id, user_id, note_id, detailed=True)
            
        elif call.data.startswith("delete_note_"):
            note_id = int(call.data.replace("delete_note_", ""))
            bot.answer_callback_query(call.id, f"Удаление заметки {note_id}")
            delete_note_confirmation(bot, call, note_id, user_id)
            
        elif call.data.startswith("confirm_delete_"):
            note_id = int(call.data.replace("confirm_delete_", ""))
            confirm_delete_handler(bot, call, note_id, user_id)
            
        elif call.data.startswith("cancel_delete_"):
            cancel_delete_handler(bot, call)
            
        elif call.data.startswith("page_"):
            page = int(call.data.replace("page_", ""))
            bot.answer_callback_query(call.id, f"Страница {page + 1}")
            show_notes_page(bot, call, user_id, page)
    
    logger.info("bot_setup_completed")
    return bot

def send_text_tree(bot, chat_id, user_id):
    """Отправить текстовое дерево заметок"""
    try:
        data = api.get_note_graph(user_id)
        
        if not data.get('notes'):
            bot.send_message(chat_id, "📭 У вас пока нет заметок для построения дерева.")
            return
        
        tree_text = "🌳 Дерево заметок:\n\n"
        
        for note_id, note_info in data['notes'].items():
            tree_text += f"📄 {note_info.get('title', 'Без названия')} (ID: {note_id})\n"
            
            # Показываем связи
            links = note_info.get('links', [])
            if links:
                tree_text += "  └── Связано с: "
                linked_titles = []
                for link in links:
                    target_note = data['notes'].get(str(link))
                    if target_note:
                        linked_titles.append(target_note.get('title', 'Без названия')[:20])
                
                if linked_titles:
                    tree_text += ", ".join(linked_titles) + "\n"
                else:
                    tree_text += "нет связей\n"
            else:
                tree_text += "  └── Нет связей\n"
        
        bot.send_message(chat_id, tree_text)
        
    except Exception as e:
        logger.error("send_text_tree_failed", error=str(e))
        bot.send_message(chat_id, "❌ Ошибка при построении дерева заметок.")

def send_image_graph(bot, chat_id, user_id):
    """Отправить граф в виде текстового представления (временно вместо изображения)"""
    try:
        data = api.get_note_graph(user_id)
        
        if not data.get('notes'):
            bot.send_message(chat_id, "📭 У вас пока нет заметок для построения графа.")
            return
        
        # Создаем простое текстовое представление графа
        notes_count = len(data['notes'])
        graph_text = f"🖼️ Граф заметок ({notes_count} заметок):\n\n"
        
        # Список всех заметок
        for i, (note_id, note_info) in enumerate(data['notes'].items(), 1):
            title = note_info.get('title', 'Без названия')
            links = note_info.get('links', [])
            
            graph_text += f"{i}. 📄 {title}\n"
            if links:
                graph_text += f"   └── Связи: {len(links)}\n"
        
        graph_text += "\n📊 Матрица связей:\n"
        graph_text += "   (1 - есть связь, 0 - нет связи)\n\n"
        
        # Создаем простую матрицу
        note_ids = list(data['notes'].keys())
        for i, from_id in enumerate(note_ids, 1):
            row = []
            for j, to_id in enumerate(note_ids, 1):
                from_info = data['notes'][from_id]
                if str(to_id) in [str(link) for link in from_info.get('links', [])]:
                    row.append("1")
                else:
                    row.append("0")
            
            graph_text += f"{i}: {' '.join(row)}\n"
        
        bot.send_message(chat_id, graph_text)
        
    except Exception as e:
        logger.error("send_image_graph_failed", error=str(e))
        bot.send_message(chat_id, "❌ Ошибка при построении графа. Используйте текстовое дерево.")

def show_note_details(bot, chat_id, user_id, note_id, detailed=False):
    """Показать детали заметки"""
    try:
        note = api.get_note_by_id(note_id, user_id)
        
        if not note:
            bot.send_message(chat_id, f"❌ Заметка с ID {note_id} не найдена.")
            return
        
        if detailed:
            message_text = f"📋 Подробности заметки:\n\n"
            message_text += f"🆔 ID: {note.get('id')}\n"
            message_text += f"📝 Заголовок: {note.get('title')}\n\n"
            message_text += f"📄 Содержание:\n{note.get('content')}\n\n"
            
            tags = note.get('tags')
            if tags:
                message_text += f"🏷️ Теги: {tags}\n"
            
            created_at = note.get('created_at')
            if created_at:
                message_text += f"📅 Создана: {created_at}\n"
            
            bot.send_message(chat_id, message_text)
        else:
            # Краткое представление с кнопками действий
            message_text = f"📄 {note.get('title', 'Без названия')}\n\n"
            content = note.get('content', '')
            if len(content) > 150:
                message_text += f"{content[:150]}...\n"
            else:
                message_text += f"{content}\n"
            
            message_text += f"\n🆔 ID: {note_id}"
            
            keyboard = create_note_actions_keyboard(note_id)
            bot.send_message(chat_id, message_text, reply_markup=keyboard)
            
    except Exception as e:
        logger.error("show_note_details_failed", error=str(e))
        bot.send_message(chat_id, "❌ Ошибка при получении информации о заметке.")

def delete_note_confirmation(bot, call, note_id, user_id):
    """Запрос подтверждения удаления заметки"""
    try:
        note = api.get_note_by_id(note_id, user_id)
        
        if not note:
            bot.answer_callback_query(call.id, "Заметка не найдена", show_alert=True)
            return
        
        from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{note_id}"),
            InlineKeyboardButton("❌ Нет, отмена", callback_data=f"cancel_delete_{note_id}")
        )
        
        bot.send_message(
            call.message.chat.id,
            f"🗑️ Вы уверены, что хотите удалить заметку?\n\n"
            f"«{note.get('title', 'Без названия')}»\n\n"
            f"⚠️ Это действие нельзя отменить!",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error("delete_note_confirmation_failed", error=str(e))
        bot.answer_callback_query(call.id, "Ошибка при подтверждении удаления", show_alert=True)

def confirm_delete_handler(bot, call, note_id, user_id):
    """Обработчик подтверждения удаления"""
    try:
        success = api.delete_note(note_id, user_id)
        if success:
            bot.answer_callback_query(call.id, "✅ Заметка удалена", show_alert=True)
            bot.edit_message_text(
                "✅ Заметка успешно удалена.",
                call.message.chat.id,
                call.message.message_id
            )
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка при удалении", show_alert=True)
    except Exception as e:
        logger.error("delete_handler_failed", error=str(e))
        bot.answer_callback_query(call.id, "❌ Ошибка при удалении", show_alert=True)

def cancel_delete_handler(bot, call):
    """Обработчик отмены удаления"""
    bot.answer_callback_query(call.id, "❌ Удаление отменено")
    bot.edit_message_text(
        "❌ Удаление отменено.",
        call.message.chat.id,
        call.message.message_id
    )

def show_notes_page(bot, call, user_id, page):
    """Показать страницу со списком заметок"""
    try:
        from handlers import MessageHandlers
        from telebot import TeleBot
        
        # Получаем заметки
        notes = api.get_user_notes(user_id)
        if not notes:
            bot.answer_callback_query(call.id, "Нет заметок", show_alert=True)
            return
        
        # Создаем временный обработчик для отображения
        temp_bot = TeleBot("dummy")
        handlers = MessageHandlers(temp_bot, api)
        
        # Получаем клавиатуру для страницы
        from keyboards import create_notes_list_keyboard
        keyboard = create_notes_list_keyboard(notes, page=page, per_page=10)
        
        # Обновляем сообщение
        bot.edit_message_text(
            f"📚 Ваши заметки ({len(notes)} всего, стр. {page + 1}):",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error("show_notes_page_failed", error=str(e))
        bot.answer_callback_query(call.id, "Ошибка при загрузке страницы", show_alert=True)

def main():
    """Основная функция запуска"""
    try:
        logger.info("bot_starting")
        
        bot = setup_bot()
        
        print("=" * 50)
        print("🤖 Zettelkasten Bot запущен!")
        print(f"📡 API сервер: {API_URL}")
        print(f"📝 Уровень логирования: {get_log_level()}")
        print("=" * 50)
        
        # Запуск бота с обработкой ошибок
        while True:
            try:
                bot.infinity_polling(timeout=60, long_polling_timeout=60)
            except Exception as e:
                logger.error("polling_error", error=str(e))
                print(f"⚠️  Ошибка polling: {e}. Перезапуск через 5 секунд...")
                import time
                time.sleep(5)
        
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