"""
author: beal2912
"""
import API.api_request as request
import API.log as log
from Class.offer import Offer
import time


class Pair(object):

    WAY_BUY = 0
    WAY_SELL = 1

    def __init__(self, exchange, quote, base):
        """
        Trading Pair
        :param exchange: reference to the exchange(at the moment only switcheo)
        :param quote: quote token
        :param base: base token
        """
        self.exchange = exchange
        self.quote = quote
        self.base = base

        self.last_price= 0

        self.asks = []
        self.bids = []

        self.updating = False
        self.block = False
        self.last_update = time.time()

    # ------------------------------------------------------------------------------------------------------------------
    def is_blocked(self):
        """
        If pair is used for actual arbitrage, it is blocked for other trades
        :return: true if blocked
        """
        return self.block

    def set_blocked(self, b):
        """
        Set blocked used for trading, release after usage,
        :param b: state
        :return: None
        """
        self.block = b
    # ------------------------------------------------------------------------------------------------------------------
    def is_updating(self):
        """
        If pair is updating offer book it returns true.
        :return: true if updating
        """
        return self.updating

    def set_updating(self, b):
        """
        Set pair is updating while loading offers.
        :param b: state
        :return: None
        """
        self.updating = b
    # ------------------------------------------------------------------------------------------------------------------
    def is_not_outdated(self):
        """
        If pair is updating offer book it returns true.
        :return: true if updating
        """
        now=time.time()
        if now - self.last_update > 30:
            return False
        return True

    def get_timestamp(self):
        return self.last_update

    # ------------------------------------------------------------------------------------------------------------------
    def get_quote_token(self):
        """
        :return: quote token
        """
        return self.quote

    def get_base_token(self):
        """
        :return: base token
        """
        return self.base


    # ------------------------------------------------------------------------------------------------------------------
    def get_symbol(self):
        """
        :return: symbol i.e. "SWTH_NEO"
        """
        return self.quote.get_name()+"_"+self.base.get_name()

    # ------------------------------------------------------------------------------------------------------------------
    def load_last_price(self):
        """
        Load last price of pairs
        :return: last price
        """
        self.last_price = float(request.public_request(self.exchange.get_url(), "/v2/tickers/last_price",
                                                       {self.get_quote_token().get_name()}))
        return self.last_price

    def set_last_price(self, price):
        """
        Set last price
        :param price: last price
        :return: None
        """
        self.last_price = price

    def get_last_price(self):
        """
        :return: last price
        """
        return self.last_price

    # ------------------------------------------------------------------------------------------------------------------
    def load_offers(self):
        """
        Load offers and create new order book.
        :param contract: contract
        :return: list of offers
        """
        if self.is_updating():
            return False
        if self.is_blocked():
            return False
        if self.is_not_outdated():
            return False


        self.set_updating(True)

        params = {"pair": self.get_symbol()}

        raw_offers = request.public_request(self.exchange.get_url(), "/v2/offers/book", params)
        self.last_update = time.time()

        if not raw_offers:
            return self.set_updating(False)


        self.asks = []
        for offer in raw_offers["asks"]:
            self.asks.append(Offer(offer["price"],offer["quantity"]))

        self.bids = []
        for offer in raw_offers["bids"]:
            self.bids.append(Offer(offer["price"], offer["quantity"]))

        log.log("pair.txt", "%s: updated" % self.get_symbol())
        self.set_updating(False)


    # ------------------------------------------------------------------------------------------------------------------
    def get_minimum_offer(self,offers,token,i=0):
        if  self.exchange.get_minimum_amount(token) > offers[i].get_quantity():
            #self.exchange.get_minimum_quantity(offers,token,i+1)
            return i



    def get_best_ask(self):
        return self.asks[0]

    def get_best_bid(self):
        return self.bids[0]

    def get_best_price(self,quantity):
        return 0

    def get_way(self,token):
        if self.base == token:
            return Pair.WAY_BUY

        if self.quote == token:
            return Pair.WAY_SELL

    def get_best(self,way):
        if way == Pair.WAY_BUY:
            return self.get_best_ask()
        if way == Pair.WAY_SELL:
            return self.get_best_bid()



    # ------------------------------------------------------------------------------------------------------------------

    def get_equal_token(self, tp):
        """
        Get the equal tokens of two pairs.
        :param tp: other pair
        :return: same token
        """
        if self.base == tp.get_base_token() or self.base == tp.get_quote_token():
            return self.base
        if self.quote == tp.get_quote_token() or self.quote == tp.get_base_token():
            return self.quote

    def get_exchange(self):
        """
        :return: get exchange
        """
        return self.exchange



    def __str__(self):
        """
        Pair to string
        :return: pair as string
        """
        return "Pair:%s " % (self.get_symbol())
