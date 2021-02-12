import datetime

import telegram
import telegram.ext
from pytz import timezone

from . import get_cur, bot_admins, bot
# from .manager_v1 import iran
from telegram.utils.helpers import mention_html, create_deep_linked_url
from .RANK_STATEMENT import check_channel_join
iran = timezone('Asia/Tehran')


def now(day_ago=0) -> datetime.datetime:
    sa_time = datetime.datetime.now(iran) - datetime.timedelta(days=day_ago)
    return sa_time


def get_action_users(action_id, group_id, from_date, to_date):
    """"""
    query = """
select ac.user_id, us.username 
from v2.groups_action_log ac
join v1.rulesaver_users us on us.user_id = ac.user_id
where ac.group_id=%(group_id)s and action_id=%(action_id)s 
and ac.created_at::date between %(from_date)s::date and %(to_date)s::date
group by 1, 2
    """
    conn, cur = get_cur()
    cur.execute(query, {
        'group_id': group_id,
        'from_date': from_date,
        'to_date': to_date,
        'action_id': action_id
    })
    res = cur.fetchall()
    return {i[0]: {'username': i[1]} for i in res} if res else res


def get_users_plays_with_action_id(action_id, group_id, from_date, to_date):
    """"""
    query = """
select ac.user_id,
        count(ac.message_id),
        count(is_alive)filter ( where  is_alive = True),
        count(is_winner)filter ( where  is_winner = True),
        count(ac.message_id)filter ( where  is_winner = True and is_alive= True),
        us.username 
from v2.groups_action_log ac
join v2.users_activity_log_v2 log on ac.user_id=log.user_id and ac.group_id=log.group_id
join v1.rulesaver_users us on us.user_id=ac.user_id
where ac.group_id=%(group_id)s and action_id=%(action_id)s
  and ac.created_at::date between %(from_date)s::date and %(to_date)s
  and log.created_at::date between %(from_date)s::date and %(to_date)s
group by ac.user_id, us.username 
order by 2 desc 
    """
    conn, cur = get_cur()
    cur.execute(query, {
        'group_id': group_id,
        'from_date': from_date,
        'to_date': to_date,
        'action_id': action_id
    })
    res = cur.fetchall()
    return {i[0]: {'played': i[1], 'alive': i[2], 'winner': i[3], 'alive-winner': i[4], 'username': i[5]} for i in res}


def get_users_plays_by_group(group_id, from_date, to_date):
    """"""
    query = """
select ac.user_id,
        count(ac.message_id),
        count(is_alive)filter ( where  is_alive = True),
        count(is_winner)filter ( where  is_winner = True),
        count(ac.message_id)filter ( where  is_winner = True and is_alive= True),
        us.username 
from v2.users_activity_log_v2 ac
join v1.rulesaver_users us on us.user_id=ac.user_id
where ac.group_id=%(group_id)s
and  ac.created_at::date between %(from_date)s::date and %(to_date)s
group by ac.user_id, us.username 
order by 2 desc
"""
    conn, cur = get_cur()
    cur.execute(query, {
        'group_id': group_id,
        'from_date': from_date,
        'to_date': to_date
    })
    res = cur.fetchall()
    return {i[0]: {'played': i[1], 'alive': i[2], 'winner': i[3], 'alive-winner': i[4], 'username': i[5]} for i in res}


def growth_status_str(status):
    if status > 00.01:
        string = '🟢 {:.2f}%'.format(status)
        return string
    elif status < -00.01:
        string = '🔴 {:.2f}%'.format(status)
        return string
    else:
        string = '⚪️ 00.00%'.format(status)
        return string


def calculate_growth(group_id, delay_day):
    current = get_users_plays_by_group(group_id, now(delay_day), now())
    current_play_total = len([user for user in current])
    current_play_played_more_than_five = len([user for user in current if current[user]['played'] >= 5])
    current_play_played_more_than_fifeteen = len([user for user in current if current[user]['played'] >= 15])
    current_play_played_more_than_twenty_five = len([user for user in current if current[user]['played'] >= 25])

    past = get_users_plays_by_group(group_id, now(delay_day * 2), now(delay_day))
    past_play_total = len([user for user in past])
    past_play_played_more_than_five = len([user for user in past if past[user]['played'] >= 5])
    past_play_played_more_than_fifeteen = len([user for user in past if past[user]['played'] >= 15])
    past_play_played_more_than_twenty_five = len([user for user in past if past[user]['played'] >= 25])

    play_total = current_play_total / past_play_total if past_play_total else 00.00
    play_played_more_than_five = current_play_played_more_than_five / past_play_played_more_than_five if past_play_played_more_than_five else 00.00
    play_played_more_than_fifeteen = current_play_played_more_than_fifeteen / past_play_played_more_than_fifeteen if past_play_played_more_than_fifeteen else 00.00
    play_played_more_than_twenty_five = current_play_played_more_than_twenty_five / past_play_played_more_than_twenty_five if past_play_played_more_than_twenty_five else 00.00

    play_total = 100 - play_total * 100 if play_total else 00.00
    play_played_more_than_five = 100 - play_played_more_than_five * 100 if play_played_more_than_five else 00.00
    play_played_more_than_fifeteen = 100 - play_played_more_than_fifeteen * 100 if play_played_more_than_fifeteen else 00.00
    play_played_more_than_twenty_five = 100 - play_played_more_than_twenty_five * 100 if play_played_more_than_twenty_five else 00.00

    return [growth_status_str(i) for i in [
        play_total,
        play_played_more_than_five,
        play_played_more_than_fifeteen,
        play_played_more_than_twenty_five]]


"""
‏{play_total} کلا بازی کردند توی گروه که
‏{play_played_more_than_five} انها حداقل 5 بازی انجام داده اند،
‏{play_played_more_than_fifeteen} انها حداقل 15 بازی انجام داده اند،
‏{play_played_more_than_twenty_five} انها حداقل 25 بازی انجام داده اند.
"""


def get_data_str(group_obj, user_obj, days_ago=4):
    """get detailed text for statistics"""
    text = """مقداری آمار از گروه {group_name} در {days_ago} روز گذشته📈 v2.8

تعداد افرادی که وارد گروه شدند: ‏{join_total} {link_join_total}
افرادی وارد گروه شدند و بازی کردند: ‏{join_total_played} {link_join_total_played}
افرادی که وارد گروه شدند و حداقل 5 بازی کردند: ‏{join_played_more_than_five} {link_join_played_more_than_five}
افرادی که وارد گروه شدند و حداقل 15 بازی انجام دادند: ‏{join_played_more_than_fifeteen} {link_join_played_more_than_fifeteen}

کل بازیکنان: {play_total} {play_total_growth} {play_total_link}
بازیکنان با حداقل 5 بازی: {play_played_more_than_five} {play_played_more_than_five_growth} {play_played_more_than_five_link}
بازی کنان با حداقل 15 بازی: {play_played_more_than_fifeteen} {play_played_more_than_fifeteen_growth} {play_played_more_than_fifeteen_link}
بازیکنان با حداقل 25 بازی: {play_played_more_than_twenty_five} {play_played_more_than_twenty_five_growth} {play_played_more_than_twenty_five_link}

Made for {user}"""

    total_joined = get_action_users(2, group_obj.id, now(days_ago), now())
    total = len(total_joined)
    data = get_users_plays_with_action_id(2, group_obj.id, now(days_ago), now())
    total_played = len([user for user in data])
    played_more_than_five = len([user for user in data if data[user]['played'] >= 5])
    played_more_than_fifeteen = len([user for user in data if data[user]['played'] >= 15])
    data = get_users_plays_by_group(group_obj.id, now(days_ago), now())
    play_total = len([user for user in data])
    play_played_more_than_five = len([user for user in data if data[user]['played'] >= 5])
    play_played_more_than_fifeteen = len([user for user in data if data[user]['played'] >= 15])
    play_played_more_than_twenty_five = len([user for user in data if data[user]['played'] >= 25])
    play_total_growth, play_played_more_than_five_growth, play_played_more_than_fifeteen_growth, \
    play_played_more_than_twenty_five_growth = calculate_growth(group_obj.id, days_ago)

    link_message = '<a href="{}">لیست کاربران</a>'
    link_players_pattern = 'statistics_getusers_{chat_id}_{days}_{play_limit}'
    link_joined_pattern = 'statistics_getjoins_{chat_id}_{days}_{play_limit}'
    return text.format(
        days_ago=days_ago,
        group_name=group_obj.title,

        join_total=total,
        join_total_played=total_played,
        join_played_more_than_five=played_more_than_five,
        join_played_more_than_fifeteen=played_more_than_fifeteen,

        link_join_total=link_message.format(create_deep_linked_url(
            bot.username,
            link_joined_pattern.format(chat_id=str(group_obj.id).replace('-100', ''), days=days_ago, play_limit=0))),
        link_join_total_played=link_message.format(create_deep_linked_url(
            bot.username,
            link_joined_pattern.format(chat_id=str(group_obj.id).replace('-100', ''), days=days_ago, play_limit=1))),
        link_join_played_more_than_five=link_message.format(create_deep_linked_url(
            bot.username,
            link_joined_pattern.format(chat_id=str(group_obj.id).replace('-100', ''), days=days_ago, play_limit=5))),
        link_join_played_more_than_fifeteen=link_message.format(create_deep_linked_url(
            bot.username,
            link_joined_pattern.format(chat_id=str(group_obj.id).replace('-100', ''), days=days_ago, play_limit=15))),

        play_total=play_total,
        play_played_more_than_five=play_played_more_than_five,
        play_played_more_than_fifeteen=play_played_more_than_fifeteen,
        play_played_more_than_twenty_five=play_played_more_than_twenty_five,

        play_total_growth=play_total_growth,
        play_played_more_than_five_growth=play_played_more_than_five_growth,
        play_played_more_than_fifeteen_growth=play_played_more_than_fifeteen_growth,
        play_played_more_than_twenty_five_growth=play_played_more_than_twenty_five_growth,

        play_played_more_than_twenty_five_link=link_message.format(create_deep_linked_url(
            bot.username,
            link_players_pattern.format(chat_id=str(group_obj.id).replace('-100', ''), days=days_ago, play_limit=25))),
        play_played_more_than_fifeteen_link=link_message.format(create_deep_linked_url(
            bot.username,
            link_players_pattern.format(chat_id=str(group_obj.id).replace('-100', ''), days=days_ago, play_limit=15))),
        play_played_more_than_five_link=link_message.format(create_deep_linked_url(
            bot.username,
            link_players_pattern.format(chat_id=str(group_obj.id).replace('-100', ''), days=days_ago, play_limit=5))),
        play_total_link=link_message.format(create_deep_linked_url(
            bot.username,
            link_players_pattern.format(chat_id=str(group_obj.id).replace('-100', ''), days=days_ago, play_limit=0))),

        user=mention_html(user_obj.id, user_obj.name)
    )


def is_admin(bot, group, user):
    try:
        user_status = bot.get_chat_member(group, user).status
        return True if user_status in ('administrator', 'creator') else ''
    except:
        return False

@check_channel_join
def statistics_command(update, context):
    message = update.message
    bot = context.bot
    user = message.from_user
    group = message.chat
    message = update.effective_message
    data = message.text.split(' ')
    day = 4
    if len(data) > 1 and data[1].isdigit():
        day = int(data[1])
        if day > 42:
            update.message.reply_text('داده ها حداکثر 42 روز نگهداری میشوند')
            return

    try:
        if is_admin(bot, group.id, user.id) or user.id in bot_admins():
            message.from_user.send_message(
                text=get_data_str(group, user, day),
                parse_mode='HTML'
                , disable_web_page_preview=True
            )

            message.reply_text(
                text='پیوی چک',
                quote=True
            )

        else:
            message.reply_text(
                text='داش تو که ادمین نیستی',
                quote=True
            )
    except:
        message.reply_text(
            text='نتونستم آمارو برات بفرستم. مطمعن شو رباتو استارت کردی و یه بار دیگه بزن `/statistics`',
            quote=True,
            parse_mode='markdown'
        )


def split_users_into_msgs(users, split, user_text, header=''):
    msgs = []
    tmp = []
    for user_id, details in users.items():
        if len(tmp) == split:
            msgs.append(header + '\n\n' + '\n'.join([user_text.format(
                user=mention_html(d[0], ('@' + str(d[1].get('username'))
                                         ) if d[1].get('username') and d[1].get('username') != 'None' else str(d[0])),
                play_count=d[1].get('played'),
                alive=d[1].get('alive'),
                winner=d[1].get('winner'),
                alive_winner=d[1].get('alive-winner'),
            ) for d in tmp]))
            tmp = []
        tmp.append([user_id, details])
    if tmp:
        msgs.append(header + '\n\n' + '\n'.join([user_text.format(
            user=mention_html(d[0], ('@' + str(d[1].get('username'))
                                     ) if d[1].get('username') and d[1].get('username') != 'None' else str(d[0])),
            play_count=d[1].get('played'),
            alive=d[1].get('alive'),
            winner=d[1].get('winner'),
            alive_winner=d[1].get('alive-winner'),
        ) for d in tmp]))
    return msgs


def statistics_detail(update: telegram.Update, context: telegram.ext.CallbackContext, data):
    """ get details of these data """
    chat = update.effective_message.chat
    user = update.effective_message.from_user
    message = update.effective_message

    if data[1] == "getusers":
        waiting_message = context.bot.send_message(chat.id, 'در حال بررسی داده ها...')
        group_id = int('-100' + data[2])
        delay_days = int(data[3])
        play_count = int(data[4])
        current = get_users_plays_by_group(group_id, now(delay_days), now())
        players_with_count = lambda count: {u: current[u] for u in current if current[u]['played'] > count}
        users = players_with_count(play_count)

        header = '🙎|⛹️|🙂|🎊|🥳'
        user_text = """{user} | {play_count} | {alive} | {winner} | {alive_winner}"""
        res = split_users_into_msgs(users, 50, user_text, header)
        waiting_message.delete()
        [context.bot.send_message(user.id, msg, parse_mode='HTML', disable_web_page_preview=True) for msg in res]
        if not res:
            update.message.reply_text('لیست خالیست')
        else:
            update.message.reply_text('''*راهنما*
‎🙎: کاربر
‎⛹️ :بازی انجام شده
‎🙂 :زنده مونده تا‌ انتهای بازی
‎🎊 : برنده شده در انتهای بازی
‎🥳 : زنده مونده و برنده شده در انتهای بازی''')

    elif data[1] == "getjoins":
        waiting_message = context.bot.send_message(chat.id, 'در حال بررسی داده ها...')
        group_id = int('-100' + data[2])
        delay_days = int(data[3])
        play_count = int(data[4])
        if play_count == 0:
            users = get_action_users(2, group_id, now(delay_days), now())
            header = '🙎'
            user_text = """{user}"""
        else:
            data = get_users_plays_with_action_id(2, group_id, now(delay_days), now())
            players_with_count = lambda count: {u: data[u] for u in data if data[u]['played'] > count}
            users = players_with_count(play_count)
            header = '🙎|⛹️|🙂|🎊|🥳'
            user_text = """{user} | {play_count} | {alive} | {winner} | {alive_winner}"""

        res = split_users_into_msgs(users, 50, user_text, header)
        waiting_message.delete()
        [context.bot.send_message(user.id, msg, parse_mode='HTML', disable_web_page_preview=True) for msg in res]
        if not res:
            update.message.reply_text('لیست خالیست')
        else:
            update.message.reply_text('''*راهنما*
‎🙎: کاربر
‎⛹️ :بازی انجام شده
‎🙂 :زنده مونده تا‌ انتهای بازی
‎🎊 : برنده شده در انتهای بازی
‎🥳 : زنده مونده و برنده شده در انتهای بازی''')
