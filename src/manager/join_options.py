from . import get_cur, stats, bot, bot_admins
import telegram
from telegram.ext import run_async, CommandHandler, MessageHandler, CallbackQueryHandler, MessageFilter, Filters
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from . import RANK_STATEMENT as rank
from string import Template
from telegram.utils.helpers import escape_markdown, mention_markdown

bot = bot.get_me()
link = lambda text, url: f'[{text}]({url})'
mention = lambda text, user_id: link(text, f'tg://user?id={user_id}')

waiters = {}


class texts:
    farsoptions = {
        'header': 'تیتر',
        'first': 'اولین جوین', 'again': 'جوین دوباره',
        'idle': 'جوین هنگام عدم وجود بازی', 'ingame': 'جوین هنگام بازی', 'jointime': 'جوین در جوین تایم',
        'footer': 'پاورقی'
    }

    header = r'''Name: $name
Rank: $rank
به $title خوش اومدی\!
'''
    first = 'از این که گروه ما رو برای بازی انتخاب کردی متشکریم\n'
    again = 'خوشحالیم که دوباره به گروهمون برگشتی\n'
    idle = escape_markdown('بازی ای در جریان نیست! یکی شروع کن\n', version=2)
    ingame = escape_markdown('الان که وسط بازیه، صبر کن تا بازی تموم شه\n', version=2)
    jointime = escape_markdown('جوین تایمه! همین الان جوین شو\n', version=2)
    footer = escape_markdown('Games Played: $stats \n', version=2)

    setted = '{} ثبت شد.'

    send = 'الان داری <b>{}</b> رو ثبت میکنی\nمتنتو بفرست تا ذخیره کنم'


######################
#   OLD BULLSHITS    #
######################

def add_gp(group_id):
    query = """
    insert into v1.manager_join_setting_1(chat_id,created_at) values (%s, (now()at time zone 'Asia/Tehran')::timestamp)
    """
    conn, cur = get_cur()


def get_status(user_id, group_id):
    query = """select count(user_id)
  from v1.users_activity_log
 where group_id = %s and user_id = %s"""
    conn, cur = get_cur()

    cur.execute(query, (group_id, user_id))
    res = cur.fetchone()
    cur.close()
    if res:
        return res[0]
    return res


def get_group_status(group_id):
    query = "select state from v2.group_states where chat_id=%s;"
    conn, cur = get_cur()

    cur.execute(query, (group_id,))
    res = cur.fetchone()
    cur.close()
    if res:
        return res[0]


def get_all_groups_status():
    query = """
select distinct on (group_id) created_at, started_at, finished_at,game_bot,group_id
from v2.all_games
where canceled is false
order by group_id,created_at desc
    """
    conn, cur = get_cur()

    cur.execute(query)
    res = cur.fetchall()
    cur.close()
    if res:
        # print(res)
        return {i[4]: dict(created_at=i[0], started_at=i[1], finished_at=i[2], bot=i[3]) for i in res}
    return res


def is_admin(client, group_id, user_id):
    try:
        status = client.get_chat_member(group_id, user_id).status
        if status in ('creator', 'administrator'):
            return True
    except Exception as e:
        client.send_message(1372089184, str(e))


def add_action(group_id, message_id, user_id, action_id):
    conn, cur = get_cur()
    try:
        cur.execute("""
        insert into v2.groups_action_log("group_id","message_id","user_id","action_id")
        values (%s,%s,%s,%s)
        """, [group_id, message_id, user_id, action_id])
        conn.commit()
    except Exception as e:
        print(e)
        bot.send_message(951153044, ' '.join(e.args))


###########################
#    END OLD BULLSHITS    #
###########################

settings_buttons = lambda group, is_on: [
    [InlineKeyboardButton(f'خوشامدگویی | {"فعال✅" if is_on else "غیر فعال❌"}',
                          callback_data=f'ison_{not is_on}_{group}')],
    [InlineKeyboardButton('تیتر', callback_data=f'set_header_{group}')],
    [InlineKeyboardButton('اولین جوین', callback_data=f'set_firstjoin_{group}'),
     InlineKeyboardButton('جوین دوباره', callback_data=f'set_againjoin_{group}')],
    [InlineKeyboardButton('جوین در جوین تایم', callback_data=f'set_jointime_{group}'),
     InlineKeyboardButton('جوین زمان عدم بازی', callback_data=f'set_idle_{group}'),
     InlineKeyboardButton('جوین هنگام بازی', callback_data=f'set_ingame_{group}')],
    [InlineKeyboardButton('پاورقی', callback_data=f'set_footer_{group}')],
    [InlineKeyboardButton('پیش نمایش', callback_data=f'preview_{group}')],
    [InlineKeyboardButton('بازگشت به تنظیمات اولیه', callback_data=f'issure_{group}')],
    [InlineKeyboardButton('بستن تنظیمات', callback_data=f'close_')]
]
moz = """
متغیر های قابل استفاده در پیام:
‍‍<code>$name</code> نام کاربر
<code>$mention</code> منشن کاربر
<code>$username</code> یوزرنیم کاربر
<code>$id</code> آیدی عددی کاربر
<code>$gpid</code> آیدی عددی گروه
<code>$title</code> اسم گروه
<code>$stats</code> تعداد بازی های ورولف کاربر
<code>$rank</code> رنک منیجر کاربر
"""


def set_option(chat_id, option, value):
    conn, cur = get_cur()

    cur.execute('SELECT chat_id FROM v2.custom_welcome WHERE chat_id = %s', (chat_id,))
    exists = cur.fetchone()

    if exists:
        cur.execute('UPDATE v2.custom_welcome SET {} = %s WHERE chat_id = %s'.format(option), (value, chat_id))
        return conn.commit()
    else:
        cur.execute('INSERT INTO v2.custom_welcome (chat_id, {}) VALUES (%s, %s)'.format(option), (chat_id, value))
        return conn.commit()


def get_option(chat_id, option):
    conn, cur = get_cur()

    cur.execute('SELECT {} FROM v2.custom_welcome WHERE chat_id = %s'.format(option), (chat_id,))
    result = cur.fetchone()
    if result:
        return result[0]


def reset_options(chat_id):
    conn, cur = get_cur()

    cur.execute('DELETE FROM v2.custom_welcome WHERE chat_id = %s', (chat_id,))
    conn.commit()


class Group:
    def __init__(self, chat_id: int):
        self.chat_id = chat_id

    def set_header(self, header_text: str):
        set_option(self.chat_id, 'header', header_text)
        self.header = header_text
        return header_text

    def set_first(self, first_text: str):
        set_option(self.chat_id, 'new_member', first_text)
        self.first = first_text
        return first_text

    def set_again(self, again_text: str):
        set_option(self.chat_id, 'old_member', again_text)
        self.again = again_text
        return again_text

    def set_jointime(self, jointime_text: str):
        set_option(self.chat_id, 'jointime', jointime_text)
        self.jointime = jointime_text
        return jointime_text

    def set_idle(self, idle_text: str):
        set_option(self.chat_id, 'idle', idle_text)
        self.idle = idle_text
        return idle_text

    def set_ingame(self, ingame_text: str):
        set_option(self.chat_id, 'ingame', ingame_text)
        self.ingame = ingame_text
        return ingame_text

    def set_footer(self, footer_text: str):
        set_option(self.chat_id, 'footer', footer_text)
        self.footer = footer_text
        return footer_text

    def set_is_on(self, is_on: bool):
        set_option(self.chat_id, 'is_on', is_on)
        self.is_on = is_on
        return is_on

    def get_header(self):
        self.header = get_option(self.chat_id, 'header')
        return self.header

    def get_first(self):
        self.first = get_option(self.chat_id, 'new_member')
        return self.first

    def get_again(self):
        self.again = get_option(self.chat_id, 'old_member')
        return self.again

    def get_jointime(self):
        self.jointime = get_option(self.chat_id, 'jointime')
        return self.jointime

    def get_ingame(self):
        self.ingame = get_option(self.chat_id, 'ingame')
        return self.ingame

    def get_idle(self):
        self.idle = get_option(self.chat_id, 'idle')
        return self.idle

    def get_footer(self):
        self.footer = get_option(self.chat_id, 'footer')
        return self.footer

    def get_is_on(self) -> bool:
        self.is_on = get_option(self.chat_id, 'is_on') in (True, None)
        return self.is_on

    def set_on(self, on_off: bool):
        set_option(self.chat_id, 'is_on', on_off)
        self.is_on = on_off
        return on_off

    def reset(self):
        reset_options(self.chat_id)

    def __str__(self):
        return f'<Group: {self.chat_id}>'


def join_handler(update, context):
    message = update.message
    chat = message.chat
    news = message.new_chat_members
    user = message.from_user
    settings = Group(chat.id)
    group_info = get_group_status(chat.id)

    for member in news:
        msg = ''
        user_info = get_status(member.id, chat.id)

        if member.id == bot.id:
            if user.id in bot_admins():
                add_gp(chat.id)
                message.reply_text('گروه نصب شد خخخ')
            else:
                try:
                    message.reply_text('با ادمین هام تماس بگیرید')
                except:
                    pass
                chat.leave()
            return

        msg += (settings.get_header() or texts.header) + '\n'

        if user_info:
            back = True
            msg += (settings.get_again() or texts.again) + '\n'
        else:
            back = False
            msg += (settings.get_first() or texts.first) + '\n'

        if group_info:
            if group_info == 'idle':
                msg += (settings.get_idle() or texts.idle) + '\n'
            elif group_info == 'ingame':
                msg += (settings.get_ingame() or texts.ingame) + '\n'
            elif group_info == 'jointime':
                msg += (settings.get_jointime() or texts.jointime) + '\n'

        # old bullshits
        res = stats.get_player_stats_text(member.id, True)
        if not back:
            buttons = [
                [InlineKeyboardButton('✦sᴛᴀᴛs✦', callback_data='stats stats {player}'.format(player=member.id))],
                [InlineKeyboardButton('✦ᴅᴇᴀᴛʜ✦', callback_data='stats death {player}'.format(player=member.id)),
                 InlineKeyboardButton('✦ᴋɪʟʟᴇᴅ ʙʏ✦',
                                      callback_data='stats killedBy {player}'.format(player=member.id)),
                 InlineKeyboardButton('✦ᴋɪʟʟs✦', callback_data='stats kills {player}'.format(player=member.id))]
            ]
            if not res:
                buttons.append([InlineKeyboardButton('مسدود کردن کاربر از گروه⛔️',
                                                     callback_data='stats ban {player}'.format(player=member.id))])
            elif res['gamesPlayed'] <= 20:
                buttons.append([InlineKeyboardButton('مسدود کردن کاربر از گروه⛔️',
                                                     callback_data='stats ban {player}'.format(player=member.id))])


        else:
            buttons = [
                [InlineKeyboardButton('✦sᴛᴀᴛs✦', callback_data='stats stats {player}'.format(player=member.id))]]

        msg += (settings.get_footer() or (
                texts.footer + '\n' + r'**پیام خوشآمد اختصاصی خودتون رو با /welcome\_setting تنطیم کنید**'))

        name = member.first_name + (member.last_name or '')
        msg = Template(msg).safe_substitute(name=escape_markdown(name, version=2), id=member.id,
                                            gpid=escape_markdown(str(chat.id), version=2),
                                            mention=member.mention_markdown_v2(),
                                            title=escape_markdown(chat.title, version=2),
                                            username=('@' + escape_markdown(member.username,
                                                                            version=2)) if member.username else '',
                                            stats=res['gamesPlayed'] if res else '0',
                                            rank=escape_markdown(rank.UserStatus(member).status), version=2)

        chat.send_message(
            msg,
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        add_action(chat.id, message.message_id, member.id, 2)


def leave_handler(update, context):
    chat_id = update.message.chat_id
    user = update.message.from_user
    add_action(chat_id, update.message.message_id, user.id, 1)


def welcome_settings(update, context):
    message = update.message
    chat = message.chat

    message.reply_text('برای تغییر تنظیمات خوشامدگویی روی دکمه زیر کلیک کنید.', reply_markup=
    InlineKeyboardMarkup(
        [[InlineKeyboardButton('تغییر تنظیمات', url=f'https://t.me/{bot.username}/?start=wlcsettings{chat.id}')]]))


def start_welcome_settings(update, context):
    message = update.message
    bot = context.bot
    user = message.from_user
    try:
        group = int(message.text[18:])
    except:
        message.reply_text('what :|')
        return

    admin = is_admin(context.bot, group, user.id) or user.id in bot_admins()
    if not admin:
        message.reply_text('برو رایتو بده')
        return
    group = context.bot.get_chat(group)
    message.reply_text(f'<b>{group.title}</b> Welcome Setting:' + moz,
                       reply_markup=InlineKeyboardMarkup(settings_buttons(group.id, True)), parse_mode='html')


def callback_handler(update, context):
    global waiters

    bot = context.bot
    callback = update.callback_query
    user = callback.from_user
    message = callback.message
    data = callback.data

    if data.startswith('set_'):
        _, option, group = data.split('_')
        option = 'first' if option == 'firstjoin' else 'again' if option == 'againjoin' else option
        admin = is_admin(context.bot, group, user.id) or user.id in bot_admins()

        if admin:
            waiters.update({user.id: data})
            buttons = [[InlineKeyboardButton('بازگشت', callback_data=f'backwlc{group}')]]
            message.edit_text(texts.send.format(texts.farsoptions[option]) + '\n' + moz,
                              reply_markup=InlineKeyboardMarkup(buttons), parse_mode='html')
        else:
            waiters.pop(user.id)
            message.edit_text('برو رایتو بده')

    elif data.startswith('ison_'):
        _, is_on, group = data.split('_')
        ison = True if is_on == 'True' else False  # fuck `eval`
        setting_group = Group(group)

        admin = is_admin(context.bot, group, user.id) or user.id in bot_admins()

        if not admin:
            callback.answer('برو رایتو بده')
            return

        setting_group.set_on(ison)
        callback.answer(f'ولکام در گروه شما {"روشن" if ison else "خاموش"} شد', show_alert=True)
        bot.edit_message_reply_markup(message.chat.id, message_id=message.message_id,
                                      reply_markup=InlineKeyboardMarkup(settings_buttons(group, ison)))

    elif data.startswith('reset_'):
        group = data.split('_')[-1]
        setting_group = Group(int(group))
        admin = is_admin(context.bot, group, user.id) or user.id in bot_admins()

        if admin:
            ison = setting_group.get_is_on()
            setting_group.reset()
            setting_group.set_on(ison)
            callback.answer('تمام قسمت های ولکام اختصاصی به پیش فرض بازگشتند', show_alert=True)
            group_title = context.bot.get_chat(group).title
            message.edit_text(f'{group_title} Welcome Setting:',
                              reply_markup=InlineKeyboardMarkup(settings_buttons(group, Group(group).get_is_on())))
        else:
            message.edit_text('برو رایتو بده')

    elif data.startswith('preview_'):
        group = data.split('_')[1]
        settings = Group(group)
        msg = ''
        user_info = get_status(user.id, int(group))
        group_info = get_group_status(int(group))

        msg += (settings.get_header() or texts.header) + '\n'

        if user_info:
            back = True
            msg += (settings.get_again() or texts.again) + '\n'
        else:
            back = False
            msg += (settings.get_first() or texts.first) + '\n'

        if group_info:
            if group_info == 'idle':
                msg += (settings.get_idle() or texts.idle) + '\n'
            elif group_info == 'ingame':
                msg += (settings.get_ingame() or texts.ingame) + '\n'
            elif group_info == 'jointime':
                msg += (settings.get_jointime() or texts.jointime) + '\n'

        msg += (settings.get_footer() or (
                texts.footer + '\n' + r'**پیام خوشآمد اختصاصی خودتون رو با /welcome\_setting تنطیم کنید**'))

        message.edit_text(
            msg,
            parse_mode='MarkdownV2',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton('بازگشت', callback_data=f'backwlc{group}')]])
        )

    elif data.startswith('issure_'):
        group = data.split('_')[-1]
        buttons = [[InlineKeyboardButton('بله', callback_data=f'reset_{group}'),
                    InlineKeyboardButton('خیر', callback_data=f'backwlc{group}')]]
        message.edit_text('آیا از بازگشت تمام قسمت ها به حالت پیش فرض مطمعنید؟',
                          reply_markup=InlineKeyboardMarkup(buttons))

    elif data.startswith('close_'):
        message.edit_text('پنل بسته شد')

    else:
        group = data[7:]
        group_title = context.bot.get_chat(group).title
        message.edit_text(f'<b>{group_title}</b> Welcome Setting:' + moz,
                          reply_markup=InlineKeyboardMarkup(settings_buttons(group, Group(group).get_is_on())),
                          parse_mode='html')


def wait_handler(update, context):
    global waiters

    message = update.message
    user = message.from_user
    setting_group = waiters[user.id].split('_')[-1]
    group = Group(setting_group)

    admin = is_admin(context.bot, group.chat_id, user.id) or user.id in bot_admins()

    if not admin:
        message.reply_text('برو رایتو بده')
        return

    if waiters.get(user.id).startswith('set_header'):
        group.set_header(message.text_markdown_v2)
        message.reply_text(texts.setted.format(texts.farsoptions['header']))

    elif waiters.get(user.id).startswith('set_firstjoin'):
        group.set_first(message.text_markdown_v2)
        message.reply_text(texts.setted.format(texts.farsoptions['first']))

    elif waiters.get(user.id).startswith('set_againjoin'):
        group.set_again(message.text_markdown_v2)
        message.reply_text(texts.setted.format(texts.farsoptions['again']))

    elif waiters.get(user.id).startswith('set_jointime'):
        group.set_jointime(message.text_markdown_v2)
        message.reply_text(texts.setted.format(texts.farsoptions['jointime']))

    elif waiters.get(user.id).startswith('set_idle'):
        group.set_idle(message.text_markdown_v2)
        message.reply_text(texts.setted.format(texts.farsoptions['idle']))

    elif waiters.get(user.id).startswith('set_ingame'):
        group.set_ingame(message.text_markdown_v2)
        message.reply_text(texts.setted.format(texts.farsoptions['ingame']))

    elif waiters.get(user.id).startswith('set_footer'):
        group.set_footer(message.text_markdown_v2)
        message.reply_text(texts.setted.format(texts.farsoptions['footer']))

    waiters.pop(user.id)


def settings_stats(update, context):
    conn, cur = get_cur()
    cur.execute('SELECT chat_id FROM v2.custom_welcome')
    res = [i[0] for i in cur.fetchall()]
    result = ['Group Title | Creator']
    for x in enumerate(res):
        num, i = x
        cur.execute('SELECT title, link, creator FROM v1.all_group_helper WHERE group_id=%s', (i,))
        _res = cur.fetchone()
        if _res:
            result.append(f'`{num}-` [{_res[0]}]({_res[1]}) | {_res[2]}')
    update.message.reply_text('\n'.join(result), parse_mode='markdown', disable_web_page_preview=True)


class WaitingFilter(MessageFilter):
    def filter(self, message):
        global waiters
        return message.from_user.id in waiters


class JoinFilter(MessageFilter):
    def filter(self, message):
        return message.new_chat_members and (Group(message.chat.id).get_is_on())


class LeaveFilter(MessageFilter):
    def filter(self, message):
        return message.left_chat_member


handlers = [
    CommandHandler('welcome_setting', welcome_settings),
    MessageHandler(Filters.private & Filters.regex('^/start wlcsettings'), start_welcome_settings),
    MessageHandler(Filters.private & WaitingFilter(), wait_handler),
    MessageHandler(Filters.update & JoinFilter(), join_handler),
    MessageHandler(Filters.update & LeaveFilter(), leave_handler),
    CallbackQueryHandler(callback_handler, pattern='^set_|^reset|^backwlc|^issure|^close|^ison|^preview'),
]

status_handler = CommandHandler('welcomes', settings_stats)
