#!/usr/bin/python
# -*- coding: utf-8 -*-

import smbus
import bme280
import tsl2561
import datetime
import time

class Sensors():

    def __init__(self, bus):
        self.thermo = bme280.Thermo(bus)
        self.lumino = tsl2561.Lumino(bus)

    def get_values(self):
        ret = {'date'       : datetime.datetime.today(),
               'humidity'   : self.thermo.get_hum(),
               'temperature': self.thermo.get_tmp(),
               'pressure'   : self.thermo.get_prs(),
               'illuminance': self.lumino.get_lux()
               }
        return ret


if __name__ == '__main__':
    bus = smbus.SMBus(1)          # I2C bus shared by devices
    sensors = Sensors(bus)
    time.sleep(10)

    try:
        while True:
            print(sensors.get_values())
            time.sleep(10)
    except KeyboardInterrupt:
        bus.close()

