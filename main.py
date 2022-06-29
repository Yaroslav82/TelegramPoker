"""Файл с основным кодом проекта"""

import telebot
from telebot import types
from pymongo import *
from datetime import datetime, timedelta
from random import sample
import re
from timer import Timer
from bot import Bot
from comb import Combinations

# объект бота
Bot_ob = Bot()
# объект комбинаций
Comb_ob =Combinations()

# объект подключения к серверу бд
client_con = Bot_ob.client_con
# объект подключения к базе данных
ob_db = Bot_ob.ob_db
# объект подключения к колекции с пользователеми
users = Bot_ob.users
# объект подключения к колекции с играми
games = Bot_ob.games
# таймер
tm = Timer()
# объект подключения к боту
bot = Bot_ob.bot


@bot.message_handler(commands=['start', 'create_game', 'statistics'])
def get_command(mes):
    user_id = mes.from_user.id
    chat_id = mes.chat.id
    # если id пользователя нет в коллекции с пользователями, тогда он добавляется в эту коллекцию
    if mes.text == '/start' and not users.count_documents({'_id': user_id}):
        # т.к. username есть не у всех юзеров, вместо него мы записываем first_name
        users.insert_one({'_id': user_id, 'username': mes.from_user.first_name, 'money': 1000, 'games_win': 0})
        # отправляем пользователю информацию о его аккаунте
        Bot_ob.user_info(user_id)

    # если id чата нет в коллекции с играми, тогда он добавляется в эту коллекцию
    elif mes.text == '/create_game' and not games.count_documents({'_id': chat_id}):
        # players - список игроков,
        # bankrupt - список игроков у которых не хватает денег для продолжения, но они делали ставки до этого
        # lap_num - кол-во пройденых кругов(1 круг состоит из добавления одной карты на стол и ставок игроков)
        # bank - в банке хранятся все деньги, в конце они отдаются победителю
        # time - время когда нужно будет начинать игру
        games.insert_one({'_id': chat_id,
                          'players': [], 'bankrupt': [], 'lap_num': 1, 'bank': 0, 'time': datetime.now() + timedelta(seconds=60)})

        # создаём инлайн кнопку с приглашением присоединиться к игре к игре
        join_btn = types.InlineKeyboardMarkup()
        item1 = types.InlineKeyboardButton('Присоединиться к игре', callback_data='join')
        join_btn.add(item1)
        # отправляем сообщение с кнопкой 'присоединиться к игре'
        bot.send_message(chat_id, 'Нажмите на кнопку чтобы вступить в игру, игра начнётся через минуту',
                         reply_markup=join_btn)

    elif mes.text == '/statistics' and user_id == chat_id:
        # отправляем пользователю информацию о его аккаунте
        Bot_ob.user_info(user_id)

    else:
        # удаляем сообщение
        bot.delete_message(chat_id, mes.message_id)


@bot.message_handler(content_types=
                     ['text', 'audio', 'document', 'photo', 'sticker', 'video',
                      'video_note', 'voice', 'location', 'contact', 'pinned_message'])
def get_text(mes):
    # id чата
    chat_id = mes.chat.id
    # id юзера
    user_id = mes.from_user.id

    # проверка, начата ли игра в этом чате
    if games.count_documents({'_id': chat_id}):
        # словарь игры
        game = games.find_one({"_id": chat_id})

        all_in = False

        # проверка, ходит ли сейчас этот игрок
        if user_id == game.get('turn'):
            # минимальная ставка
            min_bet = game.get('min_bet')
            # индекс юзера в спика игроков
            user_ind = Bot_ob.player_index(chat_id, user_id, 'players')
            # кол-во денег игрока
            user_bank = users.find_one({'_id': user_id}).get('money')
            # если у игрока меньше денег чем минимальная ставка
            if user_bank < min_bet:
                # добавляем деньги в банк и добавляем пользователя в список bankrupt т.к. у него 0 на счету
                games.update_one({'_id': chat_id},
                                    {'$inc': {'bank': user_bank, f'players.{user_ind}.bet': user_bank, f'players.{user_ind}.global_bet': user_bank},
                                    "$push": {f'bankrupt': game.get('players')[user_ind]}})
                # удаляем игрока из players
                games.update_one({'_id': chat_id},
                                    {"$pull": {'players': {'_id': user_id}}})

                # вычитаем ставку из денег игрока
                users.update_one({'_id': user_id}, {'$inc': {'money': -user_bank}})
                # присылаем сообщение в котором написано сколько денег поставил игрок и сколько денег сечас в банке
                bot.send_message(chat_id, f'В банк добавилось {user_bank}💵')
                bot.send_message(chat_id, f'У игрока {mes.from_user.first_name} не хватает валюты, поэтому он ставит всё, что есть')

            # проверка, правильно ли написано сообщение
            elif re.fullmatch('[1-9][0-9]+💵', mes.text):
                # ставка игрока
                bet = int(mes.text[:-1])

                #проверяем, чтобы ставка игрока была больше или равна минимальной и чтобы у игрока было достаточно денег
                if bet >= min_bet and user_bank >= bet:
                    Bot_ob.place_bet(chat_id, user_id, bet)
                else:
                    Bot_ob.place_bet(chat_id, user_id, min_bet)

            # если игрок решил пойти All-in, проверяем хватит ли ему денег для минимальной ставки
            elif mes.text == 'All-in':
                all_in = True
                Bot_ob.place_bet(chat_id, user_id, user_bank)
                bot.send_message(chat_id, f'Игрок {mes.from_user.first_name} поставил всё!')

           # если игрок написал Fall или какой-то бред, скидываем его карты
            else:
                Bot_ob.fall(chat_id, user_id)

            # обновляем значения game и min_bet т.к. после прошлых действий они могли измениться
            game = games.find_one({"_id": chat_id})
            min_bet = game.get("min_bet")

            # записываем всех юзеров с их ставами в players_bets
            players_bets = ''
            for el in game.get('players'):
                players_bets += (el['username'] + ' - ' + str(el['bet'])+'💵\n')

            if len(game.get('bankrupt')) > 0:
                players_bets += 'Ставки выбывших:\n'
                for el in game.get('bankrupt'):
                    players_bets += (el['username'] + ' - ' + str(el['bet']) + '💵\n')

            # отправляем сообщение в котором указаны: деньги в банке, мин.ставка и какой игрок сколько поставил
            bot.send_message(chat_id, f'''Денег в банке: {games.find_one({"_id": chat_id}).get("bank")}💵
Минимальная ставка: {games.find_one({"_id": chat_id}).get("min_bet")}💵
\nСтавки игроков:\n{players_bets}''')

            if all_in:
                # добавляем пользователя в список bankrupt т.к. у него 0 на счету
                games.update_one({'_id': chat_id},
                                    {"$push": {f'bankrupt': game.get('players')[user_ind]}})
                # удаляем игрока из players
                games.update_one({'_id': chat_id},
                                    {"$pull": {'players': {'_id': user_id}}})
                user_ind -= 1
                game = games.find_one({"_id": chat_id})

            # если игрок не последний, увеличиваем индекс на 1
            if user_ind < len(game.get('players'))-1:
                user_ind += 1
            # если последний, меняем на ноль
            else:
                user_ind = 0

            # если остался один игрок, заканчиваем игру
            if len(game.get('players')) == 0 or (len(game.get('players')) <= 1 and not all_in):
                # выкладываем все карты на стол
                if game.get('lap_num') < 3:
                    Bot_ob.put_cards(chat_id, 5)
                # заканчиваем игру
                Bot_ob.finish_game(chat_id, game)

            # если ставка следующего игрока меньше минимальной, передаём ему ход
            # мы берём именно следующего т.к. мы изменили user_ind
            elif game.get('players')[user_ind]['bet'] < min_bet:
                Bot_ob.turn(chat_id, user_ind ,min_bet)

            # если все поставили ставки, обнуляем ставки игроков и докладываем одну карту
            else:
                if game.get('lap_num') < 3:
                    # показываем несколько карт(зависит от кол-ва проёденых кругов)
                    Bot_ob.put_cards(chat_id, 3+game.get('lap_num'))
                    # увеличиваем кол-ва проёденых кругов на 1
                    games.update_one({'_id': chat_id},
                                     {'$inc': {'lap_num': 1}})
                    # обнуляем ставки игрокам
                    for i in range(len(game.get('players'))):
                        games.update_one({'_id': chat_id},
                                         {'$set': {f'players.{i}.bet': 0}})
                    # передаём ход следуещему игроку
                    Bot_ob.turn(chat_id, user_ind, 10)

                # если игра прошла 3 круга, заканчиваем её
                else:
                    Bot_ob.finish_game(chat_id, game)

        else:
            # удаляем сообщение в чате, если в этом чате началась игра
            bot.delete_message(chat_id, mes.message_id)


@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    if call.data == 'join':
        chat_id = call.message.chat.id
        user_id = call.from_user.id
        try:
            # проверяем присоединился ли этот пользователь к игре
            if not user_id in [el['_id'] for el in games.find_one(chat_id).get('players')]:
                # добавляем id сообщения с кнопкой, что-бы потом удалить кнопку у этого сообщения
                games.update_one({'_id': chat_id}, {"$set": {'button_id': call.message.message_id}})

                # если пользователь не забыл активировать бота присылаем ему это сообщение
                bot.send_message(user_id, 'Вы присоединились к игре')

                # добавляем пользователя в игру
                games.update_one({'_id': chat_id},
                                 {"$push": {f'players': {'_id': user_id, 'username' : call.from_user.first_name, 'bet' : 0}}})

        except:
            # если же пользователь забыл активировать бота, сообщаем ему об этом
            bot.send_message(chat_id,
                             f'{call.from_user.first_name}, чтобы присоединиться, нужно запустить бота')

tm.start_action()
bot.polling()