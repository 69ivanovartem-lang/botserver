# keyboards.py
from telebot.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    ReplyKeyboardMarkup, 
    KeyboardButton
)

def create_main_keyboard() -> ReplyKeyboardMarkup:
    """Основная клавиатура"""
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

def create_cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура для отмены"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ Отмена"))
    return keyboard

def create_visualization_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для визуализации"""
    keyboard = InlineKeyboardMarkup()
    keyboard.row(
        InlineKeyboardButton("📊 Текстовое дерево", callback_data="text_tree"),
        InlineKeyboardButton("🖼️ Граф (изображение)", callback_data="image_graph")
    )
    return keyboard

def create_note_actions_keyboard(note_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с заметкой"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_note_{note_id}"),
        InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_note_{note_id}"),
        InlineKeyboardButton("🔗 Связать", callback_data=f"link_note_{note_id}"),
        InlineKeyboardButton("📋 Подробнее", callback_data=f"detail_note_{note_id}")
    )
    return keyboard

def create_notes_list_keyboard(notes: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """Клавиатура со списком заметок"""
    keyboard = InlineKeyboardMarkup()
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    
    for note in notes[start_idx:end_idx]:
        keyboard.add(InlineKeyboardButton(
            f"📄 {note['title'][:30]}...",
            callback_data=f"view_note_{note['id']}"
        ))
    
    # Пагинация
    if len(notes) > per_page:
        row = []
        if page > 0:
            row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
        if end_idx < len(notes):
            row.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))
        if row:
            keyboard.row(*row)
    
    return keyboard