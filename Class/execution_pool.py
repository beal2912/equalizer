

from API.trade import Trade
from API.offer import Offer
import API.log as log
import array as arr
import time

class ExecutionPool(object):

    def __init__(self):
        """
        Create a pool to manage trade execution
        """
        log.log("execution.txt", "Initialize Execution Pool")
        self.id=0
        self.pending = []
        self.executed = []
        self.error = []



    def add(self,ticker,trades):
        if self.pending.get(ticker,False):
            log.log("execution.txt", "Trade on the same Ticker %s already pending" % (ticker) )
        else:
            self.pending[ticker] = trades





    def run(self):
        """
        Execute Trade in order
        :return: None
        """
        while len(self.pending)>0:

            trades = self.pending[0]
            if self.verify(trades):
                for trade in trades:

                    trade.get_pair().set_blocked(True)

                    log.log("execute.txt", "%s" % trade)

                    order_details = trade.send_order()
                    time.sleep(5)

                    trade.get_pair().set_blocked(False)

                    if not order_details:
                        trade.get_pair().set_blocked(True)
                        log.log("execute.txt", "%s" % trade)
                        order_details2 = trade.send_order()
                        trade.get_pair().set_blocked(False)
            else:
                #trade not valid anymore
                self.pending.pop(0)







        time.sleep(5)
        self.run()
