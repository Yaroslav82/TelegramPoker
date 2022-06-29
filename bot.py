"""Файл содержит класс Бота, внутри данного класса основные методы и атрибуты этого проекта"""

import telebot
from telebot import types
from pymongo import *
from random import sample
from comb import Combinations

class Bot:
    """С помощью данного класса можно взаимодействовать с ботом и базой данных,
    так же можно начинать игры и взаимодействовать с игроками из этих игр"""
    def __init__(self):
        # объект подключения к серверу бд
        self.client_con = MongoClient('localhost', 27017)
        # объект подключения к базе данных
        self.ob_db = self.client_con['PokerGames']
        # объект подключения к колекции с пользователеми
        self.users = self.ob_db['users']
        # объект подключения к колекции с играми
        self.games = self.ob_db['games']
        # объект бота
        self.bot = telebot.TeleBot("5425785682:AAEJDG3Aq3IQxZsJGdd6bCKRkv85YgaYGkA")

    def player_index(self, chat_id:int, user_id:int, loc:str) -> int:
        """метод возвращает индекс юзера из списка словарей игроков определённой игры

        chat_id - id игры

        user_id - id юзера, индекс которого нужно получить"""
        return [el['_id'] for el in self.games.find_one({'_id': chat_id}).get(loc)].index(user_id)

    def turn(self, chat_id:int, i:int, min_bet:int) -> None:
        """Метод обновляет згачение turn и min_bet в бд,
        так же присылает клавиатуру всем игрокам"""
        user = self.games.find_one({'_id': chat_id}).get('players')[i]
        min_bet -= user['bet']
        self.games.update_one({'_id': chat_id},
                              {"$set": {'turn': user['_id'], 'min_bet' : min_bet}})

        # Объект клавиатуры
        keyboard_markup = types.ReplyKeyboardMarkup()

        # Создание объектов кнопок
        button_10 = types.KeyboardButton(f"{min_bet}💵")
        button_50 = types.KeyboardButton(f"{min_bet*2}💵")
        button_100 = types.KeyboardButton("All-in")
        button_250 = types.KeyboardButton("Fall")

        # Добовление кнопки в клавиатуру
        keyboard_markup.add(button_10, button_50, button_100, button_250, row_width=4)

        self.bot.send_message(chat_id, f'{user["username"]}, делайте ставку', reply_markup=keyboard_markup)

    def give_cards(self, chat_id:int, deck:list) -> None:
        """Раздаёт по 2 карты всем игрокам, оставшиеся добавляет в колоду.

            chat_id - id чата

            deck - список со всеми картами"""
        # список игроков
        players = self.games.find_one({'_id': chat_id}).get('players')

        for i in range(len(players)):
            # добавляем в бд карты игрока
            self.games.update_one({'_id': chat_id},
                             {"$set": {f'players.{i}.cards': deck[:2]}})
            # присылаем игроку сообщение с его картами
            self.bot.send_message(players[i]['_id'], f'Ваши карты: {deck[0]} {deck[1]}')
            deck = deck[2:]

        # добавляем в бд оставшиеся карты в колоде
        self.games.update_one({'_id': chat_id}, {"$set": {'deck': deck[:5]}})

    def put_cards(self, chat_id:int, cards_amount:int) -> None:
        """Отправляет сообщение в котором показано определённое кол-во карт

        chat_id - id чата

        cards_amount - кол-во карт необходимых для показа"""
        self.bot.send_message(chat_id, f"""*Карты на столе:*

{' '.join(self.games.find_one({'_id': chat_id}).get('deck')[:cards_amount])}""", parse_mode="Markdown")

    def start_game(self, chat_id:int) -> None:
        """Удаляет кнопку 'присоединиться к игре',
        чтобы войти во время игры было невозможно,
        Потом раздаёт по 2 карты каждому и первые 3 карты выкладывает на стол.
        Даёт права хода первому игроку и задаёт минимальную ставку(по умолчанию 10)

        chat_id - id чата"""
        self.bot.edit_message_text(chat_id=chat_id, message_id=self.games.find_one({'_id': chat_id}).get('button_id'),
                              text=f'Игра началась!', reply_markup=None)
        self.games.update_one({'_id': chat_id}, {"$unset": {'button_id': {}}})
        # если к игре присоединилось больше одного человека
        if len(self.games.find_one({'_id': chat_id}).get('players')) > 1:
            # sample перемешивает и сразу возвращает список, 52 - это кол-во карт в колоде
            self.give_cards(chat_id, sample(open('deck.txt', encoding='UTF-8').read().split(), 52))
            # выкладываем на стол первые 3 карты
            self.put_cards(chat_id, 3)
            # передаём ход первому игроку
            self.turn(chat_id, 0, 10)
        else:
            self.games.delete_one({'_id': chat_id})
            self.bot.send_message(chat_id, 'Слишком мало людей для начала игры😢')

    def place_bet(self, chat_id:int, user_id:int, bet:int) -> None:
        """метод обновляет ставку игрока и минимальную ставку в игре"""
        # индекс игрока
        user_ind = self.player_index(chat_id, user_id, 'players')
        # минимальная ставка
        min_bet = bet + self.games.find_one({'_id' : chat_id}).get('players')[user_ind]['bet']
        # обновляем ставку игрока в нынешнем круге, обновляем ставку игрока за всё время,
        # обновляем минимальную ставку, добавляем ставку в банк
        self.games.update_one({'_id': chat_id},
                         {'$set': {'min_bet': min_bet},
                          '$inc': {'bank': bet, f'players.{user_ind}.bet': bet, f'players.{user_ind}.global_bet': bet}})

        # вычитаем ставку из денег игрока
        self.users.update_one({'_id': user_id}, {'$inc': {'money': -bet}})
        self.bot.send_message(chat_id, f'В банк добавилось {bet}💵')

    def fall(self, chat_id:int, user_id:int) -> None:
        """Удаляет игрока из бд игры, и в чат игры пишет сообщение, что он вышел

        chat_id - id игры

        user_id - id юзера, которого нужно удалить из игры"""
        # удаляем игрока из списка игроков в бд игры
        self.games.update_one({'_id': chat_id},
                              {"$pull": {'players' : {'_id' : user_id}}})
        self.bot.send_message(chat_id, f'Игрок {self.users.find_one(user_id).get("username")} скинул карты' )

    def max_comb_weight(self, chat_id:int, loc='players') -> dict | None:
        """Возвращает словарь с игроком(или с несколькими)
         у которого самый большой вес комбинации

        chat_id - id игры

        loc(location) - расположение списка игроков
        (по умолчанию players так же может быть bankrupt)"""
        winners = {}

        # перебераем все элементы из списка который указан в loc
        for el in self.games.find_one({'_id': chat_id}).get(loc):
            # округляем вес комбинации до сотых, чтобы не было подобного: 14.10000000000009
            comb_w = round(el['comb_weight'], 2)
            # если такой вес комбинации у кого-то уже есть, добавляем его id в список к этому игроку
            if comb_w in winners:
                winners.get(comb_w).append(el['_id'])
            # если нет, добавляем вес комбинации и id юзера этой комбинации
            else:
                winners.update({round(el['comb_weight'], 2): [el['_id']]})
        if winners:
            # возвращаем словарь вида {самый большой вес комбинации: id игрока с этой комбинацей}
            return {max(winners): winners[max(winners)]}

    def comb_update(self, game:dict, chat_id:int, loc='players') -> str:
        """Узнаёт и добавляет каждому игроку в списке его название комбинации и её вес

        game - словарь игры

        chat_id - id игры

        loc(location) - расположение списка игроков
        (по умолчанию players так же может быть bankrupt)"""

        # Обьект комбинаций
        Comb_ob = Combinations()
        # Результаты игроков в виде строки (чтобы потом отправить сообщение в группу игры)
        players_res = ''
        for el in game.get(loc):
            # находим комбинацию и её вес
            comb_list = Comb_ob.match_comb(game.get('deck'), el['cards'])
            # добавляем в players_res имя игрока и название его комбинации
            players_res += f'\n{el["username"]} {" ".join(el["cards"])} ({comb_list[1]})'
            # добавляем в бд игрока вес его комбинации
            self.games.update_one({'_id': chat_id},
                             {"$set": {
                                 f'{loc}.{self.player_index(chat_id, el["_id"], loc)}.comb_weight': comb_list[0]}})
        # возвращаем строку с именами игроков и их ставками
        return players_res

    def give_money(self, chat_id:int, winners_b:dict, extra_players=0) -> str:
        """Вычесляет и добавляет деньги игрокам в списке bankrupt(если они в этом списке,
         значит у них закончились деньги и для них нужна специальная формула для вычесления их куша

        chat_id - id игры

        winners_b - словарь с игроком/игроками из списка bankrupt с самой большой комбинацией

        loc(location) - расположение списка игроков
        (по умолчанию players так же может быть bankrupt))"""
        # Результаты ставок игроков в виде строки
        players_res = ''
        # Количество игроков в игре, то есть кол-во игроков в списке bankrupt и списке players
        game_len = len(self.games.find_one({'_id': chat_id}).get('players')) + len(
            self.games.find_one({'_id': chat_id}).get('bankrupt'))

        # перебераем id игроков с самыми большим весом комбинации
        for el in list(winners_b.values())[0]:
            # словарь с информацией об игроке
            user = self.games.find_one({'_id': chat_id}).get('bankrupt')[
                self.player_index(chat_id, el, 'bankrupt')]
            # деньги которые получит игрок
            bank = (user.get('global_bet') * game_len) // (
                        len(list(winners_b.values())[0]) + extra_players)
            # добавляем деньги игроку
            self.users.update_one({'_id': el}, {'$inc': {'money': bank, 'games_win': 1}})
            # забираем деньги из банка
            self.games.update_one({'_id': chat_id}, {'$inc': {'bank': -bank}})
            # если игрок получил сумму денег больше 0
            if bank > 0:
                # добавляем его в строку с побелителями
                players_res += f'\n{user.get("username")}: +{bank}💵'
        # возвращаем строку с игроками которые выйграли деньги
        return players_res

    def finish_game(self, chat_id:int, game:dict) -> None:
        """Раздаёт деньги победителям и показывает карты игроков и их комбинации"""

        # собираем строку с картами всех игроков
        players_res = 'Карты игроков:\n'
        players_res += self.comb_update(game, chat_id)
        # так же добавляем в строку карты игроков из bankrupt, если в этом списке есть игроки
        if game.get('bankrupt'):
            players_res += self.comb_update(game, chat_id, loc='bankrupt')

        # отправляем сообщение с картами игроков
        self.bot.send_message(chat_id, players_res)

        # победители из списка players
        winners_p = self.max_comb_weight(chat_id)
        # победители из списка bankrupt
        winners_b = self.max_comb_weight(chat_id, loc='bankrupt')
        # собираем строку с победителями
        players_res = 'Победители:\n'

        # если все игроки в winners_b
        if winners_b and not winners_p:
            # раздаём деньги победителям и добавляем в players_res имена и кол-во выйграных денег победителей
            players_res += self.give_money(chat_id, winners_b)
        # если победители есть в winners_b и в winners_p
        elif winners_b:
            # если вес комбинации игрока из winners_b больше чем вес комбинации winners_p
            if list(winners_b.keys())[0] > list(winners_p.keys())[0]:
                # даём ему деньги которые он выйграл
                players_res += self.give_money(chat_id, winners_b)

            # если вес комбинации равен у обоих сторон
            elif list(winners_b.keys())[0] == list(winners_p.keys())[0]:
                # даём ему деньги которые он выйграл делённые на кол-во победителей в winners_p
                players_res += self.give_money(chat_id, winners_b,
                                                 extra_players=len(list(winners_p.values())[0]))
        # если в winners_p есть игроки
        if winners_p:
            # делим деньги в банке между игроками из winners_p
            bank = self.games.find_one({"_id": chat_id}).get("bank") // len(list(winners_p.values())[0])

            # раздаём деньги из банка игрокам
            for el in list(winners_p.values())[0]:
                user = self.games.find_one({'_id': chat_id}).get('players')[
                    self.player_index(chat_id, el, 'players')]
                self.users.update_one({'_id': el}, {'$inc': {'money': bank, 'games_win': 1}})
                # добавляем в строку имя победителя и деньги которые он выйграл
                players_res += f'\n{user.get("username")}: +{bank}💵'

        # отправляем сообщение с победителями
        self.bot.send_message(chat_id, players_res)
        self.bot.send_message(chat_id, 'Конец игры', reply_markup=types.ReplyKeyboardRemove())
        # self.games.delete_one({'_id': chat_id})

    def user_info(self, user_id:int) -> None:
        """Отправляет сообщении с информацией об аккаунте пользователя
        (кол-во денег и кол-во выйгранных игр)

        user_id - id игрока"""
        info = self.users.find_one({'_id': user_id})
        self.bot.send_message(user_id, f'''*Статистика игрока*
        
Деньги: {info.get("money")}💵 
Выигранные игры: {info.get("games_win")}''', parse_mode="Markdown")

