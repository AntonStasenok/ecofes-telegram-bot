from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bot.services.database import SessionLocal, Lead, UserQuery
from bot.utils.helpers import is_valid_email
from bot.services.email_sender import send_lead_email
from bot.services.rag_engine import RAGEngine
from bot.services.llm_service import query_openrouter
from datetime import datetime
import logging

router = Router()
logger = logging.getLogger(__name__)

# Инициализация RAG-движка (один раз при старте)
rag_engine = RAGEngine()

# Inline-клавиатуры
def get_inline_menu():
    """Главное меню с inline-кнопками"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оставить контакты", callback_data="start_lead")],
        [InlineKeyboardButton(text="FAQ", callback_data="show_faq")]
    ])
    return keyboard


def get_faq_keyboard():
    """Кнопки под FAQ"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Оставить контакты", callback_data="start_lead")],
        [InlineKeyboardButton(text="Вернуться в меню", callback_data="main_menu")]
    ])
    return keyboard


# FSM — сбор данных лида
class LeadForm(StatesGroup):
    waiting_for_name = State()
    waiting_for_email = State()
    waiting_for_phone = State()
    waiting_for_industry = State()


# Обработка /start — приветствие
@router.message(F.text == "/start")
async def cmd_start(message: Message, state: FSMContext):
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

    # Удаляем старую клавиатуру и отправляем приветствие
    await message.answer(welcome_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
    
    # Отдельно — inline-меню
    await message.answer("Чем могу помочь?", reply_markup=get_inline_menu())
    
    await state.clear()


# Обработка: главное меню
@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Чем могу помочь?", reply_markup=get_inline_menu())
    await callback.answer()


# Обработка: начать анкету
@router.callback_query(F.data == "start_lead")
async def start_lead_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите ваше имя:", reply_markup=None)
    await state.set_state(LeadForm.waiting_for_name)
    await callback.answer()


# Сбор имени
@router.message(LeadForm.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Теперь введите email:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(LeadForm.waiting_for_email)


# Сбор email
@router.message(LeadForm.waiting_for_email)
async def process_email(message: Message, state: FSMContext):
    if not is_valid_email(message.text):
        await message.answer("Пожалуйста, введите корректный email:")
        return
    await state.update_data(email=message.text)
    await message.answer("Теперь укажите телефон (например, +79991234567):")
    await state.set_state(LeadForm.waiting_for_phone)


# Сбор телефона
@router.message(LeadForm.waiting_for_phone)
async def process_phone(message: Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await message.answer("Укажите сферу деятельности (например: автосервис, промышленность, сельхоз):")
    await state.set_state(LeadForm.waiting_for_industry)


# Сбор сферы и сохранение
@router.message(LeadForm.waiting_for_industry)
async def process_industry(message: Message, state: FSMContext):
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

    await state.clear()

    # Возвращаем в главное меню
    await message.answer("Чем ещё можем помочь?", reply_markup=get_inline_menu())


# Обработка: FAQ
@router.callback_query(F.data == "show_faq")
async def show_faq_callback(callback: CallbackQuery):
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


# Обработка любых текстовых сообщений (вне FSM)
@router.message(F.text)
async def handle_any_text(message: Message, state: FSMContext):
    # Если пользователь в процессе анкеты — не обрабатываем
    current_state = await state.get_state()
    if current_state is not None:
        return

    # Исключаем системные команды
    text = message.text.strip()
    if text in ["Оставить заявку", "Узнать больше", "Вернуться в меню"]:
        return

    # Логируем вопрос
    db = SessionLocal()
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
    finally:
        db.close()

    # Отвечаем через RAG + LLM
    await message.answer("🔎 Ищу ответ на ваш вопрос...")

    try:
        contexts = rag_engine.search(text)
        if not contexts:
            answer = (
                "К сожалению, не нашёл информации по вашему вопросу. "
                "Пожалуйста, свяжитесь с менеджером: +7 (800) 700-80-39"
            )
            await message.answer(answer, reply_markup=get_inline_menu())
            return
        await message.answer(
             f"🔍 Найденный контекст (для отладки):\n\n"
             f"{'-'*50}\n"
             f"{contexts[0]}\n"
             f"{'-'*50}"
        )

        context = "\n\n".join(contexts[:2])
        system_prompt = (
            "Вы — эксперт по смазочным материалам ECOFES. "
            "Отвечайте кратко, профессионально и на русском языке. "
            "Если не знаете — скажите, что уточните и свяжетесь."
        )
        full_query = f"Контекст:\n{context}\n\nВопрос: {text}"

        answer = await query_openrouter(system_prompt, full_query)

        # Сохраняем ответ
        db = SessionLocal()
        try:
            user_query.response_text = answer
            db.add(user_query)
            db.commit()
        except Exception as e:
            logger.error(f"Ошибка обновления ответа: {e}")
        finally:
            db.close()

        await message.answer(answer, reply_markup=get_inline_menu())

    except Exception as e:
        logger.error(f"Ошибка при генерации ответа: {e}")
        await message.answer(
            "Произошла ошибка при обработке запроса. "
            "Пожалуйста, попробуйте позже или свяжитесь с менеджером: +7 (800) 700-80-39",
            reply_markup=get_inline_menu()
        )
