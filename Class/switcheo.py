"""
author: Devel484
"""
import API.api_request as request
from API.contract import Contract
from API.token import Token
from Class.pair import Pair
from API.trade import Trade

import API.log as log

from switcheo.authenticated_client import AuthenticatedClient
from neocore.KeyPair import KeyPair
from switcheo.neo.utils import neo_get_scripthash_from_private_key
from requests.exceptions import HTTPError
import time
import datetime


class Switcheo(object):

    _API_URL = [
        "https://api.switcheo.network",
        "https://test-api.switcheo.network"
    ]

    MAIN_NET = 0
    TEST_NET = 1

    API_NET = None

    def __init__(self, api_net=MAIN_NET, fees=0.0015, fixed_fee=77000000, private_key=None, fee_token_name=None, discount=0.25):
        """
        Create new Switcheo exchange with url, fee rate and private key
        :param api_net:
        :param fees:
        :param private_key:
        """
        self.url = Switcheo._API_URL[api_net]
        self.tokens = []
        self.pairs = []
        self.contracts = []
        self.fees = fees
        self.fixed_fee = fixed_fee
        self.fee_token_name = fee_token_name
        self.fee_token = None
        self.key_pair = None
        self.discount = discount
        self.client = AuthenticatedClient(api_url=self.url)
        if private_key:
            try:
                self.key_pair = KeyPair(private_key)
            except:
                self.key_pair = None
                print("No or incorrect private key. Equalizer changes to view only mode")

    def initialise(self):
        """
        Initialise exchange by loading some data.
        :return: None
        """
        log.log("log.txt", "Initialize ----------------")
        log.log("log.txt", "Load contract--------------")
        self.load_contracts()
        log.log("log.txt", "Load Tokens----------------")
        self.load_tokens()
        log.log("log.txt", "Load Pairs-----------------")
        self.load_pairs()
        log.log("log.txt", "Load Last price------------")
        self.load_last_prices()
        log.log("log.txt", "Load Balance---------------")
        self.load_balances()

        if self.fee_token_name:
            self.fee_token = self.get_token(self.fee_token_name)


    @staticmethod
    def get_minimum_amount(token):
        """
        Get minimum trading amount of token
        :param token:
        :return:
        """
        if token.get_name() == "NEO":
            return 0.1 * pow(10, 8)

        if token.get_name() == "GAS":
            return 0.2 * pow(10, 8)

        return 1 * pow(10, token.get_decimals())

    def get_key_pair(self):
        """
        :return: Neo Key Pair
        """
        return self.key_pair

    def get_fees(self):
        """
        :return: fee rate
        """
        return self.fees

    def get_url(self):
        """
        :return: basic URL
        """
        return self.url

    def get_timestamp(self):
        """
        :return: timestamp in seconds
        """
        if not request.public_request(self.url, "/v2/exchange/timestamp"):
            return
        return int(request.public_request(self.url, "/v2/exchange/timestamp")["timestamp"])/1000

    def load_contracts(self):
        """
        Load contracts and creates objects
        :return: list of objects
        """
        raw_contracts = request.public_request(self.url, "/v2/exchange/contracts")
        if not raw_contracts:
            log.log("log.txt", "Error loading Contract - no data")
            return
        self.contracts = []
        i=0
        for key in raw_contracts:
            self.contracts.append(Contract(key, raw_contracts[key]))
            i=i+1
        log.log("log.txt", "%d contracts loaded" % (i))
        return self.contracts

    def get_contracts(self):
        """
        :return: contracts
        """
        return self.contracts

    def get_contract(self, blockchain="NEO"):
        """
        Get contract of blockchain
        :param blockchain: blockchain name
        :return: contract
        """
        for contract in self.contracts:
            if contract.get_blockchain() == blockchain:
                return contract
        return None

    def load_tokens(self):
        """
        Load all tokens from exchange and create objects
        :return: list of tokens
        """
        raw_tokens = request.public_request(self.url, "/v2/exchange/tokens")
        if not raw_tokens:
            log.log("log.txt", "Error loading Token - no data")
            return
        self.tokens = []
        i = 0
        for key in raw_tokens:
            if raw_tokens[key]["trading_active"]:
                self.tokens.append(Token(key, raw_tokens[key]["decimals"], raw_tokens[key]["hash"], raw_tokens[key]["minimum_quantity"]))
                log.log("log.txt", "%s loaded - minimum is %s" % (key,raw_tokens[key]["minimum_quantity"]))
                i = i + 1
            else:
                log.log("log.txt", "%s not loaded" % (key))

        log.log("log.txt", "%d tokens loaded" % (i))
        return self.tokens

    def get_tokens(self):
        """
        :return: tokens
        """
        return self.tokens

    def get_token(self, name_or_hash):
        """
        :param name_or_hash: name or hash of token
        :return: token
        """
        for token in self.tokens:
            if token.get_name() == name_or_hash or token.get_hash() == name_or_hash:
                return token
        return None

    def load_pairs(self, bases=None):
        """
        Load all pairs from exchange(with bases)
        :param bases: i.e. NEO, SWTH, ...
        :return: List of objects
        """
        params = None
        if bases:
            params = {"bases": bases}
        raw_pairs = request.public_request(self.url, "/v2/exchange/pairs", params)
        if not raw_pairs:
            log.log("log.txt", "Error loading Pairs - no data")
            return
        self.pairs = []
        i = 0
        for val in raw_pairs:
            quote, base = val.split("_")
            quote_token = self.get_token(quote)
            base_token = self.get_token(base)
            if not quote_token or not base_token:
                continue
            self.pairs.append(Pair(self, quote_token, base_token))
            log.log("log.txt", "%s loaded" % (val))
            i = i + 1

        log.log("log.txt", "%d Pairs loaded" % (i))
        return self.pairs

    def get_pairs(self):
        """
        :return: pairs
        """
        return self.pairs

    def get_pair(self, symbol):
        """
        Get pair with symbol i.e. SWTH_NEO
        :param symbol: symbol
        :return: pair
        """
        for pair in self.pairs:
            if pair.get_symbol() == symbol:
                return pair
        return None

    def get_pair_by_tokens(self, token1, token2):
        """
        Try to find pair with token1_token2 or token2_token1
        :param token1: token
        :param token2: token
        :return: pair
        """
        pair = self.get_pair(token1.get_name()+"_"+token2.get_name())
        if pair:
            return pair
        pair = self.get_pair(token2.get_name()+"_"+token1.get_name())
        return pair

    def load_last_prices(self):
        """
        Load price of each pair
        :return: list of prices
        """
        prices = request.public_request(self.get_url(), "/v2/tickers/last_price")
        if not prices:
            return
        for quote in prices:
            for base in prices[quote]:
                pair = self.get_pair(quote+"_"+base)
                if not pair:
                    continue
                pair.set_last_price(float(prices[quote][base]))
        return prices

    def load_balances(self):
        """
        Load all balances from the exchange and updates them in the tokens
        :return: balances
        """
        if self.get_key_pair() is None:
            log.log("log.txt", "No Pair Loaded")
            return []
        params = {
            "addresses": neo_get_scripthash_from_private_key(self.key_pair.PrivateKey),
            "contract_hashes": self.get_contract("NEO").get_latest_hash()
        }

        raw_balances = request.public_request(self.get_url(), "/v2/balances", params)
        if not raw_balances:
            log.log("log.txt", "No balance Pair")
            return

        for token in self.tokens:
            token.set_balance(0)

        for name in raw_balances["confirmed"]:
            token = self.get_token(name)
            token.set_balance(int(float(raw_balances["confirmed"][name])))
            #log.log("log.txt", "%s=%d" % (name,int(float(raw_balances["confirmed"][name]))))
        return raw_balances


    def load_orders(self, pair=None):
        """
        Load all orders
        :param pair: orders from pair
        :return: orders
        """
        pair_name = ""
        if pair:
            pair_name = pair.get_symbol()
        params = {
            "address": neo_get_scripthash_from_private_key(self.key_pair.PrivateKey),
            "contract_hash": self.get_contract("NEO").get_latest_hash(),
            "pair": pair_name
        }

        orders = request.public_request(self.get_url(), "/v2/orders", params)
        if not orders:
            return
        trades = []
        for order_details in orders:
            trades = trades + self.order_to_trades(order_details)
        return trades

    def time_to_timestamp(self, timestring):
        """
        Convert time string to timestamp
        :param timestring: time as string
        :return: timestamp
        """
        timestring, milliseconds = timestring.split(".")
        timestamp = time.mktime(datetime.datetime.strptime(timestring, "%Y-%m-%dT%H:%M:%S").timetuple())
        milliseconds = milliseconds[:len(milliseconds)-1]
        milliseconds = int(milliseconds)/pow(10, len(milliseconds))
        timestamp = timestamp + milliseconds
        return timestamp

    def order_to_trades(self, order_details):
        """
        Order details to trades
        :param order_details: details of orders
        :return: list of trades
        """
        trades = []
        way = Trade.get_trade_way(order_details["side"])
        use_native_token = order_details["use_native_token"]

        want_token = self.get_token(order_details["want_asset_id"])
        offer_token = self.get_token(order_details["offer_asset_id"])
        pair = self.get_pair_by_tokens(want_token, offer_token)

        fee_currency = want_token
        if use_native_token:
            fee_currency = self.get_fee_token()

        state = None
        if order_details["status"] == "pending":
            state = Trade.STATE_PENDING
        elif order_details["status"] == "expired":
            state = Trade.STATE_CANCELED
        elif order_details["status"] == "processed":
            if order_details["order_status"] == "open":
                state = Trade.STATE_ACTIVE
            elif order_details["order_status"] == "completed":
                state = Trade.STATE_FILLED
            else:
                state = Trade.STATE_CANCELED
        for fills in order_details["fills"]:

            timestamp = self.time_to_timestamp(fills["created_at"])
            fee_amount = 0
            if use_native_token:
                fee_amount = int(fills["fee_amount"])
            price = float(fills["price"])
            if not pair:
                raise ValueError("Not able to find pair with tokens:"+want_token+" and "+offer_token)
            quote_amount = int(fills["want_amount"])
            base_amount = quote_amount * price
            if way == Trade.WAY_SELL:
                base_amount = int(fills["want_amount"])
                quote_amount = int(base_amount / price)

            trades.append(Trade(pair, way, price, base_amount, quote_amount, timestamp, Trade.TRADE_TYPE_TAKER, state, fills["id"], 1, fee_currency, fee_amount))

        for makes in order_details["makes"]:
            timestamp = self.time_to_timestamp(makes["created_at"])
            price = float(makes["price"])
            if not pair:
                raise ValueError("Not able to find pair with tokens:"+want_token+" and "+offer_token)
            quote_amount = int(makes["want_amount"])
            base_amount = quote_amount * price
            if way == Trade.WAY_SELL:
                base_amount = int(makes["want_amount"])
                quote_amount = int(base_amount / price)

            available_amount = 0
            if makes["available_amount"] and makes["available_amount"] != "":
                available_amount = float(makes["available_amount"])

            offer_amount = 0
            if makes["offer_amount"] and makes["offer_amount"] != "":
                offer_amount = float(makes["offer_amount"])

            filled_amount = 0
            if makes["filled_amount"] and makes["filled_amount"] != "":
                filled_amount = float(makes["filled_amount"])

            filled = (offer_amount - available_amount) / offer_amount

            if state != Trade.STATE_CANCELED:
                if filled == 1:
                    state = Trade.STATE_FILLED
                elif filled == 0:
                    state = Trade.STATE_ACTIVE
                else:
                    state = Trade.STATE_PART_FILLED
            else:
                filled = filled_amount / offer_amount
            """
            if makes["status"] == "cancelled" or makes["status"] == "expired":
                state = Trade.STATE_CANCELED"""

            fee_amount = 0
            if use_native_token:
                for t in makes["trades"]:
                    fee_amount += int(t["fee_amount"])

            trades.append(Trade(pair, way, price, base_amount, quote_amount, timestamp, Trade.TRADE_TYPE_MAKER, state, makes["id"], filled, fee_currency, fee_amount))

        return trades

    def send_order(self, trade):
        """
        Send and order to the exchange and executes it
        :param trade: executing trade
        :return: order details
        """
        if not self.get_key_pair():
            return None

        price = trade.get_price()

        """
        Try to get amount, if not possible reduce precision
        """
        order_details = None
        details = None
        trades = None
        for i in range(3):
            try:
                want_amount = (trade.get_want() * pow(0.999, i))/pow(10, 8)

                order_details = self.client.create_order(private_key=self.key_pair, pair=str(trade.get_pair().get_symbol()),
                                                         side=str(trade.get_trade_way_as_string().lower()), price=price, amount=want_amount, use_native_token=True)

                if order_details:
                    trades = self.order_to_trades(order_details)
                    log.log("send_order.txt", "Virtual order:")
                    log.log("send_order.txt", trade)
                    log.log("send_order.txt", "Create order:")
                    for t in trades:
                        log.log("send_order.txt", t)

                    details = self.client.execute_order(order_details, self.key_pair)
                    trades = self.order_to_trades(details)
                    log.log("send_order.txt", "Execute order(s)")
                    for t in trades:
                        log.log_and_print("send_order.txt", t)
                    break

            except HTTPError as e:
                log.log("send_order.txt", "[%s]:(%s):%s" % (e.response.status_code, e.response.url,
                                                                 e.response.text))
                continue



        if not order_details:
            log.log_and_print("execute.txt", "Not possible to get valid order details for pair: %s" % trade.get_pair().get_symbol())
            return

        if not details:
            log.log_and_print("execute.txt", "Not possible to get valid executing order details for pair: %s" % trade.get_pair().get_symbol())

        return trades

    def get_fee_token(self):
        """
        Get the native fee token
        :return: fee token
        """
        return self.fee_token

    def calculate_fees(self, trade):
        """
        Calculates fees
        I.e.
        BUY NEO_SWTH pay fees in SWTH * discount
        SELL NEO_SWTH pay fees in SWTH -> fees in NEO -> lastprice NEO_SWTH -> SWTH * discount
        BUY APH_NEO pay fees SWTH -> fees in APH -> last price NEO_APH -> last price NEO_SWTH -> SWTH * discount
        SELL SWTH_GAS -> fees GAS -> GAS_NEO
        :param trade: trade
        :return: None
        """

        # calculate fixed fee
        fixed_amount = 0
        neo_token = self.get_token("NEO")
        neo_to_fee_token = self.get_pair_by_tokens(neo_token, self.get_fee_token())

        if neo_to_fee_token:
            fixed_amount = self.fixed_fee * neo_to_fee_token.get_last_price()
            log.log("log.txt", "neo fixed amount %16.8f = %16.8f * %16.8f" % (fixed_amount, self.fixed_fee,neo_to_fee_token.get_last_price()))

        else:
            log.log("error.txt","Unable to calculate fixed fee amount")


        # calculate neo value of trade
        neo_amount = trade.get_neo_value()

        # if we use native token for fee
        if trade.get_fee_token() == self.get_fee_token():
            # SWTH
            neo_fee_amount = ( neo_amount * self.get_fees() )
            swth_fee_amount= neo_fee_amount / neo_to_fee_token.get_last_price() + self.fixed_fee
            native_fee_amount = float(swth_fee_amount * (1+self.discount-self.discount))
            trade.set_fees(native_fee_amount)
        # else calculate fee with base token
        else:
            if neo_token == trade.get_pair().get_base_token():
                neo_fee_amount = (neo_amount * self.get_fees()) + fixed_amount
                trade.set_fees(float(neo_fee_amount))
            else:
                # manque l'ajout des fixed base fees
                base_fee_amount = trade.get_amount_base() * self.get_fees()
                trade.set_fees(float(base_fee_amount))








