from random import choice

from cachetools import cached, TTLCache
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from telegram.ext import run_async
from telegram.utils.helpers import mention_html
from . import get_cur, bot
from .RANK_STATEMENT import check_channel_join

group_actions = {}

items = ['Belllaaaa ciaoooooo',
         'راکا چاک چاک راکا چاکا چاک چاک',
         'رابا بام بام رابا بام بام',
         'جفت شیش اومد تاس ناز شستش',
         'اینا صداهاشون لالایی برا گوشه',
         'سلامتی هرکسی تنهاس',
         'توی عمقم خود غواس',
         'کاش بزنه سیل بیاد به قول مهراد',
         'کُک دوس ندارم پپسی',
         'چشا روبه ابراس',
         'منو نمیکنه کسی میوت...جز خودم',
         'بنی آدم اعضای یکدیگرند',
         'میارم آرامش با اعتماد و احترام',
         'هیچ قله ای سخت نیست،کوهی بلند نیس',
         'اگه خورشید قهر کرد یا یه وقت هوس کرد\nآسمون با کلی ستاره هوامونو داره',
         'نه اصلا مهم نیست اگه باختم',
         'ماه بالاسر مهتاب جادمونو روشن کرد',
         'الماس خالصم اسمم مهراده\nطراحیم سیاهه مثل مداده',
         'گیر نده انقد نکن حسودی به من',
         'خفه خون بگیر خواهشا گوش خراشو',
         'دوست داره ولی بالاخات درنمیاد',
         'این روزا قلدر قلابی چه شده زیاد',
         'این بازی مال ماعه همتونم مال مایید',
         'دست کرد تو آستین نور\nماهو گذاشت تو دستمون',
         'میدونم میدونی فرق دارم من با اینا',
         'دلم پر حرفه میگم نگیا',
         'میدونم واقعی نیست ولی سخته',
         'همیشه میرم سمت درد سر تا میشن درا یکی یکی بسته',
         'نگران نباش،اشک نریز براش',
         'چشم چشم به راه مهتاب',
         'من شعله خورشیدم رنگین کمون بی رنگ کشتی بی لنگر آزاد و رها',
         'گل اگه خوشرنگه و خوشگل ینی لاش مار داره بپا',
         'با باد میرقصم',
         'من تا ابد میرقصم با آواز طوفان',
         'من اینو قول میدم بت قول میدم بت قول میدم بت']

shin_text = 'ببین\u200cمی\u200cارزه\u200cبازنشسته\u200cشین؟!\nیه\u200cکاری\u200cکنم\u200cتوجوونی\u200cشکسته\u200cشین\nمیخوای\u200cنگات\u200cکنن؟\nبیاپیشم\u200cبشین ...\nبغل\u200cدست #شین'


@cached(cache=TTLCache(maxsize=1024, ttl=1800))
def update_group_actions():
    global group_actions
    conn, cur = get_cur()
    query = """
select chat_id, file_unique_id, action_id, media_type
from v2.manager_advanced_commands
where disabled_at is null;
           """
    cur.execute(query)
    res = cur.fetchall()
    if not res:
        group_actions = {}
        return
    group_actions = {
        g[0]: {
            i[1]: {
                'action': i[2],
                'media_type': i[3]
            }
            for i in res if i[0] == g[0]
        } for g in res
    }
    # print(group_actions)


def add_action_to_db(media_unique_id, media_type, set_by, chat_id, action):
    try:
        conn, cur = get_cur()
        query = """
        INSERT INTO "v2"."manager_advanced_commands" ("chat_id", "file_unique_id", "action_id", "set_by", "created_at",
         "disabled_at", "disabled_by", "media_type")
         VALUES (%(chat_id)s, %(file_unique_id)s, %(action_id)s, %(set_by)s, DEFAULT, null, null, %(media_type)s)
        """
        cur.execute(query, {
            'chat_id': chat_id,
            'file_unique_id': media_unique_id,
            'action_id': action,
            'set_by': set_by,
            'media_type': media_type
        })
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False


def del_action_db(chat_id, file_unique_id, user_id):
    query = """UPDATE v2.manager_advanced_commands
                SET disabled_by=%(by)s, disabled_at=now()at time zone 'Asia/Tehran'
                WHERE chat_id=%(chat_id)s and file_unique_id=%(file_unique_id)s and disabled_at is null"""
    try:
        conn, cur = get_cur()
        cur.execute(query, {
            'chat_id': chat_id,
            'file_unique_id': file_unique_id,
            'by': user_id,
        })
        conn.commit()
        return True
    except Exception as e:
        print(e)
        return False


@check_channel_join
@run_async
def set_action(update, context):
    chat = update.effective_message.chat
    user = update.effective_message.from_user
    message = update.effective_message
    t = bot.get_chat_member(chat.id, user.id)
    if t.status not in ['administrator', 'creator']:
        return
    update_group_actions()

    if not message.reply_to_message:
        message.reply_text('لطفا به یک استیکر یا گیف این دستور را ارسال کنید')
        return

    sticker = message.reply_to_message.sticker
    animation = message.reply_to_message.animation
    if not sticker and not animation:
        message.reply_text('لطفا به یک استیکر یا گیف این دستور را ارسال کنید')
        return

    if sticker:
        media_type = 1
        media_unique_id = sticker.file_unique_id
    elif animation:
        media_type = 2
        media_unique_id = animation.file_unique_id
    else:
        media_type = 0
        media_unique_id = ''
    if not media_type:
        # todo: response media not detected
        message.reply_text('محتوا شناخته نشد')
        pass
    call_back = ' '.join(['setAction', str(chat.id), str(media_type), str(media_unique_id), str(user.id)])
    buttons = [
        [
            InlineKeyboardButton(f"یک اکشن از زیر انتخاب کنید", callback_data='setAction info')
        ], [
            InlineKeyboardButton(f"Kick", callback_data=call_back + ' ' + '2'),
            InlineKeyboardButton(f"ban", callback_data=call_back + ' ' + '1'),
            InlineKeyboardButton(f"Mute", callback_data=call_back + ' ' + '3'),
        ], [
            InlineKeyboardButton(f"Promote", callback_data=call_back + ' ' + '6'),
            InlineKeyboardButton(f"Unban", callback_data=call_back + ' ' + '4'),
            InlineKeyboardButton(f"Unmute", callback_data=call_back + ' ' + '5'),
        ]
    ]
    names = {1: 'Ban', 2: 'Kick', 3: 'Mute', 4: 'Unban', 5: 'Unmute', 6: 'Promote'}
    if media_unique_id in group_actions.get(chat.id, {}):
        buttons.append([InlineKeyboardButton(f"Delete {names[group_actions[chat.id][media_unique_id]['action']]}",
                                             callback_data=' '.join(
                                                 ['delAction', str(media_unique_id), str(user.id)]))])
    if media_type == 1:
        context.bot.send_sticker(chat.id, sticker.file_id, reply_markup=InlineKeyboardMarkup(buttons))
    elif media_type == 2:
        context.bot.send_animation(chat.id, animation.file_id, reply_markup=InlineKeyboardMarkup(buttons))


@run_async
def del_action(update, context):
    query = update.callback_query
    chat = query.message.chat
    user = query.from_user
    data = query.data.replace('delAction ', '', 1).split(' ')
    media_unique_id = data[0]
    user_id = int(data[1])
    if user.id != user_id:
        query.answer('این حذف اکشن برای شما نیست')
        return
    res = del_action_db(chat.id, media_unique_id, user_id)
    if res:
        global group_actions
        del group_actions[chat.id][media_unique_id]
        query.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton('Acion deleted', url='https://t.me/lupine_guys')]]))


@run_async
def advanced_commands_buttons(update, context):
    query = update.callback_query
    chat = query.message.chat
    user = query.from_user
    data = query.data.replace('setAction ', '', 1).split(' ')
    if data[0] == 'info':
        query.answer('از منوی زیر یکی از اکشن ها را انتخاب کنید تا روی مدیای مورد نظرتون تنظیم شود', alert=True)
        return
    chat_id = int(data[0])
    media_type = int(data[1])
    media_unique_id = data[2]
    user_id = int(data[3])
    action_id = int(data[4])
    if user.id != user_id:
        query.answer('این ثبت اکشن برای شما نیست')
        return
    res = add_action_to_db(media_unique_id, media_type, user_id, chat_id, action_id)
    if res:
        bot.send_message(chat_id, 'اکشن برای ' + ('گیف' if media_type == 2 else 'استیکر') + ' مورد نظر ثبت شد')
        if action_id == 1:
            action = 'Ban'
        elif action_id == 2:
            action = 'Kick'
        elif action_id == 3:
            action = 'Mute'
        elif action_id == 4:
            action = 'Unban'
        elif action_id == 5:
            action = 'Unmute'
        else:
            action = 'Promote'
        query.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton(action, url='https://t.me/lupine_guys')]]))
        global group_actions
        if chat.id not in group_actions:
            group_actions[chat.id] = {}
        group_actions[chat.id][media_unique_id] = {'action': action_id, 'media_type': media_type}
        return
    bot.send_message(chat_id, 'لطفا بعدا امتحان کنید')


def sticker_and_gif_commands(update, context):
    update_group_actions()
    chat = update.effective_message.chat
    user = update.effective_message.from_user
    message = update.effective_message

    sticker = message.sticker
    animation = message.animation
    item = sticker if sticker else animation
    file_unique_id = item.file_unique_id
    if user.id in (798494834, 951153044, 674759339, 1184814450, 120500168, 1321528127,
                   340724963, 1082983562, 638994540, 1211099939, 100432354,
                   1128542434, 823466362, 1104743660, 1154615413, 228500242, 1104933770, 424016354, 374256930,
                   615711287, 1050361384, 307938541, 173934801, 1362716749, 1255111343, 926855015, 1157066584,
                   1389165027, 1302739609, 1036334239, 547018899, 1142166355, 1327834355):
        if update.effective_message.reply_to_message:
            if user.id in (951153044, 674759339, 1184814450, 340724963, 1082983562, 1321528127,
                           638994540, 1154615413, 228500242, 1104933770, 424016354, 926855015, 120500168, 547018899,
                           1142166355, 1327834355):
                if file_unique_id == 'AgADcgADQuhxRw':
                    user_id = message.reply_to_message.from_user.id
                    if user_id != 1372089184:
                        bot.kick_chat_member(chat.id, user_id)
                    else:
                        update.message.reply_text('یودا: بخورش')
                    return
                elif file_unique_id == 'AgAD6QYAAkvsQFE':
                    msg = "you look like so cute"
                    bot.send_message(chat.id, msg,
                                     reply_to_message_id=message.reply_to_message.message_id)
                    return
                elif file_unique_id == 'AgADAQADm5N1Jw':
                    msg = "پشتش به ماست 🌞🧠"
                    bot.send_message(chat.id, msg,
                                     reply_to_message_id=message.reply_to_message.message_id)
                    return
            if file_unique_id == 'AgADWwEAAuMMTxQ' or file_unique_id == 'AgADGgIAAkbaXSc':
                msg = choice(items) if user.id != 228500242 else shin_text
                bot.send_message(chat.id, msg,
                                 reply_to_message_id=message.reply_to_message.message_id)
                return
            elif file_unique_id == 'AgADBwADchCYLw' and message.from_user.id == 798494834:
                msg = "رای تو شقایق کیل بگیره😌"
                bot.send_message(chat.id, msg,
                                 reply_to_message_id=message.reply_to_message.message_id)
                return
            elif file_unique_id == 'AgAD_wEAAuMMTxQ':
                if user.id in [1184814450, 1082983562, 1444748278, 951153044, 1142166355, 228500242, 1444748278,
                               340724963, 1327834355]:
                    message.reply_to_message.reply_voice(
                        'AwACAgQAAx0CVhSEswABBn-rX9uhivVFTT4RjRijhEu2KqDyBDwAAk0GAAJSOHBSBeVJQXfAnYoeBA')
        else:
            if file_unique_id == 'AgAD_wEAAuMMTxQ':
                if user.id in [1184814450, 1082983562, 1444748278, 951153044, 1142166355, 228500242, 1444748278,
                               340724963, 1327834355]:
                    message.reply_voice(
                        'AwACAgQAAx0CVhSEswABBn-rX9uhivVFTT4RjRijhEu2KqDyBDwAAk0GAAJSOHBSBeVJQXfAnYoeBA')
                return

            if file_unique_id == 'AgADWwEAAuMMTxQ' or file_unique_id == 'AgADGgIAAkbaXSc':
                msg = choice(items)
                bot.send_message(chat.id, msg,
                                 reply_to_message_id=message.message_id)
                return

    if not message.reply_to_message:
        return

    actions = group_actions[chat.id] if chat.id in group_actions else {}
    if not actions:
        return
    t = bot.get_chat_member(chat.id, user.id)
    msg = '{admin} {actioned} {user}'
    if file_unique_id in actions:
        action = actions[file_unique_id]['action']
        if action == 1 and t.status in ['administrator', 'creator']:
            context.bot.kick_chat_member(chat.id, message.reply_to_message.from_user.id)
            actioned = 'Banned'
        elif action == 2 and t.status in ['administrator', 'creator']:
            context.bot.kick_chat_member(chat.id, message.reply_to_message.from_user.id)

            context.bot.restrictChatMember(chat.id, message.reply_to_message.from_user.id, ChatPermissions(
                can_send_messages=True, can_send_media_messages=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_change_info=True, can_invite_users=True, can_pin_messages=True
            ))
            actioned = 'Kicked'
        elif action == 3 and t.status in ['administrator', 'creator']:
            context.bot.restrictChatMember(chat.id, message.reply_to_message.from_user.id, ChatPermissions(False))
            actioned = 'Muted'
        elif action == 4 and t.status in ['administrator', 'creator']:
            context.bot.restrictChatMember(chat.id, message.reply_to_message.from_user.id, ChatPermissions(
                can_send_messages=True, can_send_media_messages=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_change_info=True, can_invite_users=True, can_pin_messages=True
            ))
            actioned = 'Unbanned'
        elif action == 5 and t.status in ['administrator', 'creator']:
            context.bot.restrictChatMember(chat.id, message.reply_to_message.from_user.id, ChatPermissions(
                can_send_messages=True, can_send_media_messages=True, can_send_polls=True,
                can_send_other_messages=True, can_add_web_page_previews=True,
                can_change_info=True, can_invite_users=True, can_pin_messages=True
            ))
            actioned = 'Unmuted'
        elif action == 6 and t.can_promote_members:
            bot.promote_chat_member(chat.id, message.reply_to_message.from_user.id, can_change_info=False,
                                    can_delete_messages=True, can_invite_users=True,
                                    can_restrict_members=False, can_pin_messages=True,
                                    can_promote_members=False, timeout=None)
            actioned = 'Promoted'
        else:
            return
        context.bot.send_message(chat.id, msg.format(admin=mention_html(user.id, user.full_name), actioned=actioned,
                                                     user=mention_html(update.message.reply_to_message.from_user.id,
                                                                       update.message.reply_to_message.from_user.full_name)),
                                 parse_mode='html')
