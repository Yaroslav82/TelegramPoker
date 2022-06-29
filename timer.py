"""Файл содержит класс таймер,
подробнее про класс таймер можно почитать в описании класа"""

import time
from datetime import datetime, timedelta
import threading
from bot import Bot

class Timer(Bot):
    """Класс наследует все переменные и методы из класса Bot.
    time_now - переменная с текущим временем, обновляется каждую секунду.
    time_update - метод который обновляет переменную time_now каждую секунду
    и находит игры которые нужно запустить.
    start_action - метод который запускает функцию time_update в отдельнлм потоке"""
    def __init__(self):
        # наследуем атрибуты от класса Bot
        super().__init__()
        # time_now - текущее время
        self.time_now = datetime.now()
        # gift_time - время пополнения счёта всем игрокам
        self.gift_time = datetime.now() + timedelta(days=1)
    def time_update(self):
        """метод обновляет текущее время и начинает игры"""
        while True:
            # обновляем время каждую секунду
            self.time_now = datetime.now()
            # ищем игру время которой меньше текущего
            started_game = self.games.find_one({'time': {'$lt' : self.time_now}})
            print(self.time_now)
            # если такая игра найдена, запускаем её
            if started_game:
                # id игры
                game_id = started_game.get('_id')
                print(started_game)
                # начинаем игру с помощью метода start_game из класса Bot
                self.start_game(game_id)
                # удаляем время текущей игры т.к. она уже началась
                self.games.update_one({'_id': game_id}, {"$unset": {'time': {}}})
            # если текущее время больше чем время раздачи подарков
            if self.time_now > self.gift_time:
                # добавляем всем игрокам 1000 в кошелёк
                self.users.update_many({'money': {'$lt': 1000}}, {'$inc': {'money': 1000}})
                # обновляем время пополнения счёта
                self.gift_time = datetime.now() + timedelta(days=1)
            time.sleep(1)

    def start_action(self):
        """метод запускает функцию time_update в отдельнлм потоке,
        чтобы не стопить основной код"""
        thread = threading.Thread(target=self.time_update)
        thread.start()