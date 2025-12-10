import telebot
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)
import requests
import logging
import structlog
import os

# Настройка логирования
structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    processors=[
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Конфигурация
BOT_TOKEN = os.getenv("BOT_TOKEN", "8250247525:AAFIixru3WzZGxdPoQ-e35PvegpPSGzzn7s")
API_URL = os.getenv("API_URL", "http://localhost:8000")
bot = telebot.TeleBot(BOT_TOKEN)

class APIClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def add_note(self, user_id, title, content, tags=None):
        """Создать новую заметку"""
        try:
            response = requests.post(
                f"{self.base_url}/api/notes",
                json={
                    "user_id": user_id,
                    "title": title,
                    "content": content,
                    "tags": tags
                }
            )
            return response.json() if response.status_code == 201 else None
        except Exception as e:
            logger.error("add_note_failed", error=str(e))
            return None
    
    def get_user_notes(self, user_id):
        """Получить все заметки пользователя"""
        try:
            response = requests.get(f"{self.base_url}/api/notes/{user_id}")
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            logger.error("get_notes_failed", error=str(e))
            return []
    
    def search_notes(self, user_id, query):
        """Поиск заметок"""
        try:
            response = requests.get(
                f"{self.base_url}/api/notes/{user_id}/search",
                params={"q": query}
            )
            return response.json() if response.status_code == 200 else []
        except Exception as e:
            logger.error("search_notes_failed", error=str(e))
            return []
    
    def get_note_graph(self, user_id):
        """Получить граф заметок"""
        try:
            response = requests.get(f"{self.base_url}/api/notes/{user_id}/graph")
            return response.json() if response.status_code == 200 else {"notes": {}, "graph": {}}
        except Exception as e:
            logger.error("get_graph_failed", error=str(e))
            return {"notes": {}, "graph": {}}
    
    def add_link(self, from_note_id, to_note_id, user_id):
        """Добавить связь между заметками"""
        try:
            response = requests.post(
                f"{self.base_url}/api/links",
                json={
                    "from_note_id": from_note_id,
                    "to_note_id": to_note_id,
                    "user_id": user_id
                }
            )
            return response.status_code == 201
        except Exception as e:
            logger.error("add_link_failed", error=str(e))
            return False
    
    def delete_note(self, note_id, user_id):
        """Удалить заметку"""
        try:
            response = requests.delete(
                f"{self.base_url}/api/notes/{note_id}",
                params={"user_id": user_id}
            )
            return response.status_code == 200
        except Exception as e:
            logger.error("delete_note_failed", error=str(e))
            return False

# Инициализация клиента API
api = APIClient(API_URL)

# Создание клавиатур (оставить без изменений из вашего кода)
def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        KeyboardButton("📝 Новая заметка"),
        KeyboardButton("📚 Мои заметки"),
        KeyboardButton("🔍 Поиск"),
        KeyboardButton("🌳 Дерево заметок"),
        KeyboardButton("🖼️ Граф заметок"),
        KeyboardButton("ℹ️ Помощь")
    )
    return keyboard

def create_visualization_keyboard():
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("📊 Текстовое дерево", callback_data="text_tree"),
        InlineKeyboardButton("🖼️ Граф (изображение)", callback_data="image_graph")
    )
    return keyboard

# Состояния пользователей
user_states = {}

# Обработчики команд (адаптировать для работы с API)
@bot.message_handler(commands=['start'])
def start_command(message):
    welcome_text = """
🤖 Добро пожаловать в Zettelkasten Bot!
💡 Используйте кнопки ниже для быстрого доступа к командам!
📚 Основные команды:
/new - Создать новую заметку
/notes - Показать все заметки
/search - Поиск по заметкам
/tree - Текстовое дерево заметок
/graph - Граф заметок
/help - Помощь
    """
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=create_main_keyboard()
    )

@bot.message_handler(commands=['new'])
def new_note_command(message):
    user_states[message.chat.id] = {'state': 'waiting_title'}
    bot.send_message(
        message.chat.id,
        "📝 Создание новой заметки\n\nВведите заголовок заметки:",
        reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отмена"))
    )

@bot.message_handler(commands=['notes'])
def list_notes_command(message):
    notes = api.get_user_notes(message.from_user.id)
    if not notes:
        bot.send_message(
            message.chat.id,
            "📭 У вас пока нет заметок.",
            reply_markup=create_main_keyboard()
        )
        return
    
    keyboard = InlineKeyboardMarkup()
    for note in notes:
        keyboard.add(InlineKeyboardButton(
            f"📄 {note['title'][:30]}...",
            callback_data=f"view_note_{note['id']}"
        ))
    
    bot.send_message(
        message.chat.id,
        f"📚 Ваши заметки ({len(notes)}):",
        reply_markup=keyboard
    )

@bot.message_handler(commands=['graph'])
def graph_command(message):
    try:
        data = api.get_note_graph(message.from_user.id)
        if not data.get('notes'):
            bot.send_message(
                message.chat.id,
                "📭 У вас пока нет заметок для построения графа.",
                reply_markup=create_main_keyboard()
            )
            return
        
        bot.send_message(
            message.chat.id,
            "🎨 Визуализация графа заметок",
            reply_markup=create_visualization_keyboard()
        )
    except Exception as e:
        logger.error("graph_command_failed", error=str(e))
        bot.send_message(
            message.chat.id,
            "❌ Ошибка при построении графа.",
            reply_markup=create_main_keyboard()
        )

# Остальные обработчики остаются похожими, но используют API клиент
# ...

# Обработчик всех сообщений
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if chat_id in user_states:
        state = user_states[chat_id]['state']
        
        if state == 'waiting_title':
            user_states[chat_id] = {
                'state': 'waiting_content',
                'title': message.text
            }
            bot.send_message(
                chat_id,
                "✍️ Теперь введите содержание заметки:",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отмена"))
            )
        
        elif state == 'waiting_content':
            user_states[chat_id] = {
                'state': 'waiting_tags',
                'title': user_states[chat_id]['title'],
                'content': message.text
            }
            bot.send_message(
                chat_id,
                "🏷️ Введите теги через запятую (необязательно):",
                reply_markup=ReplyKeyboardMarkup(resize_keyboard=True).add(KeyboardButton("❌ Отмена"))
            )
        
        elif state == 'waiting_tags':
            result = api.add_note(
                user_id=user_id,
                title=user_states[chat_id]['title'],
                content=user_states[chat_id]['content'],
                tags=message.text.strip() or None
            )
            
            del user_states[chat_id]
            
            if result:
                bot.send_message(
                    chat_id,
                    f"✅ Заметка создана! (ID: {result.get('id')})",
                    reply_markup=create_main_keyboard()
                )
            else:
                bot.send_message(
                    chat_id,
                    "❌ Ошибка при создании заметки.",
                    reply_markup=create_main_keyboard()
                )
    
    else:
        # Обработка поиска и других сообщений
        if message.text and not message.text.startswith('/'):
            notes = api.search_notes(user_id, message.text)
            # ... обработка результатов поиска

if __name__ == "__main__":
    logger.info("bot_started")
    print(f"🤖 Zettelkasten Bot запущен!")
    print(f"📡 API сервер: {API_URL}")
    bot.infinity_polling()