
import time
from API.trade import Trade
from Class.pair import Pair
import API.log as log


class Equalizer(object):

    def __init__(self, start_pair, middle_pair, end_pair, start_with=None):
        """
        Create Arbitrage markets
        :param start_pair: start with pair
        :param middle_pair: trade over pair
        :param end_pair: end with pair
        :param start_with: start with token
        """
        self.outer_currency = start_pair.get_equal_token(end_pair)
        self.inner_first_currency = start_pair.get_equal_token(middle_pair)
        self.inner_second_currency = middle_pair.get_equal_token(end_pair)


        if self.outer_currency is None or \
                self.inner_first_currency is None or \
                self.inner_second_currency is None or \
                start_pair == middle_pair or \
                middle_pair == end_pair or \
                start_pair == end_pair or \
                (start_with is not None and start_with != self.outer_currency) or \
                self.outer_currency == self.inner_first_currency or \
                self.inner_first_currency == self.inner_second_currency or\
                self.inner_second_currency == self.outer_currency:
            raise ValueError("[Equalizer] %s %s %s not possible" % (start_pair.get_symbol(),
                                                                    middle_pair.get_symbol(),
                                                                    end_pair.get_symbol()))

        self.ticker = "%s-%s-%s-%s" %(self.outer_currency.get_name(),
                                      self.inner_first_currency.get_name(),
                                      self.inner_second_currency.get_name(),
                                      self.outer_currency.get_name())

        self.start_pair = start_pair
        self.middle_pair = middle_pair
        self.end_pair = end_pair

        self.start_pair_way = self.start_pair.get_way(self.outer_currency)
        self.middle_pair_way = self.middle_pair.get_way(self.inner_first_currency)
        self.end_pair_way = self.end_pair.get_way(self.inner_second_currency)


        self.timestamp = 0
        self.spread = 0

        self.updating = False
        self.last_update = 0
        self.sleep = 30

        self.trading = False
        self.view_only = True


    def toggle_view_only(self, b):
        """
        Toggle view only. If set it only prints and do not check and execute.
        :param b: bool
        :return: None
        """
        self.view_only = b

    def get_ticker(self):
        return self.ticker

    def get_view_only(self):
        return self.view_only


    def set_sleep(self,second):
        log.log("log.txt", "Set %s sleep to %d seconds" % (self.ticker, str(second)))
        self.sleep = second


    def __str__(self):
        """
        Equalizer to string
        :return: pair as string
        """
        return "Ticker:%s (%s,%s,%s) View-only:%s " % (self.get_ticker(), self.start_pair,self.middle_pair,self.end_pair,str(self.get_view_only()))




    def get_start_token(self):
        """
        :return: start token
        """
        return self.outer_currency

    def is_updating(self):
        """
        :return: true while loading order books
        """
        return self.updating

    def set_updating(self, b):
        """
        Set updating
        :param b: state
        :return: None
        """
        self.updating = b

    def must_update(self):
        if time.time() - self.last_update > self.sleep:
            return True
        return False

        # ------------------------------------------------------------------------------------------------------------------
    def update(self):
        """
        Update all markets and recalculate profits
        :return: None
        """

        #already updating
        if self.is_updating():
            return

        #we update pair
        self.set_updating(True)

        self.start_pair.load_offers()
        self.middle_pair.load_offers()
        self.end_pair.load_offers()

        start = time.time()
        while True:
            if time.time() - start > 15:
                return self.set_updating(False)

            if self.start_pair.is_updating() or\
               self.middle_pair.is_updating() or\
               self.end_pair.is_updating():
                continue
            else:
                break

        times = (self.start_pair.get_timestamp(), self.middle_pair.get_timestamp(),
                 self.end_pair.get_timestamp())

        first = min(times)
        latest = max(times)

        self.timestamp = latest
        self.spread = self.timestamp - first
        log.log("update.txt", "%s:%.3f" % (self.get_symbol(), self.spread))
        if self.spread > 25:
            return self.set_updating(False)

        best_amount = self.get_best_amount()

        self.last_update = time.time()
        if best_amount:
            #self.win(best_amount)
            self.set_updating(False)

        self.set_updating(False)
        self.trading = False




    #-------------------------------------------------------------------------------------------------------------------

    def win(self, calc):
        """
        Found win, print and execute
        :param calc: information from
        :return:
        """
        win = calc[0]
        amount = calc[1]
        percentage = win/amount * 100
        log.log_and_print("equalizer_win.txt", "%s use %16.8f %s to make %16.8f %s (%.3f%%) orderbook spread: %.3fs" %
              (self.ticker, amount / pow(10, self.outer_currency.get_decimals()), self.outer_currency.get_name(),
               win / pow(10, self.outer_currency.get_decimals()), self.outer_currency.get_name(), percentage,
               self.get_spread()))

        for trade in calc[3]:
            log.log_and_print("equalizer_win.txt", trade)

        if not self.view_only:
            self.execute(calc[3])
        self.reset_blocked()
        return

    # ------------------------------------------------------------------------------------------------------------------
    def calc(self, amount):
        try:
            all_trades = []
            trades, amount = self.start_pair.get_orderbook().taker(amount, self.outer_currency)
            all_trades.append(Trade.combine(trades))
            trades, amount = self.middle_pair.get_orderbook().taker(all_trades[0].get_want(), self.inner_first_currency)
            all_trades.append(Trade.combine(trades))
            trades, amount = self.end_pair.get_orderbook().taker(all_trades[1].get_want(), self.inner_second_currency)
            all_trades.append(Trade.combine(trades))
            return all_trades[2].get_want(), all_trades
        except KeyError:
            return 0, []
    # ------------------------------------------------------------------------------------------------------------------
    def get_spread(self):
        return self.spread

    # ------------------------------------------------------------------------------------------------------------------
    def get_spreads(self):
        return self.spread


    # ------------------------------------------------------------------------------------------------------------------
    def get_best_amount(self):

        best_win = []
        i = 0
        run = True
        while run:
            try:

                start_offer = self.start_pair.get_best(self.start_pair_way)
                log.log("equalizer-best.txt", "start_offer: %s - %s" % (self.start_pair,start_offer))

                middle_offer  = self.middle_pair.get_best(self.middle_pair_way)
                log.log("equalizer-best.txt", "middle_offer: %s - %s" % (self.middle_pair, middle_offer))

                end_offer = self.end_pair.get_best(self.end_pair_way)
                log.log("equalizer-best.txt", "end_offer: %s - %s" % (self.end_pair, end_offer))


                #balance = self.outer_currency.get_balance() / pow(10, self.outer_currency.get_decimals())

                if not start_offer or not middle_offer or not end_offer:
                    log.log("equalizer-best.txt", "Offer missing %s" % (self.ticker))
                    break

                log.log("equalizer-best.txt", "got 3 offers")
                #
                # Adjust quantity between equalizer
                start_qty=0
                middle_st_qty = 0
                middle_nd_qty=0
                end_qty=0

                middle_nd_qty = middle_offer.get_token_qty(self.inner_second_currency,self.middle_pair)
                end_qty = end_offer.get_token_qty(self.inner_second_currency,self.end_pair)

                if middle_nd_qty > end_qty:
                    middle_offer.set_token_qty(self.inner_second_currency,self.middle_pair, end_qty )

                log.log("equalizer-best.txt", "adjust quantity 1 %s > %s" % (str(middle_nd_qty),str(end_qty)))

                start_qty = start_offer.get_token_qty(self.inner_first_currency, self.start_pair)
                middle_st_qty = middle_offer.get_token_qty(self.inner_first_currency, self.middle_pair)

                if start_qty > middle_st_qty:
                    start_offer.set_token_qty(self.inner_first_currency, self.start_pair, middle_st_qty)

                log.log("equalizer-best.txt", "adjust quantity 2 %s > %s" % (str(start_qty),str(middle_st_qty)))
                #if float(balance) < float(start_offer.get_quantity()*start_offer.get_price()):
                #    start_offer.set_token_qty(self.outer_currency,self.start_pair,balance)

                log.log("equalizer-best.txt", "------------ Best start quantity %s: %s - balance: " % (self.start_pair, str(start_offer.get_quantity())))


                #
                # calculate win with quantity

                start_with = start_offer.get_token_qty(self.outer_currency,self.start_pair)
                log.log("equalizer-best.txt", "Start with %s: %s" % (self.outer_currency.get_name(), str(start_with)))


                # simulate trade 1 initial qty, way, calculate fee and get output qty
                first_trade = self.simulate_trade(self.start_pair,self.outer_currency, start_with)

                # Simulate trade 2 initial qty, way, calculate fee and get output qty

                # Simulate trade 3 qty, way, calculate fee and get output qty


                end_with = end_offer.get_token_qty(self.outer_currency,self.end_pair)
                log.log("equalizer-best.txt", "End with %s" % (str(end_with)))

                # Calculate Earning
                win = end_with - start_with
                log.log("equalizer-best.txt", "win %s" % (str(win / pow(10,self.outer_currency.get_decimals()))))
                percentage = win / start_with * 100

                if win > 0:
                    log.log("equalizer-best.txt", "Win > 0")
                else:
                    #set a timeout for update and increase if no change
                    log.log("equalizer-best.txt", "set a timeout for update and increase if no change")


                log.log("equalizer-best.txt","%s:%s:%16.8f (%.2f%%) time spread:%.3fs\n" % (self.ticker, self.get_symbol(),win / pow(10,self.outer_currency.get_decimals()),
                                                                        percentage, self.get_spread()))

                return win

                """
                Only use 90% if SWTH to remain enough for paying fees
                
                if self.outer_currency == self.start_pair.get_exchange().get_fee_token():
                    balance = balance * 0.97
                """

                """
                if not self.view_only and start_with > balance:
                    if balance < self.start_pair.get_exchange().get_minimum_amount(self.outer_currency):
                        return
                    start_with = balance
                if start_with == 0:
                    break
                end_with, trades = self.calc(start_with)

                win = end_with-start_with

                percentage = win/start_with * 100
                log_string = ":%s:%.8f (%.2f%%) time spread:%.3fs\n" % (self.get_symbol(),
                                                                     win/pow(10, self.outer_currency.get_decimals()),
                                                                     percentage, self.get_spread())

                for trade in trades:
                    log_string = log_string + str(trade) + "\n"
                log.log("equalizer_all.txt", log_string)

                if percentage > 1:
                    log.log("log.txt", "*** Trade detected on Equalizer %s, expected win %.8f (%.2f%%)" % (self.ticker,win/pow(10, self.outer_currency.get_decimals()),percentage))
                    for trade in trades:
                        pair = trade.get_pair()
                        exchange = pair.get_exchange()
                        if pair.is_blocked():
                            return
                        if exchange.get_minimum_amount(pair.get_base_token()) > trade.get_amount_base():
                            log.log("log.txt", "*** Base %s Amount too low: %s" % (str(pair.get_base_token()),str(trade.get_amount_base())))
                            return
                        if exchange.get_minimum_amount(pair.get_quote_token()) > trade.get_amount_quote():
                            log.log("log.txt", "*** Quote %s Amount too low: %s" % (str(pair.get_quote_token()), str(trade.get_amount_quote())))
                            return
                        if self.trading:
                            log.log("log.txt", "*** Already Trading this ticker %s" % (self.ticker))


                    self.trading=True
                    best_win.append((win, start_with, end_with, trades))

                else:
                    if percentage > -2:
                        log.log("equalizer_almost.txt", log_string)
                    if percentage < -10:
                        self.set_sleep(120)

                    break
                i = i + 1
                """
            except Exception as e:
                log.log("equalizer-best.txt", "Exception: %s" % (e))
                #print(e)
                #print(self.get_symbol())
                break
        """"
        if len(best_win) > 0:
            best_win = sorted(best_win, key=lambda entry: entry[0], reverse=True)
            return best_win[0]
        """



    # ------------------------------------------------------------------------------------------------------------------
    def get_symbol(self):
        return self.ticker


    # ------------------------------------------------------------------------------------------------------------------
    def simulate_trade(self, pair, token, qty):
        return self.ticker


    # ------------------------------------------------------------------------------------------------------------------
    @staticmethod
    def get_all_equalizer(pairs, start_with=None, view_only=True):
        log.log("log.txt", "Load Equalizer--------------")
        equalizers = []
        i=0
        for start_pair in pairs:
            for middle_pair in pairs:
                for end_pairs in pairs:
                    try:
                        eq = Equalizer(start_pair, middle_pair, end_pairs, start_with)
                        eq.toggle_view_only(view_only)
                        equalizers.append(eq)
                        i=i+1
                        log.log("log.txt", "Load Equalizer = %s" % (str(eq)))
                    except ValueError:
                        continue

        log.log("log.txt", "%d Equalizers Loaded" % (i))
        return equalizers


    # ------------------------------------------------------------------------------------------------------------------
    def execute(self, trades):
        log.log("execute.txt", self.get_symbol())
        for trade in trades:
            trade.get_pair().set_blocked(True)
            log.log("execute.txt", "%s" % trade)
            order_details = trade.send_order()
            time.sleep(4)
            trade.get_pair().set_blocked(False)
            if not order_details:
                trade.get_pair().set_blocked(True)
                log.log("execute.txt", "%s" % trade)
                order_details2 = trade.send_order()
                trade.get_pair().set_blocked(False)
                if not order_details2:
                    self.trading = False
                    return
        self.trading=False

    # ------------------------------------------------------------------------------------------------------------------
    def reset_blocked(self):
        self.start_pair.set_blocked(False)
        self.middle_pair.set_blocked(False)
        self.end_pair.set_blocked(False)
