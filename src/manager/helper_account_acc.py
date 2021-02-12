"""
get and setup an helper acc
"""
import telegram.ext
from telegram import InlineKeyboardButton, ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram.ext import ConversationHandler

from manager import get_cur

GET_CLIENT_STR = range(0, 1)


def add_helper_str(client_str: str, group_id: int, user_id: int, api_id: int, api_hash: str):
    query = """
INSERT INTO "v2"."helpers_accounts" ("group_id", "session_str", "uploaded_by", "uploaded_at", "status", "type","api_id","api_hash")
 VALUES (%s, %s, %s, DEFAULT, 1, 'private',%s,%s)
    """
    try:
        conn, cur = get_cur()
        cur.execute(query, [group_id, client_str, user_id, api_id, api_hash])
        conn.commit()
    except Exception as e:
        print(e)


def remove_active_helper(group_id: int):
    query = """
UPDATE "v2"."helpers_accounts" SET "disabled_at" = (now() at time zone 'Asia/Tehran')::timestamp
 WHERE "group_id" = %s and "disabled_at" is null """
    try:
        conn, cur = get_cur()
        cur.execute(query, (group_id,))
        conn.commit()
    except Exception as e:
        print(e)


def get_helper_str_by_group_id(group_id):
    query = """
    SELECT session_str FROM v2.helpers_accounts t 
    where group_id=%s and disabled_at is null 
    """
    try:
        conn, cur = get_cur()
        cur.execute(query, (group_id,))
        res = cur.fetchone()
        return res[0] if res else None
    except Exception as e:
        print(e)


def get_started(update: telegram.Update, context: telegram.ext.CallbackContext, data):
    """ explain subject and get the number from user if there is no any client active for group """
    chat = update.effective_message.chat
    user = update.effective_message.from_user
    group_id = int(data[1]) * -1
    has_active = False
    if get_helper_str_by_group_id(group_id):
        update.message.reply_text('درحال حاظر شما یک هلپر فعال دارید')
        has_active = True
    # todo: explain what is this
    text = "explain text"
    context.bot.send_message(chat_id=chat.id, text=text)
    buttons = []
    # if user has active helper
    if has_active:
        buttons.append([InlineKeyboardButton('حذف هلپر فعال', callback_data='customHelper del {}'.format(group_id))])
    # if user has no active helper
    else:
        buttons.append([InlineKeyboardButton('اضافه هلپر فعال', callback_data='customHelper add {}'.format(group_id))])

    context.bot.send_message(chat_id=chat.id, text='وضعیت هلپر ها', reply_markup=InlineKeyboardMarkup(buttons))


def check_permission(group_id, chat_id, context) -> bool:
    try:
        res = context.bot.get_chat_member(chat_id=group_id, user_id=chat_id)
        if not res.can_promote_members and res.status != res.CREATOR:
            context.bot.send_message(
                chat_id=chat_id,
                text='شما دسترسی برای اینکار ندارید، حداقل دسترسی برای این بخش دسترسی برای اضافه کردن ادمین است.')
            return False
    except Exception as e:
        print(e)
        context.bot.send_message(chat_id=chat_id, text='هنگام بررسی دسترسی شما به مشکل خوردیم به علت "%s".' % (e,))
        return False

    return True


def custom_helper_callback(update: telegram.Update, context: telegram.ext.CallbackContext):
    """  """
    chat = update.effective_message.chat
    user = update.effective_message.from_user
    query = update.callback_query
    data = query.data.split(' ')
    data = {
        'subject': data[0],
        'action': data[1],
        'group_id': data[2]
    }
    context.chat_data['customClient_callback'] = data
    if data['action'] == 'del':
        if not check_permission(data['group_id'], chat.id, context):
            query.message.delete()
            return
        remove_active_helper(data['group_id'])
        context.bot.send_message(chat.id, 'تمامی هلپرهای فعال حذف شدند')
        query.message.delete()

    elif data['action'] == 'add':
        if not check_permission(data['group_id'], chat.id, context):
            return

        context.bot.send_message(chat_id=chat.id, text='متن نشست را ارسال کنید')
        try:
            query.message.delete()
        except:
            pass
        return GET_CLIENT_STR


def get_client_str(update: telegram.Update, context: telegram.ext.CallbackContext):
    """ get client str for pyrogram from user """
    chat = update.effective_message.chat
    user = update.effective_message.from_user
    data = context.chat_data.get('customClient_callback')
    if not data:
        # todo: say go back from first line
        context.bot.send_message(chat_id=chat.id, text='برو سر گپت دوباره بزن')
        return ConversationHandler.END
    if not check_permission(context.chat_data['customClient_callback']['group_id'], chat.id, context):
        return ConversationHandler.END
    texts = update.message.text.split('@')
    client_str = texts[1]
    api_id = texts[2]
    api_hash = texts[3]
    add_helper_str(client_str, data['group_id'], user.id,api_id,api_hash)
    context.bot.send_message(chat.id, 'ثبت شد')
    return ConversationHandler.END
