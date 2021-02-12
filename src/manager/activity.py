from datetime import datetime

from pytz import timezone
from telegram import Bot
from telegram.ext import run_async
from telegram.utils.helpers import mention_html, create_deep_linked_url
from .RANK_STATEMENT import check_channel_join
from . import bot, get_cur, bot_admins


iran = timezone('Asia/Tehran')


def now():
    sa_time = datetime.now(iran)
    return sa_time.strftime('%Y-%m-%d %H:%M:%S')


def admin_data(chat_id, user_id, time):
    query = f'''

with play as (
    SELECT count(group_id) as plays
    FROM v2.users_activity_log_v2
    WHERE user_id = %(user_id)s AND group_id = %(chat_id)s AND created_at :: date>= (%(now)s::DATE - interval '%(time)s days')
),
     afk as (
         SELECT count(chat_id) as afks
         FROM v2.users_afks
         WHERE user_id = %(user_id)s AND chat_id = %(chat_id)s AND afk_at :: date>= (%(now)s::DATE - interval '%(time)s days')
     ),
     tag as (
         SELECT count(group_id) as tags
         FROM v1.manager_delete_message
         WHERE user_id = %(user_id)s AND group_id = %(chat_id)s AND created_at :: date>= (%(now)s::DATE - interval '%(time)s days')
     ),
     msg as (
         SELECT count(message_id) as tags
         FROM v1.manager_players_messages
         WHERE user_id = %(user_id)s AND chat_id = %(chat_id)s AND message_at :: date>= (%(now)s::DATE - interval '%(time)s days')
     )
    SELECT *
    from play, afk, tag, msg
'''
    try:
        conn, cur = get_cur()
        cur.execute(query, {'user_id': user_id, 'chat_id': chat_id, 'now': now(), 'time': time})
        res = cur.fetchone()
        cur.close()

        return res[0], res[1], res[2], res[3]
    except Exception as e:
        print(e)
        return 0, 0, 0


def admin_detailed_data(chat_id, user_id, time):
    play_query = f''' 
SELECT count(group_id) as                                             plays,
           case
               when created_at::time between '03:00:00' and '10:59:59' then 1
               when created_at::time between '11:00:00' and '18:59:59' then 2
               when created_at::time between '19:00:00' and '02:59:59' then 3
               else 3 end  as                                             plays_time,
           count(is_winner) filter ( where is_winner is TRUE )            wins,
           count(is_alive) filter ( where is_alive is TRUE)               alives,
           count(is_alive) filter ( where is_alive is TRUE and is_winner) win_and_alive
    FROM v2.users_activity_log_v2
    WHERE user_id = %(user_id)s
      AND group_id = %(chat_id)s
      AND created_at :: date >= (%(now)s::DATE - interval '%(days)s days')
    group by plays_time '''
    tag_query = f'''

         SELECT count(group_id) as tags,
                case
                    when created_at::time between '03:00:00' and '10:59:59' then 1
                    when created_at::time between '11:00:00' and '18:59:59' then 2
                    when created_at::time between '19:00:00' and '02:59:59' then 3
                    else 3 end  as tags_time

         FROM v1.manager_delete_message
         WHERE user_id = %(user_id)s
           AND group_id = %(chat_id)s
           AND created_at :: date >= (%(now)s::DATE - interval '%(days)s days')
         group by tags_time'''
    afk_query = f'''
         SELECT count(chat_id) as afks,
                case
                    when afk_at::time between '03:00:00' and '10:59:59' then 1
                    when afk_at::time between '11:00:00' and '18:59:59' then 2
                    when afk_at::time between '19:00:00' and '02:59:59' then 3
                    else 3 end as afks_time

         FROM v2.users_afks
         WHERE user_id = %(user_id)s
           AND chat_id = %(chat_id)s
           AND afk_at :: date >= (%(now)s::DATE - interval '%(days)s days')
         group by afks_time'''
    msg_query = f'''
         SELECT count(message_id) as msgs,
                case
                    when message_at::time between '03:00:00' and '10:59:59' then 1
                    when message_at::time between '11:00:00' and '18:59:59' then 2
                    when message_at::time between '19:00:00' and '02:59:59' then 3
                    else 3 end as msgs_time

         FROM v1.manager_players_messages
         WHERE user_id = %(user_id)s
           AND chat_id = %(chat_id)s
           AND message_at :: date >= (%(now)s::DATE - interval '%(days)s days')
         group by msgs_time'''
    try:
        conn, cur = get_cur()
        cur.execute(play_query, {'user_id': user_id, 'chat_id': chat_id, 'now': now(), 'days': time})
        play_res = cur.fetchall()
        cur.execute(tag_query, {'user_id': user_id, 'chat_id': chat_id, 'now': now(), 'days': time})
        tag_res = cur.fetchall()
        cur.execute(afk_query, {'user_id': user_id, 'chat_id': chat_id, 'now': now(), 'days': time})
        afk_res = cur.fetchall()
        cur.execute(msg_query, {'user_id': user_id, 'chat_id': chat_id, 'now': now(), 'days': time})
        msg_res = cur.fetchall()
        play = {1: {}, 2: {}, 3: {}}
        tag = {1: 0, 2: 0, 3: 0}
        afk = {1: 0, 2: 0, 3: 0}
        msg = {1: 0, 2: 0, 3: 0}
        cur.close()
        if play_res:
            for i in play_res:
                win_and_alive = i[4]
                alives = i[3]
                wins = i[2]
                plays_time = i[1]
                plays = i[0]
                play.update({
                    plays_time: {'plays': plays, 'wins': wins, 'alives': alives, 'win_and_alive': win_and_alive}
                })
        if tag_res:
            for i in tag_res:
                tags = i[0]
                tags_time = i[1]
                tag.update({tags_time: tags})
        if afk_res:
            for i in afk_res:
                afks = i[0]
                afks_time = i[1]
                afk.update({afks_time: afks})
        if msg_res:
            for i in msg_res:
                msgs = i[0]
                msgs_time = i[1]
                msg.update({msgs_time: msgs})
        return play, tag, afk, msg

    except Exception as e:
        print(e)
        return 0, 0, 0, 0


def get_admins_data(chat_id, day):
    admins = bot.get_chat_administrators(chat_id)
    data = {}
    for admin in admins:
        if admin.user.is_bot:
            continue
        game, afk, tag, msg = admin_data(chat_id, admin.user.id, day)
        data.update({admin.user.id: {'username': admin.user.name, 'tag': tag, 'game': game, 'afk': afk, 'msg':msg}})
    return data

@check_channel_join
@run_async
def activity_command(update, context):
    chat = update.effective_message.chat
    user = update.effective_message.from_user
    message = update.effective_message
    data = message.text.split(' ')
    day = 7
    if len(data) > 1 and data[1].isdigit():
        day = int(data[1])
        if day > 42:
            update.message.reply_text('داده ها حداکثر 42 روز نگهداری میشوند')
            return

    data = get_admins_data(chat.id, day)
    if user.id not in data and user.id not in bot_admins():
        update.message.reply_text('آمار مدیران فقط برای مدیران قابل مشاهده است زاخا')
        return

    if update.effective_message.reply_to_message:
        target_user = update.effective_message.reply_to_message.from_user.id
        target_chat = chat.id
        msg = get_user_data(target_user, target_chat, day, user)
        try:
            bot.send_message(user.id, msg, 'HTML', disable_web_page_preview=True)
            update.message.reply_text('آمارشو پی وی گذاشتم')
            return
        except Exception as e:
            print(e)
            update.message.reply_text('اول مطمئن شو که استارت کردی منو ')
            return

    header = """◗آمار ادمین ها توی {days} روز گذشته در گروه {group} 📊V6.1

🎮 تعداد بازی ها
🔔 تعداد تگ ها
😴 تعداد AFK ها
💬 تعداد پیام ها
@username  |🎮|🔔|😴|💬

""".format(days=day, group=bot.get_chat(chat.id).title)
    args = ['{}  | {} | {} | {} | {} | <a href="{}">Detail</a>'.format(
        mention_html(i, data[i]['username'] if data[i]['username'] else str(i)),
        data[i]['game'],
        data[i]['tag'],
        data[i]['afk'],
        data[i]['msg'],
        create_deep_linked_url(bot.username, 'adminStats_{}_{}_{}'.format(i, chat.id, day))
        # 'https://t.me/manage_ww_bot?start=adminStats_{}_{}'.format(i, chat.id)
    ) for i in data]
    try:
        bot.send_message(user.id, header + '\n'.join(args), 'HTML', disable_web_page_preview=True)
        update.message.reply_text('پی وی چک')
    except Exception as e:
        print(e)
        update.message.reply_text('اول مطمئن شو که استارت کردی منو ')


def start_activity(update, context, data):
    chat = update.effective_message.chat
    user = update.effective_message.from_user
    # todo get target from data
    target_user = int(data[1])
    target_group = int(data[2])
    day = int(data[3])
    group_admins = bot.get_chat_administrators(target_group)
    admins_id = []
    for i in group_admins:
        admins_id.append(i.user.id)
    if user.id not in admins_id and user.id not in bot_admins():
        update.message.reply_text('آمار مدیران فقط برای مدیران قابل مشاهده است')
        return
    if target_user not in admins_id:
        update.message.reply_text('کاربر مورد نظر ادمین نیست')
        return
    message = get_user_data(target_user, target_group, day, user)
    bot.send_message(user.id, message)
    return data


def get_user_data(user_id, group_id, days, for_user):
    try:
        data = admin_detailed_data(group_id, user_id, days)

        message = """◗آمار {name} توی {days} روز گذشته در گروه {group} 

🎮 تعداد بازی ها
🔔 تعداد تگ ها
😴 تعداد AFK ها
💬 تعداد پیام ها
⏱ زمان
🏞صبح (11-03)
🌇ظهر (19-11)
🌃شب (03-19)


📊 آمار کلی:
⏱|🎮|🔔|😴|💬
🏞| {plays_1} | {tags_1} | {afks_1} | {msgs_1} 
🌇| {plays_2} | {tags_2} | {afks_2} | {msgs_2}
🌃| {plays_3} | {tags_3} | {afks_3} | {msgs_3}

‏﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌
🎮 آمار بازی ها:

نوبت 🏞 
┃بازی های انجام شده: {plays_1}
┃بازی های برنده شده: {wins_1}
┃بازی های زنده مانده: {alives_1}
┃بازی های زنده مانده و برنده شده: {win_and_alive_1}

نوبت 🌇 
┃بازی های انجام شده: {plays_2}
┃بازی های برنده شده: {wins_2}
┃بازی های زنده مانده: {alives_2}
┃بازی های زنده مانده و برنده شده: {win_and_alive_2}

نوبت 🌃 
┃بازی های انجام شده: {plays_3}
┃بازی های برنده شده: {wins_3}
┃بازی های زنده مانده: {alives_3}
┃بازی های زنده مانده و برنده شده: {win_and_alive_3}

‏﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌
🔔 آمار تگ ها:

نوبت 🏞 
┛‏ تگ های انجام شده:{tags_1}

نوبت 🌇 
┛‏ تگ های انجام شده:{tags_2}

نوبت 🌃 
┛‏ تگ های انجام شده:{tags_3}

‏﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌
😴 آمار afkها:

نوبت 🏞 
┛‏ تعداد afkها: {afks_1}

نوبت 🌇 
┛‏ تعداد afkها: {afks_2}

نوبت 🌃 
┛‏ تعداد afkها: {afks_3}

‏﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌﹌
😴 آمار پیام ها:

نوبت 🏞 
┛‏ تعداد پیام ها: {msgs_1}

نوبت 🌇 
┛‏ تعداد پیام ها: {msgs_2}

نوبت 🌃 
┛‏ تعداد پیام ها: {msgs_3}

Made for {user}
        """
        try:
            user_name = bot.get_chat_member(group_id, user_id).user.name
        except Exception as e:
            print(e)
            user_name = user_id
        group_name = bot.get_chat(group_id).title

        return message.format(
            name=''.join(user_name),
            group=group_name,
            plays_1=data[0][1]['plays'] if 'plays' in data[0][1] else '0',
            plays_2=data[0][2]['plays'] if 'plays' in data[0][2] else '0',
            plays_3=data[0][3]['plays'] if 'plays' in data[0][3] else '0',
            wins_1=data[0][1]['wins'] if 'wins' in data[0][1] else '0',
            wins_2=data[0][2]['wins'] if 'wins' in data[0][2] else '0',
            wins_3=data[0][3]['wins'] if 'wins' in data[0][3] else '0',
            alives_1=data[0][1]['alives'] if 'alives' in data[0][1] else '0',
            alives_2=data[0][2]['alives'] if 'alives' in data[0][2] else '0',
            alives_3=data[0][3]['alives'] if 'alives' in data[0][3] else '0',
            win_and_alive_1=data[0][1]['win_and_alive'] if 'win_and_alive' in data[0][1] else '0',
            win_and_alive_2=data[0][2]['win_and_alive'] if 'win_and_alive' in data[0][2] else '0',
            win_and_alive_3=data[0][3]['win_and_alive'] if 'win_and_alive' in data[0][3] else '0',
            tags_1=data[1][1],
            tags_2=data[1][2],
            tags_3=data[1][3],
            afks_1=data[2][1],
            afks_2=data[2][2],
            afks_3=data[2][3],
            msgs_1=data[3][1],
            msgs_2=data[3][2],
            msgs_3=data[3][3],
            user=for_user.name,
            days=days)
    except Exception as e:
        print(e)
        return 'مشکل در بارگذاری اطلاعات کاربر'

