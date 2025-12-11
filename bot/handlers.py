# handlers.py
import telebot
from typing import Dict, Any
from config import logger
from api_client import APIClient
from keyboards import (
    create_main_keyboard,
    create_cancel_keyboard,
    create_visualization_keyboard,
    create_note_actions_keyboard,
    create_notes_list_keyboard
)

class MessageHandlers:
    def __init__(self, bot: telebot.TeleBot, api_client: APIClient):
        self.bot = bot
        self.api = api_client
        self.user_states: Dict[int, Dict] = {}
    
    def start_command(self, message: telebot.types.Message) -> None:
        """Обработчик команды /start"""
        logger.info("start_command", 
                   user_id=message.from_user.id,
                   username=message.from_user.username)
        
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
        
        self.bot.send_message(
            message.chat.id,
            welcome_text,
            reply_markup=create_main_keyboard()
        )
        
        logger.debug("start_command_completed", user_id=message.from_user.id)
    
    def new_note_command(self, message: telebot.types.Message) -> None:
        """Обработчик команды /new"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        logger.info("new_note_command", user_id=user_id)
        
        self.user_states[chat_id] = {'state': 'waiting_title'}
        self.bot.send_message(
            chat_id,
            "📝 Создание новой заметки\n\nВведите заголовок заметки:",
            reply_markup=create_cancel_keyboard()
        )
        
        logger.debug("waiting_for_title", user_id=user_id)
    
    def list_notes_command(self, message: telebot.types.Message) -> None:
        """Обработчик команды /notes"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        logger.info("list_notes_command", user_id=user_id)
        
        notes = self.api.get_user_notes(user_id)
        
        if not notes:
            self.bot.send_message(
                chat_id,
                "📭 У вас пока нет заметок.",
                reply_markup=create_main_keyboard()
            )
            logger.debug("no_notes_found", user_id=user_id)
            return
        
        keyboard = create_notes_list_keyboard(notes)
        
        self.bot.send_message(
            chat_id,
            f"📚 Ваши заметки ({len(notes)}):",
            reply_markup=keyboard
        )
        
        logger.debug("notes_list_sent", 
                    user_id=user_id,
                    notes_count=len(notes))
    
    def graph_command(self, message: telebot.types.Message) -> None:
        """Обработчик команды /graph"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        
        logger.info("graph_command", user_id=user_id)
        
        try:
            data = self.api.get_note_graph(user_id)
            
            if not data.get('notes'):
                self.bot.send_message(
                    chat_id,
                    "📭 У вас пока нет заметок для построения графа.",
                    reply_markup=create_main_keyboard()
                )
                logger.debug("no_notes_for_graph", user_id=user_id)
                return
            
            self.bot.send_message(
                chat_id,
                "🎨 Визуализация графа заметок",
                reply_markup=create_visualization_keyboard()
            )
            
            logger.debug("graph_options_sent", user_id=user_id)
            
        except Exception as e:
            logger.error("graph_command_failed",
                        user_id=user_id,
                        error=str(e),
                        exc_info=True)
            self.bot.send_message(
                chat_id,
                "❌ Ошибка при построении графа.",
                reply_markup=create_main_keyboard()
            )
    
    def handle_all_messages(self, message: telebot.types.Message) -> None:
        """Обработчик всех сообщений"""
        chat_id = message.chat.id
        user_id = message.from_user.id
        
        logger.debug("message_received",
                    user_id=user_id,
                    chat_id=chat_id,
                    text_length=len(message.text) if message.text else 0)
        
        if chat_id in self.user_states:
            self._handle_state_message(message)
        else:
            self._handle_normal_message(message)
    
   # handlers.py - исправленная функция _handle_state_message
def _handle_state_message(self, message: telebot.types.Message) -> None:
    """Обработка сообщений в состоянии"""
    chat_id = message.chat.id
    user_id = message.from_user.id
    
    if chat_id not in self.user_states:
        return
    
    state = self.user_states[chat_id]['state']
    
    logger.debug("state_message",
                user_id=user_id,
                state=state,
                text_preview=message.text[:50] if message.text else "")
    
    if message.text == "❌ Отмена":
        del self.user_states[chat_id]
        self.bot.send_message(
            chat_id,
            "❌ Операция отменена.",
            reply_markup=create_main_keyboard()
        )
        logger.info("operation_cancelled", user_id=user_id)
        return
    
    if state == 'waiting_title':
        self.user_states[chat_id] = {
            'state': 'waiting_content',
            'title': message.text
        }
        self.bot.send_message(
            chat_id,
            "✍️ Теперь введите содержание заметки:",
            reply_markup=create_cancel_keyboard()
        )
        
    elif state == 'waiting_content':
        if 'title' not in self.user_states[chat_id]:
            logger.error("title_not_found_in_state", chat_id=chat_id)
            del self.user_states[chat_id]
            self.bot.send_message(
                chat_id,
                "❌ Ошибка: данные заголовка не найдены.",
                reply_markup=create_main_keyboard()
            )
            return
            
        self.user_states[chat_id] = {
            'state': 'waiting_tags',
            'title': self.user_states[chat_id]['title'],
            'content': message.text
        }
        self.bot.send_message(
            chat_id,
            "🏷️ Введите теги через запятую (необязательно):",
            reply_markup=create_cancel_keyboard()
        )
        
    elif state == 'waiting_tags':
        if 'title' not in self.user_states[chat_id] or 'content' not in self.user_states[chat_id]:
            logger.error("data_not_found_in_state", chat_id=chat_id)
            del self.user_states[chat_id]
            self.bot.send_message(
                chat_id,
                "❌ Ошибка: данные заметки не найдены.",
                reply_markup=create_main_keyboard()
            )
            return
            
        # Сохраняем данные перед удалением состояния
        title = self.user_states[chat_id]['title']
        content = self.user_states[chat_id]['content']
        
        result = self.api.add_note(
            user_id=user_id,
            title=title,
            content=content,
            tags=message.text.strip() or None
        )
        
        del self.user_states[chat_id]
        
        if result:
            self.bot.send_message(
                chat_id,
                f"✅ Заметка '{title[:30]}...' создана! (ID: {result.get('id')})",
                reply_markup=create_main_keyboard()
            )
            logger.info("note_created",
                       user_id=user_id,
                       note_id=result.get('id'))
        else:
            self.bot.send_message(
                chat_id,
                "❌ Ошибка при создании заметки.",
                reply_markup=create_main_keyboard()
            )
            logger.error("note_creation_failed", user_id=user_id)
    
    def _handle_normal_message(self, message: telebot.types.Message) -> None:
        """Обработка обычных сообщений"""
        user_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text
        
        if not text:
            return
        
        logger.debug("normal_message",
                    user_id=user_id,
                    text_preview=text[:50])
        
        # Обработка текстовых команд с кнопок
        if text == "📝 Новая заметка":
            self.new_note_command(message)
        elif text == "📚 Мои заметки":
            self.list_notes_command(message)
        elif text == "🔍 Поиск":
            self.bot.send_message(
                chat_id,
                "🔍 Введите поисковый запрос:",
                reply_markup=create_cancel_keyboard()
            )
            logger.debug("waiting_search_query", user_id=user_id)
        elif text == "ℹ️ Помощь":
            self.start_command(message)  # Помощь = стартовое сообщение
        else:
            # Поиск по умолчанию
            notes = self.api.search_notes(user_id, text)
            self._send_search_results(chat_id, notes, text)
    
    def _send_search_results(self, chat_id: int, notes: list, query: str) -> None:
        """Отправка результатов поиска"""
        if not notes:
            self.bot.send_message(
                chat_id,
                f"🔍 По запросу '{query}' ничего не найдено.",
                reply_markup=create_main_keyboard()
            )
            return
        
        keyboard = create_notes_list_keyboard(notes)
        self.bot.send_message(
            chat_id,
            f"🔍 Найдено заметок: {len(notes)}\nЗапрос: '{query}'",
            reply_markup=keyboard
        )