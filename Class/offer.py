"""
author: Devel484
"""


class Offer(object):

    def __init__(self, price, qty):
        """
        Sub object for OfferBook
        :param price: price
        :param quantity: quantity
        """
        self.price = float(price)
        self.quote_quantity = float(qty)
        self.base_quantity = float(qty)*float(price)
        self.index = 1

    def get_price(self):
        """
        :return: price
        """
        return self.price

    def get_quantity(self):
        """
        :return: price
        """
        return self.quote_quantity

    def set_quantity(self,qty):
        """
        :return: price
        """
        self.quote_quantity= float(qty)
        self.base_quantity = float(qty)*self.price

    def get_base_quantity(self):
        return self.base_quantity

    def get_token_qty(self, token, pair):
        if token.get_name() == pair.get_quote_token().get_name():
            return self.get_quantity()
        elif token.get_name() == pair.get_base_token().get_name():
            return self.get_base_quantity()
        else:
            return 0

    def set_token_qty(self, token, pair, qty):

        if token.get_name() == pair.get_quote_token().get_name():
            self.quote_quantity = float(qty)
            self.base_quantity = float(qty) * self.price
        if token.get_name() == pair.get_base_token().get_name():
            self.base_quantity = float(qty)
            self.quote_quantity = float(qty) / self.price

    def __str__(self):
        """
        Pair to string
        :return: pair as string
        """
        return "Amount:%16.8f Price:%16.8f Base:%16.8f" % (self.get_quantity(), self.get_price(), self.get_base_quantity())
