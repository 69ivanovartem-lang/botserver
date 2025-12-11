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
        InlineKeyboardButton("🖼️ Граф (текстовый)", callback_data="image_graph")
    )
    return keyboard

def create_note_actions_keyboard(note_id: int) -> InlineKeyboardMarkup:
    """Клавиатура действий с заметкой"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("📋 Подробнее", callback_data=f"detail_note_{note_id}"),
        InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_note_{note_id}")
    )
    return keyboard

def create_notes_list_keyboard(notes: list, page: int = 0, per_page: int = 10) -> InlineKeyboardMarkup:
    """Клавиатура со списком заметок"""
    keyboard = InlineKeyboardMarkup()
    
    start_idx = page * per_page
    end_idx = start_idx + per_page
    current_notes = notes[start_idx:end_idx]
    
    if not current_notes:
        # Если на странице нет заметок, возвращаемся на первую
        page = 0
        start_idx = 0
        end_idx = per_page
        current_notes = notes[start_idx:end_idx]
    
    for note in current_notes:
        title = note.get('title', 'Без названия')
        note_id = note.get('id', 0)
        
        if len(title) > 30:
            title = title[:27] + "..."
        
        keyboard.add(InlineKeyboardButton(
            f"📄 {title}",
            callback_data=f"view_note_{note_id}"
        ))
    
    # Пагинация
    if len(notes) > per_page:
        row = []
        if page > 0:
            row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"page_{page-1}"))
        
        page_info = f"Стр. {page + 1}/{(len(notes) + per_page - 1) // per_page}"
        row.append(InlineKeyboardButton(page_info, callback_data="page_info"))
        
        if end_idx < len(notes):
            row.append(InlineKeyboardButton("Вперед ➡️", callback_data=f"page_{page+1}"))
        
        if row:
            keyboard.row(*row)
    
    # Кнопка возврата
    keyboard.add(InlineKeyboardButton("🔙 Назад в меню", callback_data="back_to_menu"))
    
    return keyboard

def create_delete_confirmation_keyboard(note_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения удаления"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_{note_id}"),
        InlineKeyboardButton("❌ Нет, отмена", callback_data=f"cancel_delete_{note_id}")
    )
    return keyboard