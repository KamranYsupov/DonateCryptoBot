import os
from datetime import datetime, timedelta
import uuid

import loguru
from aiogram import Router, F, Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramAPIError
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from dependency_injector.wiring import inject, Provide

from app.core.container import Container
from app.schemas.donate import DonateEntity, DonateTransactionEntity
from app.services.donate_confirm_service import DonateConfirmService
from app.services.telegram_user_service import TelegramUserService
from app.models.telegram_user import status_list
from app.services.donate_service import DonateService
from app.schemas.telegram_user import TelegramUserEntity
from app.keyboards.donate import get_donate_keyboard
from app.utils.sponsor import get_callback_value
from app.models.telegram_user import DonateStatus, MatrixBuildType
from app.core.config import settings
from app.services.matrix_service import MatrixService
from app.schemas.matrix import MatrixEntity
from app.keyboards.donate import get_donations_keyboard
from app.db.commit_decorator import commit_and_close_session
from app.keyboards.reply import get_reply_keyboard
from app.utils.pagination import Paginator
from app.utils.sort import get_reversed_dict
from app.utils.sponsor import check_is_second_status_higher
from app.utils.texts import get_donate_confirm_message
from app.utils.excel import export_users_to_excel
from app.utils.texts import get_user_statuses_statistic_message

donate_router = Router()

@donate_router.callback_query(F.data.startswith("yes_"))
@inject
async def subscribe_handler(
        callback: CallbackQuery,
) -> None:
    sponsor_user_id = get_callback_value(callback.data)

    buttons = [
        InlineKeyboardButton(
            text="📌 КАНАЛ 📌",
            url=settings.channel_link),
        InlineKeyboardButton(
            text="💬 ЧАТ 💬",
            url=settings.chat_link),
        InlineKeyboardButton(
            text="Проверить подписку ✅",
            callback_data=f"menu_{sponsor_user_id}",
        )
    ]
    keyboard = InlineKeyboardBuilder()
    keyboard.add(*buttons)

    await callback.message.delete()
    await callback.message.answer(
        f"🔑 Для доступа к основным функциям бота, подпишитесь на чат и канал сообщества ⤵️",
        reply_markup=keyboard.adjust(1, 1).as_markup()
    )


@donate_router.callback_query(F.data.startswith("menu_"))
@inject
@commit_and_close_session
async def subscription_checker(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
):
    sponsor_user_id = get_callback_value(callback.data)
    sponsor = await telegram_user_service.get_telegram_user(user_id=sponsor_user_id)

    chat_result = await callback.bot.get_chat_member(
        chat_id=settings.chat_id, user_id=callback.from_user.id
    )
    channel_result = await callback.bot.get_chat_member(
        chat_id=settings.channel_id, user_id=callback.from_user.id
    )

    not_subscribed_statuses = (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
    if channel_result.status in not_subscribed_statuses or chat_result.status in not_subscribed_statuses:
        await callback.answer("Ты не подписался ❌", show_alert=True)
        return

    await callback.message.delete()


    if not callback.from_user.username:
        await callback.message.answer(
            "Для регистрации добавьте пожалуйста <em>username</em> в свой telegram аккаунт",
            reply_markup=get_donate_keyboard(
                buttons={"Попробовать ещё раз": callback.data}
            )
        )
        return


    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )

    if not current_user:
        user_dict = callback.from_user.model_dump()
        user_id = user_dict.pop("id")

        user_dict["user_id"] = user_id
        user_dict["sponsor_user_id"] = sponsor_user_id
        user_dict["depth_level"] = sponsor.depth_level + 1
        user = TelegramUserEntity(**user_dict)

        current_user = await telegram_user_service.create_telegram_user(
            user=user,
            sponsor=sponsor,
        )

        try:
            await callback.bot.send_message(
                chat_id=sponsor.user_id,
                text=f"По вашей ссылке зарегистрировался пользователь @{current_user.username}."
            )
        except TelegramAPIError:
            pass

    await callback.message.answer(
        "✅ Готово! Выбери сервис", reply_markup=get_reply_keyboard(current_user)
    )

@donate_router.callback_query(F.data.startswith("donations"))
@donate_router.message(F.text == "⚡️ Активация")
@inject
async def donations_menu_handler(
        aiogram_type: Message | CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    telegram_method = aiogram_type.answer if isinstance(aiogram_type, Message) \
        else aiogram_type.message.edit_text

    current_user = await telegram_user_service.get_telegram_user(
        user_id=aiogram_type.from_user.id
    )
    default_buttons = {}

    if current_user.status != DonateStatus.NOT_ACTIVE:
        default_buttons.update({
            "Транзакции 💳": f"transactions",
            "АКТИВНЫЕ УРОВНИ": f"team_1"
        })

    if current_user.is_admin:
        users = await telegram_user_service.get_list()
        statuses_statistic_message = get_user_statuses_statistic_message(
            users,
        )
        message_text = (
            f"Партнеров в «НА СВЯЗИ»: <b>{len(users)}</b>\n"
            f"\n{statuses_statistic_message}\n"
            f"Лично приглашенных: <b>{current_user.invites_count}</b>\n"
            f"Баланс для активации: "
            f"<b>{current_user.bill_for_activation}</b>\n"
            "Баланс для вывода: "
            f"<b>{current_user.bill_for_withdraw}</b>\n"
        )
        buttons = default_buttons
        admin_buttons = {
            "Скачать базу ⬇️": "excel_users",
            "Заявки на вывод 💸": "withdrawal_requests_1",
            "Список забаненных пользователей 📇🅱️": "banned_users_1",
            "Забанить пользователя 🔒": "ban_user",
        }
        buttons.update(admin_buttons)

        await telegram_method(
            text=message_text,
            reply_markup=get_donate_keyboard(
                buttons=default_buttons,
            ),
        )
        return

    buttons = {}
    sponsor = await telegram_user_service.get_telegram_user(
        user_id=current_user.sponsor_user_id
    )
    buttons.update(get_reversed_dict(
        get_donations_keyboard(
            current_status=current_user.status,
            status_list=status_list,
        ))
    )
    message_text = (
            f"Мой куратор: "
            + ("@" + sponsor.username if sponsor.username else sponsor.first_name)
            + "\n"
              f"Мой статус: <b>{current_user.status.value}</b>\n"
              f"Лично приглашенных: <b>{current_user.invites_count}</b>\n"
              f"Баланс для активации: "
              f"<b>{current_user.bill_for_activation}</b>\n"
              "Баланс для вывода: "
              f"<b>{current_user.bill_for_withdraw}</b>\n"
    )

    buttons.update(default_buttons)
    buttons.update({"Пополнить баланс": "start_buy_tokens_state"})
    #
    # if current_user.bill > 0:
    #     buttons.update({"Вывод средств": "withdrawal_request"})

    await telegram_method(
        text=message_text,
        reply_markup=get_donate_keyboard(
            buttons=buttons,
        ),
    )


@donate_router.callback_query(F.data == 'excel_users')
async def export_users_to_excel_callback_handler(
        callback: CallbackQuery,
):
    await callback.message.edit_text(
        "<em>Подождите немного ...</em>",
        parse_mode='HTML',
    )

    file_name = "app/telegram_users.xlsx"
    await export_users_to_excel(file_name)
    file_input = FSInputFile(file_name)

    await callback.message.delete()
    await callback.message.answer_document(file_input)

    os.remove(file_name)


@donate_router.callback_query(F.data.startswith("send_donate_"))
@inject
@commit_and_close_session
async def confirm_donate(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:

    callback_donate_data = "_".join(callback.data.split("_")[1:])
    await callback.answer(str(callback_donate_data))
    donate_sum = float(callback_donate_data.split("_")[-2])
    bill_type = callback_donate_data.split("_")[-1]
    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )

    need_to_buy_tokens = getattr(current_user, f"bill_for_{bill_type}") - donate_sum
    if need_to_buy_tokens < 0:
        need_to_buy_tokens = int(abs(need_to_buy_tokens))
        await callback.message.edit_text(
            f"Для активации уровня нехватает {need_to_buy_tokens} токенов.",
            reply_markup=get_donate_keyboard(
                buttons={
                    "Преобрести 💳": f"buy_tokens_{need_to_buy_tokens}",
                    "🔙 Назад": f"donations",
                },
                sizes=(1, 1),
            ),
        )

        return


    await callback.message.edit_text(
        text=f"Для активации уровня с вашего баланса спишется <b>{donate_sum}</b> токенов.\n\n"
             "<b>Вы согласны продолжить?</b>",
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(
            buttons={
                "Да": callback_donate_data,
                "Нет": f"donations",
            },
            sizes=(2, 1),
        ),
    )

@donate_router.callback_query(F.data.startswith("donate_"))
@inject
@commit_and_close_session
async def donate_handler(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    bill_type = callback.data.split("_")[-1]
    donate_sum = int(callback.data.split("_")[-2])

    status = donate_service.get_donate_status(donate_sum)
    current_user = await telegram_user_service.get_telegram_user(
        user_id=callback.from_user.id
    )

    if not callback.from_user.username:
        await callback.message.edit_text(
            "Перед отправкой подарка, "
            "добавьте пожалуйста <em>username</em> в свой телеграм аккаунт"
        )
        return

    if callback.from_user.username and current_user.username is None:
        current_user.username = callback.from_user.username

    first_sponsor = await telegram_user_service.get_telegram_user(
        user_id=current_user.sponsor_user_id
    )
    donations_data = {}

    matrix = await donate_service.handle_matrix_activation(
        first_sponsor,
        current_user,
        donate_sum,
        donations_data,
        status,
    )

    donate = await donate_confirm_service.create_donate(
        telegram_user_id=current_user.id,
        donate_data=donations_data,
        matrix_id=matrix.id,
        quantity=donate_sum,
    )

    bill_field = f"bill_for_{bill_type}"
    bill_value = getattr(current_user, bill_field)
    await telegram_user_service.update(
        obj_id=current_user.id,
        obj_in={bill_field: bill_value - donate_sum},
    )

    if current_user.status == DonateStatus.NOT_ACTIVE or (
        int(status.get_status_donate_value())
        > int(current_user.status.get_status_donate_value())
    ):
        current_user.status = status

    transactions_data = await donate_confirm_service.get_donate_transactions_by_donate_id(
        donate_id=donate.id, return_data=True,
    )
    messages = []
    for transaction in transactions_data:
        sponsor = await telegram_user_service.get_telegram_user(
            id=transaction["sponsor_id"]
        )
        await telegram_user_service.update(
            obj_id=sponsor.id,
            obj_in={"bill_for_withdraw": sponsor.bill_for_withdraw + transaction["quantity"]},
        )
        messages.append((sponsor.user_id, transaction["quantity"]))

    await callback.message.delete()

    await callback.message.answer("🎉")
    await callback.message.answer("Уровень успешно активирован ✅")

    for chat_id, quantity in messages:
        try:
            await callback.bot.send_message(
                text=f"Вам подарок в размере <b>${quantity}</b>\n",
                chat_id=chat_id,
            )
        except TelegramAPIError:
            pass


@donate_router.callback_query(F.data == "transactions")
@inject
async def get_transactions_menu(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
) -> None:
    buttons = {
        "Транзакции мне 📈": f"transactions_to_me_1",
        "Транзакции от меня 📉": f"transactions_from_me_1",
    }
    user_id = callback.from_user.id
    user = await telegram_user_service.get_telegram_user(user_id=user_id)
    if user.is_admin:
        buttons["Все транзакции 📊"] = f"all_transactions_1"

    buttons["🔙 Назад"] = f"donations"

    await callback.message.edit_text(
        "В этом разделе вы можете посмотреть информацию о подтверждении транзакций по подаркам.\n"
        "Выберете раздел:",
        reply_markup=get_donate_keyboard(buttons=buttons),
    )


@donate_router.callback_query(F.data.startswith("transactions_to_me_"))
@inject
@commit_and_close_session
async def get_transactions_list_to_me(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    page_number = int(callback.data.split("_")[-1])

    user_id = callback.from_user.id
    user = await telegram_user_service.get_telegram_user(user_id=user_id)
    transactions = await donate_confirm_service.get_donate_transaction_by_sponsor_id(
        sponsor_id=user.id,
    )

    paginator = Paginator(transactions, page_number=page_number, per_page=5)
    buttons = {}
    sizes = (1, 1)

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"transactions_to_me_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"transactions_to_me_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1)

    message = "Транзакции от пользователей Вам.\n\n"
    transactions = paginator.get_page()

    if transactions:
        for transaction in transactions:
            donate = await donate_confirm_service.get_donate_by_id(
                donate_id=transaction.donate_id
            )
            user = await telegram_user_service.get_telegram_user(
                id=donate.telegram_user_id
            )
            message += (
                f"ID: {transaction.id}\n"
                f"Сумма: ${transaction.quantity}\n"
                f"От: @{user.username}\n"
                f"Дата: {transaction.created_at}\n"
            )
    else:
        message = "У вас нет транзакций"

    buttons["🔙 Назад"] = f"transactions"
    await callback.message.edit_text(
        message,
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=sizes,
        ),
    )


@donate_router.callback_query(F.data.startswith("transactions_from_me_"))
@inject
async def get_transactions_list_from_me(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_service: DonateService = Provide[Container.donate_service],
        matrix_service: MatrixService = Provide[Container.matrix_service],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    page_number = int(callback.data.split("_")[-1])

    user_id = callback.from_user.id
    user = await telegram_user_service.get_telegram_user(user_id=user_id)
    donates = await donate_confirm_service.get_all_my_donates_and_transactions(
        telegram_user_id=user.id,
    )

    paginator = Paginator(list(donates.items()), page_number=page_number, per_page=3)
    buttons = {}
    sizes = (1, 1)
    message = "<b><u>Ваши подарки и транзакции</u></b>\n\n"

    donates = paginator.get_page()
    if donates:
        for donate, transactions in donates:
            message += (
                f"<b><u>Подарок на сумму: "
                f"${donate.quantity}</u></b>\n"
                f"ID: {donate.id}\n"
                f"Дата: {donate.created_at}\n"
            )

            if transactions:
                for transaction in transactions:
                    sponsor = await telegram_user_service.get_telegram_user(
                        id=transaction.sponsor_id
                    )
                    message += f"Кому: @{sponsor.username}\n\n"
    else:
        message = "У Вас нет подарков"

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"transactions_from_me_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"transactions_from_me_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1)

    buttons["🔙 Назад"] = f"transactions"

    await callback.message.edit_text(
        message,
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(buttons=buttons, sizes=sizes),
    )


@donate_router.callback_query(F.data.startswith("all_transactions_"))
@inject
async def get_all_transactions(
        callback: CallbackQuery,
        telegram_user_service: TelegramUserService = Provide[
            Container.telegram_user_service
        ],
        donate_confirm_service: DonateConfirmService = Provide[
            Container.donate_confirm_service
        ],
) -> None:
    page_number = int(callback.data.split("_")[-1])
    donates_and_transactions = (
        await donate_confirm_service.get_all_donates_and_transactions()
    )

    paginator = Paginator(
        list(donates_and_transactions.items()), page_number=page_number, per_page=3
    )
    buttons = {}
    sizes = (1, 1)
    message = "Все подарки и транзакции\n\n"
    donates_and_transactions = paginator.get_page()

    if paginator.has_previous():
        buttons |= {"◀ Пред.": f"all_transactions_{page_number - 1}"}
    if paginator.has_next():
        buttons |= {"След. ▶": f"all_transactions_{page_number + 1}"}

    if len(buttons) == 2:
        sizes = (2, 1)

    if donates_and_transactions:
        for donate, transactions in paginator.get_page():
            user = await telegram_user_service.get_telegram_user(
                id=donate.telegram_user_id
            )
            message += (
                f"<b><u>Подарок на сумму: "
                f"${donate.quantity}</u></b>\n"
                f"ID: {donate.id}\n"
                f"Дата: {donate.created_at}\n"
            )
            message += "Транзакции по подарку: \n\n"
            if transactions:
                for transaction in transactions:
                    sponsor = await telegram_user_service.get_telegram_user(
                        id=transaction.sponsor_id
                    )
                    message += (
                        f"ID: {transaction.id}\n"
                        f"Сумма: ${transaction.quantity}\n"
                        f"От кого: @{user.username}\n"
                        f"Кому: @{sponsor.username}\n"
                    )

    buttons["🔙 Назад"] = f"transactions"
    await callback.message.edit_text(
        message,
        parse_mode="HTML",
        reply_markup=get_donate_keyboard(
            buttons=buttons,
            sizes=sizes,
        ),
    )

