#!/usr/bin/python
# -*- coding: utf-8 -*-

import smbus
import time
import datetime
import threading

address = 0x39 # 0100101(7bit,0x39)
READ_INT = 2   # [sec], each reading interval is to be grater than 2 sec
LOG_INT = 600  # [sec]
DEBUG = False

# Dislpay a given message with the date
def print_date_msg(msg):
    d = datetime.datetime.today()
    print  d.strftime('%Y/%m/%d %H:%M:%S') + ' [LUMI] ' + msg


# tsl2561 (except tsl2561 CS)
class Lumino():
    def __init__(self, bus):
        self.__bus = bus
        self.__lux = 0.0
        self.__gain = 0x00             # 0x00=x1(default), 0x10=x16
        self.__integragration_time = 0x02  # 0x02=402ms(default), 0x01=101ms, 0x00=13.7ms
        self.__scale = 16.0            # default

        self.__enable_sensor()
        if DEBUG: self.__print_register_value()

        self.tu = threading.Thread(target=self.__update_value)
        self.tu.setDaemon(True)
        self.tu.start()


    def __enable_sensor(self):
        self.__bus.write_i2c_block_data(address, 0x80, [0x03])

        
    def __print_register_value(self):
        timing_reg = self.__bus.read_i2c_block_data(address, 0xA1, 1)
        id_reg = self.__bus.read_i2c_block_data(address, 0xAA, 1)
        print "Timing Register: " + str(timing_reg)
        print "ID Register: " + str(id_reg)

        
    def __set_gain(self):
        pass

    
    def __set_integration_time(self):
        pass

    def __load_visible_light_rawdata(self):
        data = self.__bus.read_i2c_block_data(address, 0xAC ,2) # Read 2 Byte
        raw = data[1] << 8 | data[0]
        return raw

    def __load_infrared_ray_rawdata(self):
        data = self.__bus.read_i2c_block_data(address, 0xAE ,2) # Read 2 Byte
        raw = data[1] << 8 | data[0]
        return raw

    def __calc_scale(self):
        pass

    def __update_value(self):
        while True:
            vl_raw = self.__load_visible_light_rawdata() * self.__scale
            ir_raw = self.__load_infrared_ray_rawdata() * self.__scale


            if DEBUG: print_date_msg(str(id(self.__bus)))

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


    def __log_value(self):
        while True:
            time.sleep(LOG_INT)
            print_date_msg(self.stringValue())


    def get_lux(self):
        return self.__lux


    def string_value(self):
        return  "Lux: " + str(self.get_lux())


    def display_value(self):
        print self.string_value()



def main_loop():
    bus = smbus.SMBus(1)
    lumino = Lumino(bus)
    while True:
        lumino.display_value()
        time.sleep(1)


if __name__ == '__main__':
    try:
        main_loop()
    except KeyboardInterrupt:
        print "Keyboard Interrupt"
# ============= EOF ======================
