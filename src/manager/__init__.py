import psycopg2
import psycopg2.extensions
from telegram import Bot
from dotenv import load_dotenv
from os import getenv
from cachetools import cached, TTLCache

load_dotenv()

GIVEMESSAGE = range(1)
manager_token = getenv('DISPATCHER_TOKEN')
bot = Bot(manager_token)

dev_group = int(getenv('DEV_GROUP'))


def get_cur():
    database_kw = eval(getenv('DATABASE'))

    if not hasattr(get_cur, 'conn') or get_cur.conn.closed != 0:
        get_cur.conn = psycopg2.connect(**database_kw)
        get_cur.conn.autocommit = True
    if get_cur.conn.status == psycopg2.extensions.STATUS_IN_TRANSACTION:
        get_cur.conn.rollback()
    cur = get_cur.conn.cursor()
    conn = get_cur.conn
    return conn, cur


@cached(cache=TTLCache(maxsize=1024, ttl=120))
def get_from_permission(permission_id):
    conn, cur = get_cur()
    query = """
    select array_agg(user_id) 
    from v2.permissions
    where permission_id= %(permission_id)s and deleted_at is null
    """
    cur.execute(query, {'permission_id': permission_id})
    res = cur.fetchone()
    if not res:
        return []
    return res[0]


rank_emoji_admins = lambda: get_from_permission(6)
bot_admins = lambda: get_from_permission(3)

from .manager_v1 import manager_app
