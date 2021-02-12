import psycopg2
import telegram
from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from . import get_cur, bot
from cachetools import cached, TTLCache

channel_id = '@lupine_guys'
group_id = -1001461432821


def check_channel_join(func):

    def check(user_id):
        try:
            return bot.get_chat_member(channel_id, user_id).status != 'left'
        except:
            return False
    markup = InlineKeyboardMarkup([[InlineKeyboardButton('Lupine Guys', url=f't.me/{channel_id[1:]}')]])

    def wrapper(update, context):
        if not check(update.effective_user.id):
            txt = 'برای استفاده از این دستور باید در چنل [لوپین گایز](t.me/{}) عضو باشید'.format(channel_id[1:])
            return update.message.reply_text(txt, parse_mode='markdown', disable_web_page_preview=True,
                                             reply_markup=markup)
        return func(update, context)
    return wrapper

class UserStatus:
    def __init__(self, user):
        self.user = user
        if type(user) == int:
            self.user_id = user
        else:
            self.user_id = user.id
        self.channel_status = self.get_channel_status()
        self.group_status = self.get_group_status()
        self.custom_rank = self.get_custom_rank()
        self.status = self.get_status()

    def get_channel_status(self):
        try:
            response = bot.get_chat_member(channel_id, self.user_id)
            if response['status'] == 'member':
                return 1
            elif response['status'] == 'administrator':
                return 2
            elif response['status'] == 'creator':
                return 3
            else:
                return 0
        except:
            return 0

    def get_group_status(self):
        try:
            response = bot.get_chat_member(group_id, self.user_id)
            if response['status'] == 'member':
                return 1
            elif response['status'] == 'administrator':
                return 2
            elif response['status'] == 'creator':
                return 3
            else:
                return 0
        except:
            return 0

    def get_custom_rank(self):
        query = """
        select rank
        from v1.users_custom_rank
        WHERE user_id = %s
        """
        cur, conn = get_cur()
        try:
            cur.execute(query, (self.user_id,))
            res = cur.fetchone()
            cur.close()
            if not res:
                return ''
            return res[0]

        except Exception as e:
            print(e)
            return ''

    def get_status(self):
        if self.custom_rank:
            return self.custom_rank
        elif self.channel_status == 1 and self.group_status == 1:
            return 'کاربر ویژه🔥'
        elif self.channel_status == 2:
            return 'مدیر مجموعه ☢️'
        elif self.group_status == 2:
            return 'هدایتگر مجموعه 💠'
        elif self.channel_status == 3:
            return 'مالک مجموعه 🐾'
        else:
            return 'کاربر عادی'


