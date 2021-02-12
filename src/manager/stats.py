from . import bot
import telegram
from telegram.ext import run_async
from telegram.utils.helpers import mention_markdown as mention
import requests

player_stats = 'https://www.tgwerewolf.com/Stats/PlayerStats/?pid={}&json=true'
player_kills = 'https://www.tgwerewolf.com/Stats/PlayerKills/?pid={}&json=true'
player_killed_by = 'https://www.tgwerewolf.com/Stats/PlayerKilledBy/?pid={}&json=true'
player_death = 'https://www.tgwerewolf.com/Stats/PlayerDeaths/?pid={}&json=true'


def get_player_stats_text(player, json=None):
    res = requests.get(player_stats.format(player))
    if not res:
        return res
    res_json = res.json()
    if not res_json:
        return res_json
    if json:
        return res_json
    text = """main stats
Games played: {games_played}
Games won: {won_count}, {won_percent}%
Games lost: {lost_count}, {lost_percent}%
Games survived: {survived_count}, {survived_percent}%"""
    return text.format(
        games_played=res_json['gamesPlayed'],
        won_count=res_json['won']['total'],
        won_percent=res_json['won']['percent'],
        lost_count=res_json['lost']['total'],
        lost_percent=res_json['lost']['percent'],
        survived_count=res_json['lost']['total'],
        survived_percent=res_json['lost']['percent'],
    )


def get_player_kills_text(player):
    res = requests.get(player_kills.format(player))
    if not res:
        return res
    res_json = res.json()
    if not res_json:
        return res_json
    text = """kills"""
    for item in res_json:
        text += '\n{name}: {count}'.format(name=item['name'], count=item['times'])
    return text


def get_player_killed_by_text(player):
    res = requests.get(player_killed_by.format(player))
    if not res:
        return res
    res_json = res.json()
    if not res_json:
        return res_json
    text = """killed by"""
    for item in res_json:
        text += '\n{name}: {count}'.format(name=item['name'], count=item['times'])
    return text


def get_player_death_text(player):
    res = requests.get(player_death.format(player))
    if not res:
        return res
    res_json = res.json()
    if not res_json:
        return res_json
    text = """death"""
    for item in res_json:
        text += '\n{method}: {percent}%'.format(method=item['method'], percent=item['percent'])
    return text


@run_async
def buttons(update, context):
    query = update.callback_query
    chat_id = query.message.chat.id
    user = query.from_user
    data = query.data.replace('stats ', '', 1).split(' ')
    if data[0] == 'stats':
        player = data[1]
        text = get_player_stats_text(player)
        if not text:
            text = 'کاربر سابقه ای ندارد'
        query.answer(text=text, show_alert=True)
        return
    elif data[0] == 'kills':
        player = data[1]
        text = get_player_kills_text(player)
        query.answer(text=text, show_alert=True)
        return

    elif data[0] == 'killedBy':
        player = data[1]
        text = get_player_killed_by_text(player)
        query.answer(text=text, show_alert=True)
        return
    elif data[0] == 'death':
        player = data[1]
        text = get_player_death_text(player)
        query.answer(text=text, show_alert=True)
        return
    elif data[0] == 'ban':
        player = data[1]
        if bot.get_chat_member(chat_id, user.id).status in ['creator', 'administrator']:
            t = bot.get_chat_member(chat_id=chat_id, user_id=int(player))
            name = t.user.full_name
            bot.kick_chat_member(chat_id, player)
            query.edit_message_text(
                '{} Banned {}'.format(mention(user.id, user.first_name), mention(int(player), name)),
                parse_mode='Markdown')
        return
