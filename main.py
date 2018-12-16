from Class.switcheo import Switcheo
from equalizer import Equalizer
from API.equalizer_updater import EqualizerUpdater
from neocore.KeyPair import KeyPair

import time

#PRIVATE_KEY = "ko private"
PRIVATE_KEY = KeyPair.PrivateKeyFromNEP2("6PYTrmnzzrf3FmQd5sBe3SKqJC9AJs94ApsuEo7uepJwtKBgVbEnrBH2ER","y9ygj25ZGSMz-*sZ");
PRIVATE_KEY2 = KeyPair.PrivateKeyFromWIF("L1y7Ng3ye6YJbi3NmyAuWA3sBzAV835LYjLqhuckNwH7zNqRBLyV");




def main():
    print("Equalizer searches for instant profits with the perfect amount.")
    print("If instant profit is found it will printed to the console, keep waiting")
    print("Use 'tail -f logs/mainnet/equalizer_all.txt' (only linux) to see all results even losses.")
    print("Only trades with profit will be printed.")
    print(PRIVATE_KEY)
    print(len(PRIVATE_KEY))

    #print(bytes.fromhex(PRIVATE_KEY2))


    switcheo = Switcheo(private_key=PRIVATE_KEY)

    print("Start loading Switcheo")
    switcheo.initialise()
    print("Start loading Equalizer")
    equalizers = Equalizer.get_all_equalizer(switcheo.get_pairs(), switcheo.get_token("LX"))

    #equalizers = equalizers + Equalizer.get_all_equalizer(switcheo.get_pairs(), switcheo.get_token("SWTH"), switcheo.get_key_pair() is None)
    #equalizers = equalizers + Equalizer.get_all_equalizer(switcheo.get_pairs(), switcheo.get_token("GAS"), switcheo.get_key_pair() is None)

    equalizer_updater = EqualizerUpdater(equalizers)
    equalizer_updater.start()

    #
    while True:
       try:
           print("time sleep start----------------")
           time.sleep(5)
           print("time sleep end------------------")
           switcheo.load_balances()
           switcheo.load_last_prices()
           #print("Offer call to API: "+str(offerUpdateNum))
       except Exception as e:
           print(e)


if __name__ == "__main__":
    main()
