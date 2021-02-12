import datetime
import logging
from random import choice
import traceback
import html
import json

from cachetools import cached, TTLCache
from pytz import timezone
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Bot
from telegram.ext import Updater, CommandHandler, Filters, MessageHandler, CallbackQueryHandler, run_async, \
    ConversationHandler

from . import RANK_STATEMENT
from . import activity
from . import chern_list
from . import group_data
from . import join_options
from . import manager_token, get_cur, dev_group, rank_emoji_admins, bot_admins
from . import mention_options
from . import stats
from .advanced_commands import advanced_commands_buttons, set_action, sticker_and_gif_commands, del_action
from .helper_account_acc import GET_CLIENT_STR, get_client_str, get_started, custom_helper_callback
from .statistics import statistics_command, statistics_detail
from .join_options import handlers as join_options_handlers, status_handler as join_options_welcomes_command


game_started = r'ایول بازی شروع شد 😃|توجه توجه دانشگاه شروع شد|حلقه پیدا شد|قطار داره راه میافته|ژوون بازی شروع شد|WINTER IS HERE|استارت شد ، سیستم در حال ارسال نقش|ژوووووون💦 بازی شروع شد|بالاخره بازی شروع شد|خب بُکُن بُکُن شروع شد|ایول مسابقات شروع شد|خب خب خب . بازی شروع شد|حااا بازی شروع وشد |ایول بازی شروع شد|قطار راه افتاد |بالاخره شروع شد|در های ورودی کمپانی بسته شد|ایول درهای هتل بسته شد|خب رسیدیم میستیک فالز|😍جون جون وایستین بازی شروع شد'
game_canceled = r'کلاس ها تعطیله عزیزان|چقدر کمین!|چقدر شایرخلوته|تعداد مسافران کافی نیست |زرت تعدادتون کمه دیوثا |تعدادتون خیلی کمه😖|با این تعداد آدم میخواین فرمانروایی راه بندازین|چقدر کمین!|کچلم کردین ، اخه با این تعداد |زرشگ فقط همین قدر اصن نوریم برره|متاسفم حداقل باید 5 تا کابوی شرکت کنه|عجیبه! بازیکنان فوتبال میلیون ها دلار کسب می کنند اما اینجا بازیکن کافی ندارد. مسابقات لغو شد'

iran = timezone('Asia/Tehran')

updater = Updater(token=manager_token, use_context=True, workers=55)
job_queue = updater.job_queue
job_minute = job_queue.run_repeating(mention_options.group_status_cache, interval=3, first=0)
bot = updater.bot

dispatcher = updater.dispatcher
dp = dispatcher
u = updater


def now():
    sa_time = datetime.datetime.now(iran)
    return sa_time.strftime('%Y-%m-%d %H:%M:%S')


@run_async
def execute(update, context):
    exec(update.message.text[6:])


@run_async
def start(update, context):
    # print('started')
    # return GIVEMESSAGE
    if context.args:
        data = context.args[0].split('_')
        if data[0] == 'churn-list':
            user = update.message.from_user
            chat = update.message.chat
            res = bot.get_chat_member(data[1], user.id)
            if res.status not in ['creator', 'administrator'] and user.id not in bot_admins():
                context.bot.send_message(update.message.chat_id, 'یختی بابایه اشتباه اومدی', parse_mode='HTML')
                return
            context.bot.send_message(update.message.chat_id, 'working on ...', parse_mode='HTML')
            try:
                msg = chern_list.make_list(data[1])
            except Exception as e:
                print(e)
            if not msg:
                msg = 'لیست خالی است'
                context.bot.send_message(update.message.chat_id, msg, parse_mode='HTML')
                return
            header = msg['header']
            msgs = msg['msg_list']
            for msg in msgs:
                try:
                    context.bot.send_message(update.message.chat_id, header + msg, parse_mode='HTML')
                except Exception as e:
                    print(e)
            return

        elif data[0] == 'joinSetting':
            join_options.join_message(update, context, data)
            return
        elif data[0] == 'adminStats':
            activity.start_activity(update, context, data)
            return
        elif data[0] == 'customHelper':
            get_started(update, context, data)
            return
        elif data[0] == 'statistics':
            statistics_detail(update, context, data)
            return
    update.message.reply_text('برو که زندگی مال ماست... همه برن فقط تو بمون 😉')


@cached(cache=TTLCache(maxsize=1024, ttl=180))
def get_ranks_data():
    conn, cur = get_cur()
    try:
        query = f"""
select id,title,emoji
from v2.ranks
where id>0 
order by id
"""
        cur.execute(query)
        res = cur.fetchall()
        cur.close()
        return res
    except Exception as e:
        cur.execute("rollback")
        conn.commit()
        cur.close()
        return get_ranks_data()


def add_rank_db(user_id, rank_id):
    conn, cur = get_cur()
    query = """
INSERT INTO v2.members_ranks (user_id, rank_id)
       SELECT %(user_id)s, %(rank_id)s
       WHERE NOT EXISTS (SELECT 1 FROM v2.members_ranks WHERE user_id=%(user_id)s and rank_id=%(rank_id)s); 
        """
    cur.execute(query, {
        'user_id': user_id,
        'rank_id': rank_id
    })
    conn.commit()


@run_async
def add_emoji(update, context):
    if update.message.from_user.id not in rank_emoji_admins():
        update.message.reply_text('مث ما نمیتونی تو بدی شل تکون شل تکون')
        return
    if not context.args:
        update.message.reply_text('خشی برسه کیفم کوک میشه')
        return

    data = context.args
    rank_id = data[0]
    if update.message.reply_to_message:
        users_id = [update.message.reply_to_message.from_user.id]
    else:
        users_id = [data[1]]
        if data[1] == 'admins' and update.effective_message.chat.id == -1001461432821:
            users_id = [i.user.id for i in bot.get_chat_administrators(-1001461432821)]

    [add_rank_db(user_id, rank_id) for user_id in users_id]
    update.message.reply_text('ما تا صب نمی کوبیم، ما میدیم شل تکون شل تکون')


@run_async
def display_ranks(update, context):
    ranks = get_ranks_data()
    form = "‌{id}| {emoji}-{title}"
    update.message.reply_text('\n'.join([form.format(id=str(i[0]).zfill(2), title=i[1], emoji=i[2]) for i in ranks]))


@run_async
def custom_rank(update, context):
    if not update.message.from_user.id in rank_emoji_admins():
        update.message.reply_text("چخده")
        return
    if context.args:
        data = context.args
        if len(data) != 2:
            update.message.reply_text('یوزر ایدی عددی و رنک')
            return
        user_id = data[0]
        rank = data[1]
        rank = rank if rank != 'Null' else None
        query = f"""
UPDATE "v1"."users_custom_rank" SET "updated_at"='{now()}', rank=%(rank)s WHERE "user_id"=%(user_id)s;
INSERT INTO "v1"."users_custom_rank" ("user_id", "rank")
       SELECT %(user_id)s, %(rank)s
WHERE NOT EXISTS (SELECT 1 FROM "v1"."users_custom_rank" WHERE user_id=%(user_id)s)
"""
        conn, cur = get_cur()
        try:
            cur.execute(query, {'user_id': user_id, 'rank': rank})
            conn.commit()
            cur.close()
        except Exception as e:
            print(e)
            cur.close()
        status = RANK_STATEMENT.UserStatus(int(user_id))
        update.message.reply_text(str(status.__dict__))


@RANK_STATEMENT.check_channel_join
@run_async
def get_churn_list(update, context):
    user = update.message.from_user
    chat = update.message.chat
    res = bot.get_chat_member(chat.id, user.id)
    if res.status not in ['creator', 'administrator'] and user.id not in bot_admins():
        return
    buttons = InlineKeyboardMarkup([[InlineKeyboardButton('churn list',
                                                          url='http://t.me/manage_ww_bot?start=churn-list_{}'.format(
                                                              chat.id))]])
    context.bot.send_message(update.message.chat_id, 'روی لینک زیر بزن تا بریم سراقشون', reply_markup=buttons)


# logger = logging.getLogger(__name__)
#
#
# def error(update, context):
#     """Log Errors caused by Updates."""
#     logger.warning('Update "%s" caused error "%s"', update, context.error)


def custom_gif(update, context):
    print(update)
    if update.effective_message.reply_to_message:
        if update.effective_message.animation.file_unique_id == 'AgADcgADQuhxRw':
            user_id = update.effective_message.reply_to_message.from_user.id
            bot.kick_chat_member(update.effective_message.chat.id, user_id)
        elif update.effective_message.animation.file_unique_id == 'AgAD6QYAAkvsQFE':
            msg = "you look like so cute"
            bot.send_message(update.effective_message.chat.id, msg,
                             reply_to_message_id=update.effective_message.reply_to_message.message_id)


def custom_stcker(update, context):
    items = ['Belllaaaa ciaoooooo',
             'راکا چاک چاک راکا چاکا چاک چاک',
             'رابا بام بام رابا بام بام',
             'باید روبه رنگین کمون رول بزنم وقتی معجزه رفت د پس کوبص عمت',
             'کاش بزنه سیل بیاد به قول مهراد',
             'کُک دوس ندارم پپسی',
             'چشا روبه ابراس',
             "Never mind I'll find someone like you",
             'منو نمیکنه کسی میوت...جز خودم',
             'بنی آدم اعضای یکدیگرند',
             'میارم آرامش با اعتماد و احترام']

    if update.effective_message.reply_to_message:
        # if update.effective_message.sticker.file_unique_id == 'AgADcgADQuhxRw' and update.effective_message.from_user.id != 1184814450:
        #     user_id = update.effective_message.reply_to_message.from_user.id
        #     bot.kick_chat_member(update.effective_message.chat.id, user_id)
        if update.effective_message.sticker.file_unique_id == 'AgADBwADchCYLw' and update.effective_message.from_user.id == 798494834:
            msg = "رای تو شقایق کیل بگیره😌"
            bot.send_message(update.effective_message.chat.id, msg,
                             reply_to_message_id=update.effective_message.reply_to_message.message_id)
        elif update.effective_message.sticker.file_unique_id == 'AgADWwEAAuMMTxQ':
            msg = choice(items)
            bot.send_message(update.effective_message.chat.id, msg,
                             reply_to_message_id=update.effective_message.reply_to_message.message_id)
    else:
        if update.effective_message.sticker.file_unique_id == 'AgADWwEAAuMMTxQ':
            msg = choice(items)
            bot.send_message(update.effective_message.chat.id, msg,
                             reply_to_message_id=update.effective_message.message_id)
            return


def get_file_data(update, context):
    update.message.reply_text(str(update.message.reply_to_message.effective_attachment))

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.ERROR
)

logger = logging.getLogger(__name__)

def error_handler(update, context) -> None:
    """Log the error and send a telegram message to notify the developer."""
    # Log the error before we do anything else, so we can see it even if something breaks.
    logger.error(msg="Exception while handling an update:", exc_info=context.error)

    # traceback.format_exception returns the usual python message about an exception, but as a
    # list of strings rather than a single string, so we have to join them together.
    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = ''.join(tb_list)

    # Build the message with some markup and additional information about what happened.
    # You might need to add some logic to deal with messages longer than the 4096 character limit.
    message = (
        f'An exception was raised while handling an update\n'
        f'<pre>update = {html.escape(json.dumps(update.to_dict(), indent=2, ensure_ascii=False))}'
        '</pre>\n\n'
        f'<pre>context.chat_data = {html.escape(str(context.chat_data))}</pre>\n\n'
        f'<pre>context.user_data = {html.escape(str(context.user_data))}</pre>\n\n'
        f'<pre>{html.escape(tb_string)}</pre>'
    )

    # Finally, send the message
    context.bot.send_message(chat_id=-1001444185267, text=message, parse_mode='HTML')

def manager_app():
    handlers = [
        *join_options_handlers,
        CommandHandler('start', start),
        CommandHandler('rank', custom_rank),
        CommandHandler('ranks', display_ranks),
        CommandHandler('addemoji', add_emoji),
        CommandHandler('churn', get_churn_list),
        CommandHandler('get_stats', group_data.get_stats),
        CommandHandler('activity', activity.activity_command
                       , filters=Filters.group),
        CommandHandler('statistics', statistics_command
                       , filters=Filters.group
                       ),
        CommandHandler('action', set_action
                       , filters=Filters.group
                       ),
        CommandHandler('getd', get_file_data
                       , filters=Filters.chat(dev_group)
                       ),
        MessageHandler(Filters.animation | Filters.sticker, sticker_and_gif_commands),
        join_options_welcomes_command,
        CommandHandler('tag_del', mention_options.delete_messages,
                       filters=Filters.group),
        MessageHandler(Filters.group & Filters.text,
                       mention_options.define_message_as_mention),
        CallbackQueryHandler(stats.buttons, pattern='^stats '),
        CallbackQueryHandler(group_data.buttons, pattern='^group_data '),
        CallbackQueryHandler(advanced_commands_buttons, pattern='^setAction '),
        CallbackQueryHandler(del_action, pattern='^delAction ')

    ]

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(custom_helper_callback, pattern='^customHelper ')],

        states={

            GET_CLIENT_STR: [MessageHandler(Filters.regex('^tg.hl@'), get_client_str)]
        },

        fallbacks=[],
        allow_reentry=False

    )
    handlers.append(conv_handler)
    for handler in handlers:
        dispatcher.add_handler(handler)

    # conv_handler = ConversationHandler(
    #     entry_points=[CommandHandler('stt', start)],
    #     states={
    #
    #     },
    #     fallbacks=[CommandHandler('cn', start)],
    #     allow_reentry=True
    #
    # )
    #
    # dp.add_handler(conv_handler)
    print(12)
    u.start_polling(clean=True)
# u.idle()
