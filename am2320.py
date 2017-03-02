#!/usr/bin/python
# -*- coding: utf-8 -*-

import smbus
import time
import datetime
import threading
#import raspi_lcd as i2clcd

address = 0x5c  # 1011100(7bit,0x5c) + 0(1bit,R/W bit) = 0xb8
#ARRAY_SIZE = 1
READ_INT = 5 # [sec], # each reading interval is to be grater than 2 sec
DEBUG_MODE = True

# 日時付きでメッセージ表示
def printDateMsg(msg):
    d = datetime.datetime.today()
    print  d.strftime('%Y/%m/%d %H:%M:%S') + ' [TRMO] ' + msg

# am2320 のクラス
class Thermo(threading.Thread):

    def __init__(self):
        super(Thermo, self).__init__()
        self.__i2c = smbus.SMBus(1)
        self.__hum = 0.0
        self.__tmp = 0.0
        #self.__arrayHum = ARRAY_SIZE*[0]
        #self.__arrayTmp = ARRAY_SIZE*[0]
        self.__stop_flag = False
        self.__is_available = False
        #self.com_i2c = False
        #self.running_flag = threading.Event()
        #self.running_flag.set()

    def __updateValue(self):

        #self.com_i2c = True    # 通信開始
        if self.__is_available:
            try:    # センサsleep解除
                self.__i2c.write_i2c_block_data(address, 0x00, [])
            except:
                pass    # ACK が帰ってくるとは限らないが続行
            time.sleep(0.001)

            try:    # 読み取り命令
                self.__i2c.write_i2c_block_data(address,0x03,[0x00,0x04])
            except:
                if DEBUG_MODE: printDateMsg("[Error] am2320(1) ")
                #self.com_i2c = False	# 通信終了
                self.__hum = 0.0		# 読み取り失敗時は0.0
                self.__tmp = 0.0
                self.__is_available = False
                return
            time.sleep(0.015)

            try:    # データ受取
                block = self.__i2c.read_i2c_block_data(address,0,6)
            except:
                if DEBUG_MODE: printDateMsg("[Error] am2320(2) ")
                #self.com_i2c = False   # 通信終了
                self.__hum = 0.0        # 読み取り失敗時は0.0
                self.__tmp = 0.0
                self.__is_available = False
                return
            time.sleep(0.001)

            #if DEBUG_MODE: print "OK:   am2320"
            #self.com_i2c = False	# 通信終了
            # 一番古いデータを削除し、新しいデータを末尾に保存
            #self.__arrayHum.pop(0)
            #self.__arrayTmp.pop(0)
            #self.__arrayHum.append(float(block[2] << 8 | block[3])/10)
            #self.__arrayTmp.append(float(block[4] << 8 | block[5])/10)
            # 平均値
            #self.__hum = sum(self.__arrayHum)/ARRAY_SIZE
            #self.__tmp = sum(self.__arrayTmp)/ARRAY_SIZE
            self.__hum = (block[2] << 8 | block[3])/10.0
            self.__tmp = (block[4] << 8 | block[5])/10.0
            self.__is_available = False

    def getHum(self):
        self.__updateValue()
        return self.__hum

    def getTmp(self):
        self.__updateValue()
        return self.__tmp

    def displayValue(self):
        #print "湿度: %2.1f %" %  self.__hum
        #print "温度: %2.1f C" %  self.__tmp
        #print "湿度: " + str(self.__hum) + "％, " \
        #+ "温度: " + str(self.__tmp) + "℃"
        print "湿度: " + str(self.getHum()) + "％, " \
            + "温度: " + str(self.getTmp()) + "℃"

    def run(self):
        while not self.__stop_flag:
            #self.running_flag.wait()
            #self.__updateValue()
            self.__is_available = True
            time.sleep(READ_INT)

    def stop(self):
        self.__stop_flag = True

    # def suspend(self):
    #         self.running_flag.clear()

    # def resume(self):
    #         self.running_flag.set()

def main_loop():
    while True:
        thermo.displayValue()
        #hum_str = str(thermo.getHum())[0:4]
        #tmp_str = str(thermo.getTmp())[0:4]
        #str1 = hum_str + "%," + tmp_str + "C "
        #lcd.display_messages([str1])
        time.sleep(1)
        #thermo.suspend()
        #thermo.resume()


if __name__ == '__main__':
    thermo = Thermo()
    thermo.start()
    #lcd = i2clcd.LCDController()
    #lcd.initialize_display()

    try:
        main_loop()
    except KeyboardInterrupt:
        print "Keyboard Interrupt"
    finally:
        thermo.stop()
# ============= EOF ======================
