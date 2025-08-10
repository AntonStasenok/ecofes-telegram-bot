import os
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.services.database import SessionLocal, Lead, UserQuery
from bot.utils.helpers import is_valid_email
from bot.services.email_sender import send_lead_email
from bot.services.rag_engine import RAGEngine
from bot.services.llm_service import query_openrouter
from bot.services.query_classifier import QueryClassifier
from bot.services.chat_responses import ChatResponses
from datetime import datetime
import logging
import re

# Настройка логирования
logger = logging.getLogger(__name__)

# 🔥 ОБЯЗАТЕЛЬНО: объявить ДО создания роутера
SUPPORT_CHAT_ID = os.getenv("SUPPORT_CHAT_ID")
if SUPPORT_CHAT_ID:
    try:
        SUPPORT_CHAT_ID = int(SUPPORT_CHAT_ID)
    except ValueError:
        SUPPORT_CHAT_ID = None
else:
    SUPPORT_CHAT_ID = None

print(f"🔧 [DEBUG] SUPPORT_CHAT_ID = {SUPPORT_CHAT_ID}")

# Создание роутера
router = Router()

# Инициализация компонентов
rag_engine = RAGEngine()
query_classifier = QueryClassifier()
chat_responses = ChatResponses()

# ========================= КЛАВИАТУРЫ =========================

def get_inline_menu():
    """Главное меню бота"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Подобрать масло", callback_data="start_selection")],
        [InlineKeyboardButton(text="📋 Оставить заявку", callback_data="start_lead")],
        [InlineKeyboardButton(text="ℹ️ Узнать больше", callback_data="show_faq")],
        [InlineKeyboardButton(text="📞 Связаться с менеджером", callback_data="start_support_chat")]
    ])

def get_faq_keyboard():
    """Кнопки под FAQ"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Оставить контакты", callback_data="start_lead")],
        [InlineKeyboardButton(text="🔍 Подобрать масло", callback_data="start_selection")],
        [InlineKeyboardButton(text="🏠 Вернуться в меню", callback_data="main_menu")]
    ])

def get_support_menu():
    """Меню поддержки"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Начать чат с менеджером", callback_data="start_support_chat")],
        [InlineKeyboardButton(text="🏠 Вернуться в меню", callback_data="main_menu")]
    ])

def get_end_chat_keyboard():
    """Кнопка для завершения чата с поддержкой"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Завершить диалог", callback_data="end_support_chat")]
    ])

def get_selection_keyboard():
    """Меню для подбора масла"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚗 Легковой автомобиль", callback_data="select_car")],
        [InlineKeyboardButton(text="🚛 Грузовик/коммерческий", callback_data="select_truck")],
        [InlineKeyboardButton(text="🏍️ Мотоцикл", callback_data="select_moto")],
        [InlineKeyboardButton(text="❄️ Снегоход", callback_data="select_snow")],
        [InlineKeyboardButton(text="🛥️ Водный транспорт", callback_data="select_water")],
        [InlineKeyboardButton(text="🏭 Промышленная техника", callback_data="select_industrial")],
        [InlineKeyboardButton(text="🏠 Вернуться в меню", callback_data="main_menu")]
    ])

# ========================= FSM СОСТОЯНИЯ =========================

class LeadForm(StatesGroup):
    """Состояния для сбора данных лида"""
    waiting_for_name = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_industry = State()

class SelectionForm(StatesGroup):
    """Состояния для подбора масла"""
    waiting_for_vehicle_info = State()

# ========================= КОМАНДЫ И МЕНЮ =========================

@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    first_name = message.from_user.first_name or "Пользователь"

    welcome_text = (
        f"Здравствуйте, {first_name}!\n\n"
        "Вы в официальном боте <b>ECOFES</b> — российского лидера в разработке "
        "инновационных и высококачественных смазочных материалов для автомобилей и промышленности.\n\n"
        "Здесь вы можете:\n"
        "• Подобрать подходящее масло для вашей техники\n"
        "• Узнать о продуктах и их преимуществах\n"
        "• Оставить свои контакты, чтобы получить консультацию специалиста\n\n"
        "Выберите команду в меню или задайте вопрос — "
        "и мы поможем обеспечить надежность и эффективность вашего оборудования "
        "с помощью передовых решений ECOFES.\n\n"
        "Спасибо, что выбираете качество и технологическое превосходство!"
    )

    # Очищаем состояние и удаляем старую клавиатуру
    await state.clear()
    await message.answer(welcome_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    
    # Отдельно отправляем inline-меню
    await message.answer("Чем могу помочь?", reply_markup=get_inline_menu())

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    """Возврат в главное меню"""
    await state.clear()  # Очищаем состояние
    await callback.message.edit_text("Чем могу помочь?", reply_markup=get_inline_menu())
    await callback.answer()

# ========================= ПОДБОР МАСЛА =========================

@router.callback_query(F.data == "start_selection")
async def start_selection_callback(callback: CallbackQuery, state: FSMContext):
    """Запуск подбора масла"""
    await state.clear()
    selection_text = (
        "🔍 <b>Подбор масла ECOFES</b>\n\n"
        "Выберите тип вашей техники, чтобы получить персональные рекомендации:"
    )
    await callback.message.edit_text(selection_text, reply_markup=get_selection_keyboard(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("select_"))
async def vehicle_type_callback(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора типа техники"""
    vehicle_types = {
        "select_car": "🚗 легкового автомобиля",
        "select_truck": "🚛 грузового/коммерческого транспорта", 
        "select_moto": "🏍️ мотоцикла",
        "select_snow": "❄️ снегохода",
        "select_water": "🛥️ водного транспорта",
        "select_industrial": "🏭 промышленной техники"
    }
    
    vehicle_type = vehicle_types.get(callback.data, "техники")
    
    await state.update_data(vehicle_type=callback.data)
    
    info_text = (
        f"Отлично! Подбираем масло для {vehicle_type}.\n\n"
        "Пожалуйста, укажите:\n"
        "• Марка и модель\n"
        "• Год выпуска\n"
        "• Тип двигателя (если знаете)\n"
        "• Пробег (для авто)\n"
        "• Условия эксплуатации\n\n"
        "Чем подробнее информация, тем точнее будет подбор! 📝"
    )
    
    await callback.message.edit_text(info_text, reply_markup=None)
    await state.set_state(SelectionForm.waiting_for_vehicle_info)
    await callback.answer()

@router.message(SelectionForm.waiting_for_vehicle_info)
async def process_vehicle_info(message: Message, state: FSMContext):
    """Обработка информации о технике и подбор масла"""
    user_data = await state.get_data()
    vehicle_info = message.text
    vehicle_type = user_data.get("vehicle_type", "")
    
    await message.answer("🔎 Анализирую информацию и подбираю оптимальное масло...")
    
    # Формируем специальный запрос для подбора масла
    selection_query = f"Подбор масла для {vehicle_info}"
    
    try:
        # Ищем в базе знаний
        contexts = rag_engine.search(selection_query)
        
        if contexts:
            # Формируем системный промпт для подбора масла
            system_prompt = (
                "Вы — эксперт по подбору моторных масел ECOFES. "
                "На основе предоставленной информации о технике клиента, "
                "подберите наиболее подходящие масла из ассортимента ECOFES. "
                "ВАЖНО: рекомендуйте только те продукты, которые есть в контексте. "
                "Объясните, почему именно эти масла подходят. "
                "Укажите конкретные марки масел, их характеристики и преимущества. "
                "Если нужна дополнительная информация — попросите её у клиента."
            )
            
            context = "\n\n".join(contexts[:3])  # Используем больше контекста
            full_query = (
                f"Контекст (продукты ECOFES):\n{context}\n\n"
                f"Информация о технике клиента: {vehicle_info}\n"
                f"Тип техники: {vehicle_type}\n\n"
                f"Задача: подобрать оптимальное масло"
            )
            
            # Получаем рекомендацию от LLM
            recommendation = await query_openrouter(system_prompt, full_query)
            
            if recommendation:
                await message.answer(
                    f"✅ <b>Рекомендация по подбору масла:</b>\n\n{recommendation}",
                    parse_mode="HTML",
                    reply_markup=get_inline_menu()
                )
            else:
                await message.answer(
                    chat_responses.get_technical_help_response(),
                    reply_markup=get_inline_menu()
                )
        else:
            # Если в базе ничего не найдено
            await message.answer(
                "К сожалению, в базе знаний не нашлось точной информации для вашей техники. "
                "Для персонального подбора масла рекомендую связаться с нашим специалистом.",
                reply_markup=get_inline_menu()
            )
            
    except Exception as e:
        logger.error(f"Ошибка при подборе масла: {e}")
        await message.answer(
            "Произошла ошибка при подборе масла. Пожалуйста, обратитесь к менеджеру для консультации.",
            reply_markup=get_inline_menu()
        )
    
    # Логируем запрос в БД
    db = SessionLocal()
    try:
        user_query = UserQuery(
            user_id=message.from_user.id,
            username=message.from_user.username,
            query_text=f"Подбор масла: {vehicle_info}",
            response_text=recommendation if 'recommendation' in locals() else "Ошибка подбора"
        )
        db.add(user_query)
        db.commit()
    except Exception as e:
        logger.error(f"Ошибка логирования запроса подбора: {e}")
    finally:
        db.close()
    
    await state.clear()

# ========================= СБОР ЗАЯВКИ (FSM) =========================

@router.callback_query(F.data == "start_lead")
async def start_lead_callback(callback: CallbackQuery, state: FSMContext):
    """Запуск процесса сбора заявки"""
    await state.clear()  # Очищаем предыдущее состояние
    await callback.message.edit_text("Введите ваше имя:", reply_markup=None)
    await state.set_state(LeadForm.waiting_for_name)
    await callback.answer()

@router.message(LeadForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Сбор имени"""
    await state.update_data(name=message.text)
    await message.answer("Теперь введите email:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(LeadForm.waiting_for_email)

@router.message(LeadForm.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    """Сбор email с валидацией"""
    if not is_valid_email(message.text):
        await message.answer("Пожалуйста, введите корректный email:")
        return
    
    await state.update_data(email=message.text)
    await message.answer("Теперь укажите телефон (например, +79991234567):")
    await state.set_state(LeadForm.waiting_for_phone)

@router.message(LeadForm.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    """Сбор телефона"""
    await state.update_data(phone=message.text)
    await message.answer("Укажите сферу деятельности (например: автосервис, промышленность, сельхоз):")
    await state.set_state(LeadForm.waiting_for_industry)

@router.message(LeadForm.waiting_for_industry)
async def process_industry(message: Message, state: FSMContext):
    """Сбор сферы деятельности и сохранение лида"""
    user_data = await state.get_data()
    name = user_data["name"]
    email = user_data["email"]
    phone = user_data["phone"]
    industry = message.text

    # Получаем Telegram username
    telegram_username = message.from_user.username
    telegram_username = f"@{telegram_username}" if telegram_username else "не указан"

    # Сохраняем в БД
    db = SessionLocal()
    try:
        lead = Lead(
            name=name,
            email=email,
            phone=phone,
            industry=industry,
            telegram_username=telegram_username
        )
        db.add(lead)
        db.commit()
        db.refresh(lead)

        await message.answer(
            f"Спасибо, {name}! Ваши данные сохранены. Наш специалист свяжется с вами в ближайшее время.",
            reply_markup=ReplyKeyboardRemove()
        )

        # Отправляем email
        lead_info = {
            "name": name,
            "email": email,
            "phone": phone,
            "industry": industry,
            "telegram_username": telegram_username,
            "created_at": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }
        await send_lead_email(lead_info)

    except Exception as e:
        logger.error(f"Ошибка сохранения лида: {e}")
        await message.answer("Произошла ошибка при сохранении. Попробуйте позже.")
    finally:
        db.close()

    # Очищаем состояние и возвращаем в главное меню
    await state.clear()
    await message.answer("Чем ещё можем помочь?", reply_markup=get_inline_menu())

# ========================= FAQ =========================

@router.callback_query(F.data == "show_faq")
async def show_faq_callback(callback: CallbackQuery):
    """Показ FAQ"""
    faq_text = (
        "📋 <b>Часто задаваемые вопросы (FAQ):</b>\n\n"

        "<b>1. Как подобрать подходящее масло для автомобиля?</b>\n"
        "Укажите марку, модель, год выпуска и тип двигателя. Наши специалисты проведут индивидуальный подбор, "
        "учитывая рекомендации автопроизводителя, условия эксплуатации и климат.\n\n"

        "<b>2. Какие продукты доступны для коммерческого транспорта или спецтехники?</b>\n"
        "В ассортименте ECOFES — масла для грузовиков, автобусов, сельхоз- и строительной техники, "
        "мотоциклов, лодок, снегоходов и садовой техники. Также есть гидравлические, трансмиссионные, "
        "компрессорные и индустриальные масла.\n\n"

        "<b>3. Где найти ближайшего дилера или представителя?</b>\n"
        "Офис: г. Москва, проспект Вернадского, 8А, офис 102.\n"
        "Производство: г. Энгельс, ул. Промышленная, 12.\n"
        "Уточнить дилера можно по телефону или email.\n\n"

        "<b>4. Как получить консультацию или оставить заявку?</b>\n"
        "• Телефон: +7 (800) 700-80-39\n"
        "• Email: zakaz@ecoschemtech.ru\n"
        "• Форма на сайте — ответ в течение 2 часов. Консультации бесплатны.\n\n"

        "<b>5. Какой срок годности масел?</b>\n"
        "От 3 до 5 лет при соблюдении условий хранения (вдали от влаги, солнца, при комнатной температуре).\n\n"

        "<b>6. Как определить дату производства?</b>\n"
        "Указана на упаковке и в сопроводительных документах. При вопросах — обращайтесь на горячую линию.\n\n"

        "<b>7. Что делать, если возникли технические вопросы?</b>\n"
        "Задайте вопрос по телефону, email или через сайт — наши технические специалисты дадут развернутый ответ.\n\n"

        "<b>8. Как стать партнером или заказать масло оптом?</b>\n"
        "Отправьте запрос — предложим индивидуальные условия. Преимущества: скидки, маркетинговая поддержка, "
        "сопровождение специалистами и открытие представительств.\n\n"
    )

    await callback.message.edit_text(faq_text, reply_markup=get_faq_keyboard(), parse_mode="HTML")
    await callback.answer()

# ========================= ЧАТ С ПОДДЕРЖКОЙ =========================

@router.callback_query(F.data == "start_support_chat")
async def start_support_chat(callback: CallbackQuery, state: FSMContext):
    """Начало чата с поддержкой"""
    if not SUPPORT_CHAT_ID:
        await callback.message.edit_text(
            "❌ Служба поддержки временно недоступна. Попробуйте позже.",
            reply_markup=get_inline_menu()
        )
        await callback.answer()
        return

    # Очищаем старое состояние и устанавливаем режим поддержки
    await state.clear()
    await state.update_data(in_support_chat=True)
    
    await callback.message.edit_text(
        "💬 Вы подключены к менеджеру. Всё, что вы напишете, будет отправлено напрямую специалисту.\n\n"
        "Для завершения диалога нажмите кнопку ниже или введите /end.",
        reply_markup=get_end_chat_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "end_support_chat")
async def end_support_chat_callback(callback: CallbackQuery, state: FSMContext):
    """Завершение чата с поддержкой через кнопку"""
    user_data = await state.get_data()
    if not user_data.get("in_support_chat"):
        await callback.answer("Вы не находитесь в диалоге с менеджером.")
        return
    
    await state.clear()  # Полностью очищаем состояние
    await callback.message.edit_text(
        "✅ Чат с менеджером завершён. Спасибо за обращение!\n\n"
        "Чем ещё можем помочь?",
        reply_markup=get_inline_menu()
    )
    await callback.answer("Диалог завершён")

@router.message(F.text == "/end")
async def end_support_chat(message: Message, state: FSMContext):
    """Завершение чата с поддержкой"""
    user_data = await state.get_data()
    if not user_data.get("in_support_chat"):
        return  # Игнорируем, если не в режиме чата
    
    await state.clear()  # Полностью очищаем состояние
    await message.answer("✅ Чат с менеджером завершён. Спасибо за обращение!")
    await message.answer("Чем ещё можем помочь?", reply_markup=get_inline_menu())

@router.message(F.reply_to_message)
async def handle_manager_reply(message: Message):
    """Обработка ответов менеджера из группы поддержки"""
    # Проверяем, что сообщение из группы поддержки
    if SUPPORT_CHAT_ID is None or message.chat.id != SUPPORT_CHAT_ID:
        return

    replied = message.reply_to_message
    if not replied or not replied.text:
        return

    # Извлекаем ID клиента из сообщения
    user_id_match = re.search(r"ID: (\d+)", replied.text)
    if not user_id_match:
        await message.reply("❌ Не удалось найти ID клиента.")
        return

    user_id = int(user_id_match.group(1))
    bot = message.bot

    try:
        # Отправляем ответ клиенту с кнопкой завершения диалога
        await bot.send_message(
            chat_id=user_id,
            text=f"📎 Ответ от менеджера:\n\n<i>{message.text}</i>",
            parse_mode="HTML",
            reply_markup=get_end_chat_keyboard()
        )
        await message.reply("✅ Ответ отправлен клиенту.")
    except Exception as e:
        await message.reply(f"❌ Ошибка при отправке ответа клиенту: {e}")
        logger.error(f"Ошибка отправки клиенту {user_id}: {e}")

# ========================= ОСНОВНОЙ ОБРАБОТЧИК ТЕКСТА =========================

@router.message(F.text)
async def handle_all_text_messages(message: Message, state: FSMContext):
    """Единый обработчик всех текстовых сообщений с улучшенной логикой"""
    # Если пользователь в процессе анкеты — не обрабатываем здесь
    current_state = await state.get_state()
    if current_state is not None:
        return

    # Получаем данные состояния
    user_data = await state.get_data()
    text = message.text.strip()
    
    # Исключаем системные команды и кнопки
    if text in ["/start", "/end", "Оставить заявку", "Узнать больше", "Вернуться в меню"]:
        return
    
    print(f"🔧 [DEBUG] Обработка сообщения от {message.from_user.id}: '{text}'")
    print(f"🔧 [DEBUG] Режим поддержки: {user_data.get('in_support_chat', False)}")
    
    # РЕЖИМ ПОДДЕРЖКИ - проверяем ПЕРВЫМ
    if user_data.get("in_support_chat"):
        if not SUPPORT_CHAT_ID:
            await message.answer("❌ Служба поддержки временно недоступна.")
            return

        bot: Bot = message.bot
        user = message.from_user

        # Формируем сообщение для менеджера
        manager_text = (
            f"🗣️ Сообщение от клиента\n"
            f"Пользователь: {user.full_name}\n"
            f"Username: @{user.username if user.username else 'не указан'}\n"
            f"ID: {user.id}\n"
            f"---\n"
            f"{text}"
        )

        try:
            # Отправляем в группу поддержки
            await bot.send_message(
                chat_id=SUPPORT_CHAT_ID,
                text=manager_text
            )
            # Подтверждение клиенту с кнопкой завершения
            await message.answer(
                "📨 Сообщение отправлено менеджеру. Ожидайте ответа.",
                reply_markup=get_end_chat_keyboard()
            )
            print(f"✅ [DEBUG] Сообщение от {user.id} отправлено в поддержку")
        except Exception as e:
            await message.answer("❌ Не удалось отправить сообщение. Попробуйте позже.")
            logger.error(f"Ошибка отправки в поддержку: {e}")
        
        return  # ВАЖНО: выходим из функции после обработки

    # ОБЫЧНЫЙ РЕЖИМ - классификация запроса
    print(f"🔧 [DEBUG] Классифицируем запрос: '{text}'")
    
    # Классифицируем тип запроса
    query_type, confidence = query_classifier.classify_query(text)
    print(f"🔧 [DEBUG] Тип запроса: {query_type}, уверенность: {confidence}")

    # Логируем вопрос в БД
    db = SessionLocal()
    user_query = None
    try:
        user_query = UserQuery(
            user_id=message.from_user.id,
            username=message.from_user.username,
            query_text=text
        )
        db.add(user_query)
        db.commit()
        db.refresh(user_query)
    except Exception as e:
        logger.error(f"Ошибка логирования вопроса: {e}")

    # Определяем стратегию ответа на основе классификации
    answer = None
    
    if query_type == "greeting":
        answer = chat_responses.get_greeting_response()
        
    elif query_type == "about":
        answer = chat_responses.get_about_response(text)
        
    elif query_type == "simple":
        if any(word in text.lower() for word in ["спасибо", "благодар"]):
            answer = chat_responses.get_simple_response()
        elif any(word in text.lower() for word in ["пока", "до свидания"]):
            answer = chat_responses.get_goodbye_response()
        else:
            answer = chat_responses.get_simple_response()
    
    elif query_type == "commercial":
        answer = chat_responses.get_commercial_response()
        
    elif query_type == "selection":
        answer = chat_responses.get_selection_response()
    
    elif query_type == "catalog":
        answer = chat_responses.get_catalog_response()
    
    elif query_type in ["technical", "general"] and confidence >= query_classifier.get_confidence_threshold(query_type):
        # Используем RAG + LLM для технических вопросов с достаточной уверенностью
        await message.answer("🔎 Ищу информацию в базе знаний...")
        
        try:
            # Улучшенный поиск с ключевыми словами
            keywords = query_classifier.get_query_keywords(text)
            search_query = f"{text} {' '.join(keywords)}" if keywords else text
            
            contexts = rag_engine.search(search_query)
            if not contexts:
                answer = chat_responses.get_technical_help_response()
            else:
                # Формируем контекст и запрос к LLM
                context = "\n\n".join(contexts[:3])  # Используем больше контекста
                system_prompt = (
                    "Вы — профессиональный консультант по продажам компании ECOFES — российского производителя "
                    "высококачественных смазочных материалов, специализирующегося на разработке и производстве "
                    "моторных масел, трансмиссионных жидкостей, гидравлических масел и других смазочных материалов "
                    "для автомобильной и промышленной техники.\n\n"
                    "ВАЖНО: отвечайте ТОЛЬКО на основе предоставленного контекста. "
                    "Если в контексте нет точного ответа на вопрос — честно скажите: "
                    "'В доступной мне информации нет точного ответа на ваш вопрос. "
                    "Рекомендую обратиться к специалисту для детальной консультации.'\n\n"
                    "НЕ ПРИДУМЫВАЙТЕ информацию. Отвечайте развернуто, но по существу, на русском языке. "
                    "Если можете ответить — давайте полезный и точный совет. "
                    "Указывайте конкретные названия продуктов ECOFES, их характеристики и области применения."
                )
                
                full_query = f"Контекст (база знаний ECOFES):\n{context}\n\nВопрос клиента: {text}"

                # Получаем ответ от LLM
                answer = await query_openrouter(system_prompt, full_query)
                
                if not answer or "нет точного ответа" in answer.lower():
                    answer = chat_responses.get_technical_help_response()

        except Exception as e:
            logger.error(f"Ошибка при работе с RAG/LLM: {e}")
            answer = (
                "Произошла ошибка при поиске информации. "
                "Пожалуйста, попробуйте переформулировать вопрос или обратитесь к менеджеру."
            )
    
    else:
        # Для неопределённых запросов или низкой уверенности
        answer = chat_responses.get_unknown_response()

    # Сохраняем ответ в БД
    if user_query and answer:
        try:
            user_query.response_text = answer
            db.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления ответа: {e}")

    # Отправляем ответ пользователю
    if answer:
        # Определяем нужна ли клавиатура
        if query_type in ["greeting", "about"]:
            keyboard = get_inline_menu()
        elif query_type in ["commercial", "selection", "catalog"]:
            keyboard = get_inline_menu()  # Всегда показываем меню для этих типов
        elif query_type == "simple":
            keyboard = None  # Для простых ответов клавиатура не нужна
        else:
            keyboard = get_inline_menu()  # По умолчанию показываем меню
            
        parse_mode = "HTML" if "<b>" in answer or "<i>" in answer else None
        await message.answer(answer, reply_markup=keyboard, parse_mode=parse_mode)
    else:
        await message.answer(
            "Извините, возникла проблема с обработкой запроса. "
            "Попробуйте позже или обратитесь к менеджеру.",
            reply_markup=get_inline_menu()
        )

    # Закрываем соединение с БД
    db.close()


# ========================= ОБРАБОТКА ДРУГИХ ТИПОВ СООБЩЕНИЙ =========================

@router.message()
async def handle_other_messages(message: Message):
    """Обработчик для всех остальных типов сообщений (фото, документы и т.д.)"""
    await message.answer(
        "Я работаю только с текстовыми сообщениями. "
        "Пожалуйста, опишите ваш вопрос текстом или воспользуйтесь меню.",
        reply_markup=get_inline_menu()
    )
