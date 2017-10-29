#!/usr/bin/python
# -*- coding: utf-8 -*-

import smbus
import time
import datetime
import threading

address = 0x39 # 0100101(7bit,0x39)
READ_INT = 5   # [sec], each reading interval is to be grater than 2 sec
LOG_INT = 600  # [sec]
DEBUG_MODE = True

# Dislpay a given message with the date
def printDateMsg(msg):
    d = datetime.datetime.today()
    print  d.strftime('%Y/%m/%d %H:%M:%S') + ' [LUMI] ' + msg


# tsl2561 (except tsl2561 CS)
class Lumino():
    def __init__(self):
        self.__lux = 0.0
        self.__gain = 0x00             # 0x00=x1(default), 0x10=x16
        self.__integrationTime = 0x02  # 0x02=402ms(default), 0x01=101ms, 0x00=13.7ms
        self.__scale = 16.0            # default
        self.__i2c = smbus.SMBus(1)

        self.__enableSensor()
        if DEBUG_MODE: self.__printRegisterValue()

        self.tu = threading.Thread(target=self.__updateValue)
        self.tu.setDaemon(True)
        self.tu.start()

        self.tl = threading.Thread(target=self.__logValue)
        self.tl.setDaemon(True)
        self.tl.start()

    def __enableSensor(self):
        self.__i2c.write_i2c_block_data(address, 0x80, [0x03])

    def __printRegisterValue(self):
        timing_reg = self.__i2c.read_i2c_block_data(address, 0xA1, 1)
        id_reg = self.__i2c.read_i2c_block_data(address, 0xAA, 1)
        print "Timing Register: " + str(timing_reg)
        print "ID Register: " + str(id_reg)

    def __setGain(self):
        pass

    def __setIntegrationTime(self):
        pass

    def __loadVisibleLightRawData(self):
        data = self.__i2c.read_i2c_block_data(address, 0xAC ,2) # Read 2 Byte
        raw = data[1] << 8 | data[0]
        return raw

    def __loadInfraredRayRawData(self):
        data = self.__i2c.read_i2c_block_data(address, 0xAE ,2) # Read 2 Byte
        raw = data[1] << 8 | data[0]
        return raw

    def __calcScale(self):
        pass
    
    def __updateValue(self):
        while True:
            vl_raw = self.__loadVisibleLightRawData() * self.__scale
            ir_raw = self.__loadInfraredRayRawData() * self.__scale

            # Avoid 0 division
            if (float(vl_raw) == 0.0):
                ratio = 9999
            else:
                ratio = (ir_raw / float(vl_raw))

        
            # Calcuration of Lux
            if ((ratio >= 0) & (ratio <= 0.52)):
                tmp = (0.0315 * vl_raw) - (0.0593 * vl_raw * (ratio**1.4))
            elif (ratio <= 0.65):
                tmp = (0.0229 * vl_raw) - (0.0291 * ir_raw)
            elif (ratio <= 0.80):
                tmp = (0.0157 * vl_raw) - (0.018 * ir_raw)
            elif (ratio <= 1.3):
                tmp = (0.00338 * vl_raw) - (0.0026 * ir_raw)
            elif (ratio > 1.3):
                tmp = 0

            self.__lux = tmp
            time.sleep(READ_INT)


    def __logValue(self):
        while True:
            time.sleep(LOG_INT)
            printDateMsg(self.stringValue())


    def getLux(self):
        return self.__lux


    def stringValue(self):
        return  "Lux: " + str(self.getLux())



    def displayValue(self):
        print self.stringValue()



def main_loop():
    lumino = Lumino()
    while True:
        lumino.displayValue()
        time.sleep(1)


if __name__ == '__main__':
    try:
        main_loop()
    except KeyboardInterrupt:
        print "Keyboard Interrupt"
# ============= EOF ======================
