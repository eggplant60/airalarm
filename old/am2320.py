#!/usr/bin/python
# -*- coding: utf-8 -*-

import smbus
import time
import datetime
import threading
import crc16

ADDRESS = 0x5c # 7bit address  (will be left shifted to add the read write bit)
READ_INT = 10   # [sec], each reading interval is to be grater than 2 sec
LOG_INT = 600  # [sec]
DEBUG_MODE = True

#W_ADDR = ADDRESS << 1 + 0x00 # ADDRESS(7bit) + R/W bit(1bit)
#R_ADDR = ADDRESS << 1 + 0x01 # ADDRESS(7bit) + R/W bit(1bit)

# Print a given message with the date
def printDateMsg(msg):
    d = datetime.datetime.today()
    print  d.strftime('%Y/%m/%d %H:%M:%S') + ' [TRMO] ' + msg


# am2320
class Thermo():
    def __init__(self):
        self.__i2c_bus = smbus.SMBus(1)
        self.__hum = 0.0
        self.__tmp = 0.0

        self.tu = threading.Thread(target=self.__updateValue)
        self.tu.setDaemon(True)
        self.tu.start()

        self.tl = threading.Thread(target=self.__logValue)
        self.tl.setDaemon(True)
        self.tl.start()


    def __updateValue(self):
        while True:
            try:
                self.__i2c_bus.write_i2c_block_data(ADDRESS, 0x00, [])    # センサsleep解除
            except:
                pass  # センサはACK が帰ってくるとは限らない仕様
            time.sleep(0.001) # Min: 800us

            try:
                self.__i2c_bus.write_i2c_block_data(ADDRESS,0x03,[0x00,0x04])    # 読み取り命令
            except:
                if DEBUG_MODE: printDateMsg("[Error] am2320(1) ")
                self.__hum = 0.0		# 読み取り失敗時は0.0
                self.__tmp = 0.0
                time.sleep(READ_INT)
                continue
            time.sleep(0.002) # Min: 1.5ms

            try:
                block = self.__i2c_bus.read_i2c_block_data(ADDRESS,0,8)    # データ受取
            except:
                if DEBUG_MODE: printDateMsg("[Error] am2320(2) ")
                self.__hum = 0.0        # 読み取り失敗時は0.0
                self.__tmp = 0.0
                time.sleep(READ_INT)
                continue

            # # CRC Chech
            # #block[0] = 0x03
            # print(block)
            # crc = crc16.crc16(block[0:6])
            # print(crc & 0xFF, crc >> 8)

            self.__hum = (block[2] << 8 | block[3])/10.0
            self.__tmp = (block[4] << 8 | block[5])/10.0
            time.sleep(READ_INT)


    def __logValue(self):
        while True:
            time.sleep(LOG_INT)
            printDateMsg(self.stringValue())


    def getHum(self):
        return self.__hum


    def getTmp(self):
        return self.__tmp


    def stringValue(self):
        return  "Humidity: " + str(self.getHum()) + "％, " \
            + "Temparature: " + str(self.getTmp()) + "℃"


    def displayValue(self):
        print self.stringValue()



def main_loop():
    while True:
        thermo.displayValue()
        time.sleep(1)


if __name__ == '__main__':
    thermo = Thermo()

    try:
        main_loop()
    except KeyboardInterrupt:
        print "Keyboard Interrupt"
    # finally:
    #     thermo.stop()
# ============= EOF ======================
