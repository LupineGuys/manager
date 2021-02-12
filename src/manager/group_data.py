import datetime
from psycopg2.extras import RealDictCursor
from pytz import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import run_async
from . import bot_admins, get_cur, bot
from .RANK_STATEMENT import check_channel_join


def now():
    iran = timezone('Asia/Tehran')
    sa_time = datetime.datetime.now(iran)
    return sa_time.strftime('%Y-%m-%d')


query = """
delete
FROM v2.all_games T1
USING   v2.all_games T2
WHERE T1.ctid < T2.ctid       
      AND T1.message_id = T2.message_id       
      AND T1.group_id = T2.group_id;
      
with data as (with time_data(date, group_id, players, joinTime, gameTime, canceled) as (select
                                                                                          created_at :: date,
                                                                                          group_id,
                                                                                          player_count,
                                                                                          started_at :: timestamp -
                                                                                          created_at :: timestamp,
                                                                                          finished_at :: timestamp -
                                                                                          started_at :: timestamp,
                                                                                          canceled
                                                                                        from v2.all_games
                                                                                        where group_id = %s
                                                                                              and created_at :: date =
                                                                                                  '{now}'::date  {day})
SELECT
  date,
  group_id,
  count(*)  
    filter (where canceled is false)           games_passed,
  count(*)
    filter (where canceled is True)            games_canceled,
  avg(players) :: int                          avg_players,
  sum(players)                                 sum_players,
  avg(joinTime)                                avg_jointime,
  avg(gameTime)                                avg_gametime,
  sum(joinTime)                                sum_jointime,
  sum(gameTime)                                sum_gametime,
  '23:59:59' - (sum(joinTime) + sum(gameTime)) no_game_duration
from time_data
group by group_id,date)
select *
from data
         join (
    select group_id,
           count(*),
           count(distinct user_id),
           count(distinct user_id) filter ( where user_id not in (select distinct user_id
                                                                  from v2.users_activity_log_v2
                                                                  where group_id = %s
                                                                    and created_at::date < '{now}'::date {day}) )
    from v2.users_activity_log_v2
    where group_id = %s
      and created_at::date = '{now}'::date  {day}
    group by group_id) d(chat_id, play_count, players_count, new_players_count) on group_id = chat_id
"""
text_fa = """✦آمار گروه {group} در {date} v2

✦آمار بازی‌ها 
✓ تعداد بازی‌ها انجام شده :  {game_played} بازی
✓ تعداد بازی‌های لغو شده :  {game_canceled} بازی

✦آمار پلیرها
✓ میانگین تعداد پلیر در هر بازی :  {avg_players} بازیکن
✓ مجموع تعداد‌ پلیرهایی که بازی کردند : {sum_players} بازیکن
✓ تعداد‌ پلیرهایی که بازی کردند : {players_count} بازیکن
✓ تعداد پلیر‌های جدید : {new_players_count} بازیکن

✦آمارهای زمانی
✓ میانگین زمان هر بازی : {avg_gametime}
✓ میانگین جوین تایم : {avg_jointime}
✓ مجموع ساعاتی که بازی در جریان بوده : {sum_gametime}
✓ مجموع جوین‌ تایم‌ها : {sum_jointime}
✓ مجموع ساعاتی که بازی‌ای در جریان نبوده : {nogame_time}

"""
text = """{group} {date} v1

Games stat
game played : {game_played} games
game canceled : {game_canceled} games

Players stat
avg players : {avg_players} players
sum players : {sum_players} players
new users : {new_players_count} players

Time stat
avg game time : {avg_gametime} 
avg join time : {avg_jointime}
sum game time : {sum_gametime}
sum join time : {sum_jointime}
sum idle time : {nogame_time}


avg = میانگین
sum مجموع
"""


def get_all_gp():
    conn, cur = get_cur()
    query = f"""
select distinct g.group_id , title
from v1.all_group_helper as g

join (select distinct group_id
from v2.users_activity_log_v2)d on g.group_id=d.group_id
        """
    cur.execute(query)
    res = cur.fetchall()
    cur.close()
    return {i[0]: i[1] for i in res}


def get_group_name(group: int):
    conn, _ = get_cur()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    query = f"""
    select distinct group_id, title
    from v1.all_group_helper 
where group_id = {group}
            """
    cur.execute(query)
    res = cur.fetchall()
    cur.close()
    return res


def get_group_data(group_id, day: int = -1):
    conn, _ = get_cur()
    cur = conn.cursor(cursor_factory=RealDictCursor)
    try:
        cur.execute(query.format(day=day, now=now()), (group_id, group_id, group_id))
        res = cur.fetchone()
        cur.close()
        return dict(
            date=res['date'],
            group_id=res['group_id'],
            game_played=res['games_passed'],
            game_canceled=res['games_canceled'],
            avg_players=res['avg_players'],
            sum_players=res['sum_players'],
            avg_jointime=datetime.timedelta(seconds=res['avg_jointime'].seconds),
            avg_gametime=datetime.timedelta(seconds=res['avg_gametime'].seconds),
            sum_jointime=datetime.timedelta(seconds=res['sum_jointime'].seconds),
            sum_gametime=datetime.timedelta(seconds=res['sum_gametime'].seconds),
            nogame_time=datetime.timedelta(seconds=res['no_game_duration'].seconds),
            players_count=res['players_count'],
            new_players_count=res['new_players_count']
        )

    except:
        cur.close()
        return False


spy_mode_users = [721788770, 397934928, 105443113, 1005963668, 103752050, 119090316]


@check_channel_join
@run_async
def get_stats(update, context):
    user = update.message.from_user
    chat = update.message.chat
    res = bot.get_chat_member(chat.id, user.id)
    if chat.id == user.id:
        update.message.reply_text('این قابلیت به @gorg_yatim_bot انتقال یافت')
    if res.status not in ['creator', 'administrator'] and user.id not in bot_admins():
        return
    res = get_group_data(chat.id)
    if not res:
        update.message.reply_text('اطلاعات گروه موجود نیست!')
        return
    msg = text_fa.format(
        date=res['date'],
        group=chat.title,
        game_played=res['game_played'],
        game_canceled=res['game_canceled'],
        avg_players=res['avg_players'],
        sum_players=res['sum_players'],
        avg_jointime=res['avg_jointime'],
        avg_gametime=res['avg_gametime'],
        sum_jointime=res['sum_jointime'],
        sum_gametime=res['sum_gametime'],
        nogame_time=res['nogame_time'],
        players_count=res['players_count'],
        new_players_count=res['new_players_count']
    )
    try:
        buttons = [[InlineKeyboardButton('روز قبل',
                                         callback_data='group_data get_data {group_id} -2'.format(group_id=chat.id))]

                   ]
        bot.send_message(user.id, msg, reply_markup=InlineKeyboardMarkup(buttons))
        update.message.reply_text('پیوی چک')
    except:
        update.message.reply_text('مشکلی پیش اومده چک کن ببین با من پیوی داری یا بلاکم نکردی؟')


@run_async
def buttons(update, context):
    query = update.callback_query
    chat = query.message.chat
    user = query.from_user
    data = query.data.replace('group_data ', '', 1).split(' ')
    if data[0] == 'get_data':
        group_id = data[1]
        days = int(data[2])
        if days >= 0:
            query.answer(text=' از امروز و روزهای اینده اطلاعاتی در دسترس نمیباشد', show_alert=True)
            return
        res = get_group_data(group_id, days)
        if not res:
            query.answer(text='مشکل در بارگزاری اطلاعات', show_alert=True)
            return
        try:
            chat = bot.get_chat(group_id)
        except:
            chat = None
        if not chat:
            query.answer('به نظر میرسه ربات داخل گروه نیست', show_alert=True)
        msg = text_fa.format(
            date=res['date'],
            group=chat.title,
            game_played=res['game_played'],
            game_canceled=res['game_canceled'],
            avg_players=res['avg_players'],
            sum_players=res['sum_players'],
            avg_jointime=res['avg_jointime'],
            avg_gametime=res['avg_gametime'],
            sum_jointime=res['sum_jointime'],
            sum_gametime=res['sum_gametime'],
            nogame_time=res['nogame_time'],
            players_count=res['players_count'],
            new_players_count=res['new_players_count']
        )
        if days < -1:
            buttons = [[InlineKeyboardButton('روز قبل',
                                             callback_data='group_data get_data {group_id} {days}'.format(
                                                 group_id=chat.id, days=days - 1)),
                        InlineKeyboardButton('روز بعد',
                                             callback_data='group_data get_data {group_id} {days}'.format(
                                                 group_id=chat.id, days=days + 1))]]
        else:
            buttons = [[InlineKeyboardButton('روز قبل',
                                             callback_data='group_data get_data {group_id} -2'.format(
                                                 group_id=chat.id))]]
        query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(buttons))

    if data[0] == 'page':
        query.answer(text='این قابلیت به ربات گرگ یتیم منتقل شد لطفا از اون استفاده کنید', show_alert=True)
    if data[0] == 'spy_mode':
        query.answer(text='این قابلیت به ربات گرگ یتیم منتقل شد لطفا از اون استفاده کنید', show_alert=True)
