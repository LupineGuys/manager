from . import get_cur, join_options, bot
import telegram
from telegram.error import BadRequest
from telegram.ext import run_async
from threading import Thread
import schedule
from time import sleep


def add_message_for_delete_database(message_id, group_id, user_id):
    query = """
    insert into v1.manager_delete_message(group_id,message_id,created_at, user_id)
    values (%s,%s,(now()at time zone 'Asia/Tehran')::timestamp,%s)
    """

    conn, cur = get_cur()

    try:
        cur.execute(query, (group_id, message_id, user_id))
        conn.commit()
        return True
    except:
        cur.close()

        return False


def get_all_message_ids_to_delete(group_id):
    query = """
    select message_id
    from v1.manager_delete_message
    where deleted_at is null and group_id = %s
    """
    conn, cur = get_cur()

    try:
        cur.execute(query, (group_id,))
        res = cur.fetchall()
        cur.close()
        if res:
            return [i[0] for i in res]
        return res
    except:
        cur.close()

        return False


def set_as_deleted(group_id, messages):
    value = []
    for message in messages:
        try:
            value.append([group_id, message])
        except:
            pass
    query = """
    update v1.manager_delete_message
    set deleted_at = (now()at time zone 'Asia/Tehran')::timestamp
    where group_id=%s and message_id = %s
    """
    conn, cur = get_cur()

    try:
        cur.executemany(query, value)
        conn.commit()
        cur.close()
        return True
    except:
        cur.close()
        return False


messages = []


def add_user_message():
    global messages
    data = messages.copy()
    messages = []
    query = """
    insert into v1.manager_players_messages(chat_id, user_id, message_id, message_at)
    values (%s,%s,%s,(now()at time zone 'Asia/Tehran')::timestamp)
    """
    conn, cur = get_cur()

    try:
        cur.executemany(query, data)
        conn.commit()
        return True
    except Exception as e:
        cur.close()
        return False


def group_status_cache(context: telegram.ext.CallbackContext):
    res = join_options.get_all_groups_status()
    if res:
        global group_cache
        group_cache = res
        # print(len(group_cache))


# Filters.entity('text_mention')
def get_group_status(chat_id):
    if chat_id in group_cache:
        if chat_id == -1001461432821:
            print(group_cache[chat_id])
        return group_cache[chat_id]


@run_async
def define_message_as_mention(update, context):
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    if update.message.from_user.id == 798494834 and update.message.text.lower() in (
            '/nextgame@werewolfbot',
            '/nextgame@werewolfbetabot'):
        bot.send_message(chat_id, 'Amitis💜 is here', reply_to_message_id=update.message.message_id)

    user_id = update.message.from_user.id
    entities = update.message.entities
    # todo check game time
    if entities:
        group_info = get_group_status(chat_id)
        status = 0
        if group_info:
            if group_info['finished_at']:
                status = 0
            elif group_info['started_at']:
                status = 2
            elif group_info['created_at']:
                status = 1
            else:
                status = 0
        elif not group_info:
            return

        # if status == 1:
        entity_length = 0
        message_length = len(update.message.text)
        for entity in entities:
            if entity['type'] in ['text_mention', 'mention']:
                entity_length += entity['length']
        if entity_length / message_length >= 0.4:
            add_message_for_delete_database(message_id, chat_id, update.message.from_user.id)
        else:
            messages.append([chat_id, user_id, message_id])
    else:
        messages.append([chat_id, user_id, message_id])


def delete_message(values):
    error = 0
    try:
        bot.delete_message(values['chat_id'], values['message_id'])
    except BadRequest as e:
        if e.message == 'Message to delete not found':
            error = -1
        elif e.message == "Message can't be deleted":
            error = 1
    except Exception as e:
        print(e)
        error = 2
    return error, values['message_id']


@run_async
def delete_messages(update, context):
    chat_id = update.message.chat_id
    messages = get_all_message_ids_to_delete(chat_id)
    if not messages:
        context.bot.send_message(chat_id, "در گروه شما منشنی در زمان جوین تایم تشخیص داده نشده است برای حذف")
        return
    values = []
    for message_id in messages:
        try:
            values.append(dict(chat_id=chat_id, message_id=message_id))
        except:
            pass

    res = jmap(delete_message, values, workers=200, verbose=100, backend='t')
    deleted = []
    deleted_before = []
    could_not_delete = []
    problems = []
    for error, message_id in res:
        if error == 0:
            deleted.append(message_id)
        elif error == -1:
            deleted_before.append(message_id)
        elif error == 1:
            could_not_delete.append(message_id)
        else:
            problems.append(message_id)

    context.bot.send_message(chat_id, """حذف منشن پایان یافت✅
دیلیت شده توسط ربات: {}
دیلیت شده توسط شخص دیگر: {}
دیلیت نشده: {}
{}
""".format(len(deleted), len(deleted_before), len(could_not_delete),
           'دیلیت نشده به علت عدم دسترسی به حذف مسیج\n اگر ادمین گروه هستید لطفا دسترسی ربات رو باز کنید تا منشن های داخل جوین تایم حذف بشن و پلیر راحت تر باشه' if could_not_delete >= deleted else ''))

    set_as_deleted(chat_id, deleted + deleted_before + problems)


def jmap(func, iterable, workers=-1, verbose=10, backend='l', *args, **kwargs):
    if backend == 'l':
        backend = 'loky'
    elif backend == 't':
        backend = 'threading'
    from joblib import Parallel, delayed
    with Parallel(n_jobs=workers, verbose=verbose, backend=backend, **kwargs) as p:
        result = p(delayed(function=func)(i) for i in iterable)
    return result


def save_messages():
    schedule.every(60).seconds.do(add_user_message)
    print('scheduling saving msgs')
    while True:
        schedule.run_pending()
        sleep(1)


job_thread = Thread(target=save_messages)
job_thread.start()

group_cache = {}
