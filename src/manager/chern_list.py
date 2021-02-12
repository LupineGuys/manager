import datetime

import psycopg2
import telegram
from pytz import timezone
from telegram.utils.helpers import escape, mention_html
from . import get_cur, bot
iran = timezone('Asia/Tehran')


def now():
    sa_time = datetime.datetime.now(iran)
    return sa_time.strftime('%Y-%m-%d %H:%M:%S')


class User:
    def __init__(self, user_id):
        self.user_id = user_id
        self.name = None
        self.play_count = 0
        self.status = None

    def set_name(self, item):
        if len(item) == 8:
            self.name = item
        elif len(item) <= 6:
            mis = 8 - len(item)
            self.name = item + '.'.join([''] * mis) + '..'
        elif len(item) >= 6:
            s = item[:5]
            self.name = s + '..'


def get_users_from_database(group_id):
    query = f"""
    WITH players as (
select user_id ,count(user_id)as p_c
from v2.users_activity_log_v2
where group_id=%s and created_at::date between '{now()}'::date -interval'21 days' and '{now()}'::date - interval'7 days'
group by user_id
),
  last_w_p as (
    select user_id ,count(user_id)as p_c_t
from v2.users_activity_log_v2
where group_id=%s and created_at::date between '{now()}'::date -interval'7 days' and '{now()}'::date
group by user_id
  )
select *
from players
  full join last_w_p ls on ls.user_id=players.user_id
where p_c>= 3 and ls.user_id is null
order by p_c desc
    
    """
    conn, cur = get_cur()
    cur.execute(query, (group_id, group_id))
    res = cur.fetchall()
    if res:
        return {i[0]: i[1] for i in res}
    return res


def get_users_list(group_id):
    f_list = get_users_from_database(group_id)
    users = []
    if not f_list:
        return users
    for item in f_list:
        user = User(item)
        user.play_count = f_list[item]
        users.append(user)
    return users


def make_users_list(group_id):
    old_users = get_users_list(group_id)
    users = []
    if not old_users:
        return users
    for user in old_users:
        try:
            res = bot.get_chat_member(group_id, user.user_id)
            if res:
                user.status = res.status
                # user.set_name(res.user.first_name)
                user.name = res.user.name
                users.append(user)
                continue
        except telegram.error.Unauthorized as un:
            res = bot.get_chat_member(-1001461432821, user.user_id)
            if res:
                user.status = res.status
                # user.set_name(res.user.first_name)
                user.name = res.user.name
                users.append(user)
                continue
        except:
            pass
        user.status = 'Unknown'
        # user.set_name(str(user.user_id))
        user.name = str(user.user_id)
        users.append(user)
    return users


def make_list(group_id):
    try:
        res = bot.get_chat(group_id)
        title = res.title
    except:
        res = True
        title = 'گروه خارج از مدار'
    if not res:
        return None
    users = make_users_list(group_id)
    if not users:
        return None

    header = 'لیست کاربران چرن تا این لحظه در گروه {} \n\n\n'.format(title)
    header += ' <code>name</code> | <code>play count in last 2 weeks</code> | <code>status</code> \n\n'
    users_msg_list = []
    users_msg = ''
    for i, user in enumerate(users, start=1):
        if not i % 50:
            users_msg_list.append(users_msg)
            users_msg = ''
        users_msg += "{name} | {play_count} | {status}\n".format(
            name=mention_html(user.user_id, user.name if user.name else user.user_id),
            play_count=user.play_count,
            status=user.status
        )
    if users_msg:
        users_msg_list.append(users_msg)
    return {'header': header, 'msg_list': users_msg_list}


