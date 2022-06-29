"""Файл с классом Combinations"""

class Combinations():
    """Класс содержит методы для определения комбинации и определения веса данной комбинации,
    для каждой комбинации создана отдельная функция"""

    def _name_replace(self, str_1: str, a_val: str) -> str:
        """Меняет в строке J на 11, Q  на 12, K на 13

        a_val - значения туза"""
        return str_1.replace('J', '11').replace('Q', '12').replace('K', '13').replace('A', a_val).split()

    def _num_repalce(self, str_1: str, a_val: str) -> str:
        """Меняет в строке 11 на J, 12 на Q, 13 на K

        a_val - значения туза"""
        return str_1.replace('11', 'J').replace('12', 'Q').replace('13', 'K').replace(a_val, 'A')

    def card_weight(self, card: str) -> int:
        """Определяет вес карты,

        card - карта, вес которой нужно узнать"""
        return int(self._name_replace(card, '14')[0])

    def high_card(self, cards_val: list) -> list:
        """Находит старшую карту в колоде

        cards_val - список номиналов карт"""
        # a - дип копия списка cards_val
        a = cards_val[:]
        # меняем карты в виде букв, на числа
        a = self._name_replace(' '.join(a), '14')
        max_card = max(a, key=int)
        return [int(max_card) / 100,
                self._num_repalce(max_card, '14')]

    def cards_amount(self, cards_val: list, am: int) -> list:
        """Находит и возвращает карту и её вес, если ее количество в списке больше am

        cards_val - список номиналов карт

        am(amount) - количество одинаковых карт"""
        max_card = max(cards_val, key=cards_val.count)
        if cards_val.count(max_card) > am:
            return [0 + self.card_weight(max_card) / 100, max_card]

    def cards_order(self, cards_val: list, a_val=14) -> list:
        """Находит есть ли в списке номиналы карты идущие подряд

        cards_val - список номиналов карт

        a_val - значения туза (по умолчанию 14)"""
        # a - дип копия cards_val
        a = cards_val[:]
        # меняем карты в виде букв, на числа
        a = self._name_replace(' '.join(a), a_val)
        if len(set(a)) > 4:
            val = sorted(set(a), key=int, reverse=True)
            res = [val[0]]
            for el in val[1:]:
                if len(res) > 4:
                    return res
                elif len(res) == 0 or int(el) == int(res[-1]) - 1:
                    res.append(el)
                else:
                    res.clear()
                    res.append(el)
            if len(res) > 4:
                return res

    def street(self, cards_val: list) -> list:
        """Определяет является ли комбинация карт стритом,
        если да возвращает до какой карты стрит и вес комбинации

        cards_val - список номиналов карт"""
        # перечесляем значения туза
        for el in ['14', '1']:
            ord = self.cards_order(cards_val, a_val=el)
            # если метод cards_order находит 5 подряд идущих карт, возвращаем вес комбинации и до какой карты стрит
            if ord:
                max_card = max(ord, key=int)
                ord = self._num_repalce(' '.join(ord), el).split()
                return [4 + int(self.card_weight(max_card)) / 100, f'Стрит до {ord[0]}']

    def flush(self, cards: list) -> list:
        """Определяет есть ли флеш(5 одинаковых мастей) в списке карт

        cards - список карт"""
        cards = [el for el in cards if suit[0] in el]
        numb = [el[:-1] for el in cards]
        res = [*self.high_card(numb), f'Флэш по {suit}']
        return [res[0] + 5] + res[1:]

    def two_comb(self, cards_val: list, am: int) -> list:
        """Находит есть ли в списке 2 пары номиналов каких либо карт,
        или есть ли фул хаус в колоде (зависит от параметра am)

        am - кол-во карт которые должны быть одновременно с парой других карт

        cards_val - список номиналов карт"""
        # a - дип копия списка cards_val
        a = cards_val[:]
        if self.cards_amount(a, am):
            res = [self.cards_amount(a, 1)[0]]
            res.append(self.cards_amount(a, am)[1])

            for i in range(am+1):
                a.remove(res[1])

            card_am = self.cards_amount(a, 1)
            if card_am:
                res.append(card_am[1])

                if am == 1:
                    if res[0] < card_am[0]:
                        res.pop(0)
                        res.insert(0, card_am[0])
                    res.append(f'Две пары {res[1]} и {res[2]}')
                    return [res[0]+2, res[-1]]

                elif am == 2:
                    res.append(f'Фулл хаус из {res[1]} и {res[2]}')
                    return [res[0]+6, res[-1]]

    def match_comb(self, deck:list, cards:list):
        """Находим какая комбинация образуется в картах на столе и картах игрока

        deck - карты на столе

        cards - карты игрока"""
        # cards_list  карты игрока + карты на столе
        cards_list = deck + cards
        # numb  номиналы карт
        numb = [el[:-1] for el in cards_list]
        # список карт с одинаковыми мастями
        mast_list = []
        # suit  все масти
        suit = '♥♣♠♦'

        for el in suit:
            # если кол-во определённой масти меньше 5 удаляем её из suit
            if ''.join(cards_list).count(el) < 5:
                suit = suit.replace(el, '')
            # если больше добавляем в mast_list карты с данной мастью
            else:
                mast_list = [el for el in cards_list if suit[0] in el]

        # если получается стрит из карт в mast_list
        if self.street([el[:-1] for el in mast_list]):
            # записываем его в comb
            comb = self.street([el[:-1] for el in mast_list])

            # если стрит до туза, значит это флеш рояль
            if comb[1] == 'Стрит до A':
                return [5 + comb[0], 2, f'Флеш рояль по {suit[0]}']

            # если нет, тогда стрит флеш
            else:
                return [4 + comb[0], 2, f'Стрит флеш до {comb[1][9:]} по {suit[0]}']

        # если в номиналах карт есть 4 одинкаовых карты, значит это каре
        elif self.cards_amount(numb, 3):
            # возвращаем вес комбинации и строку, где написано из какой карты каре
            return [self.cards_amount(numb, 3)[0] + 7, f'Каре из {self.cards_amount(numb, 3)[1]}']

        # если метод full_house что-то возвращает, значит он есть
        elif self.two_comb(numb, 2):
            return self.two_comb(numb, 2)

        # есть ли в suit осталось одна масть и метод flush не возвращает None
        elif len(suit) == 1 and self.flush(cards_list):
            # возвращаем результат метода flush
            return self.flush(cards_list)

        # если из карт обрзуется стрит
        elif self.street(numb):
            # возвращаем метод street
            return self.street(numb)

        # если в номиналах карт есть 3 одинкаовых карты, значит это сет
        elif self.cards_amount(numb, 2):
            # возвращаем вес комбинации и строку, где написано из какой карты сет
            return [self.cards_amount(numb, 2)[0] + 3, f'Сет из {self.cards_amount(numb, 2)[1]}']

        # если в картах есть 2 пары
        elif self.two_comb(numb, 1):
            # возвращаем метод two_pair
            return self.two_comb(numb, 1)

        # если в номиналах карт есть 2 одинкаовых карты, значит это пара
        elif self.cards_amount(numb, 1):
            # возвращаем вес комбинации и строку, где написано из какой карты пара
            return [self.cards_amount(numb, 1)[0] + 1, f'Пара {self.cards_amount(numb, 1)[1]}']

        # если у вас ничего нет из выше перечисленого
        else:
            # возвращаем старшую карту и её вес
            return [self.high_card(numb)[0], f'Старшая карта {self.high_card(numb)[1]}']