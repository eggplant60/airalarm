#!/usr/bin/python
# -*- coding: utf-8 -*-

import smbus
import time
import datetime
import threading

ADDRESS = 0x76 # 7bit address (will be left shifted to add the read write bit)
READ_INT = 2  # [sec]
LOG_INT = 600  # [sec]
DEBUG = True

# Print a given message with the date
def printDateMsg(msg):
    d = datetime.datetime.today()
    print d.strftime('%Y/%m/%d %H:%M:%S') + ' [TRMO] ' + msg


# BME280
class Thermo():
    def __init__(self, bus):
        self.bus = bus
        self.prs = 0.0
        self.tmp = 0.0
        self.hum = 0.0

        # list of calibration parameters
        self.digPrs = []
        self.digTmp = []
        self.digHum = []
        self.t_fine = 0.0

        # Setup
        self.setup()

        # Get calibration parameters
        self.get_calib_param()

        # Thread for updating values
        self.tu = threading.Thread(target=self.updateValue)
        self.tu.setDaemon(True)
        self.tu.start()

        # Thread for logging
        self.tl = threading.Thread(target=self.logValue)
        self.tl.setDaemon(True)
        self.tl.start()

    def setup(self):
        osrs_t = 1  # Temperature oversampling x 1
        osrs_p = 1  # Pressure oversampling x 1
        osrs_h = 1  # Humidity oversampling x 1
        mode = 3  # Normal mode
        t_sb = 5  # Tstandby 1000ms
        filter = 0  # Filter off
        spi3w_en = 0  # 3-wire SPI Disable

        ctrl_hum_reg = osrs_h
        ctrl_meas_reg = (osrs_t << 5) | (osrs_p << 2) | mode
        config_reg = (t_sb << 5) | (filter << 2) | spi3w_en

        self.bus.write_byte_data(ADDRESS, 0xF2, ctrl_hum_reg)
        self.bus.write_byte_data(ADDRESS, 0xF4, ctrl_meas_reg)
        self.bus.write_byte_data(ADDRESS, 0xF5, config_reg)

    def get_calib_param(self):
        calib = self.bus.read_i2c_block_data(ADDRESS, 0x88, 24)
        calib.append(self.bus.read_byte_data(ADDRESS, 0xA1))
        calib.extend(self.bus.read_i2c_block_data(ADDRESS, 0xE1, 7))

        self.digTmp.append((calib[1] << 8) | calib[0])
        self.digTmp.append((calib[3] << 8) | calib[2])
        self.digTmp.append((calib[5] << 8) | calib[4])
        self.digPrs.append((calib[7] << 8) | calib[6])
        self.digPrs.append((calib[9] << 8) | calib[8])
        self.digPrs.append((calib[11]<< 8) | calib[10])
        self.digPrs.append((calib[13]<< 8) | calib[12])
        self.digPrs.append((calib[15]<< 8) | calib[14])
        self.digPrs.append((calib[17]<< 8) | calib[16])
        self.digPrs.append((calib[19]<< 8) | calib[18])
        self.digPrs.append((calib[21]<< 8) | calib[20])
        self.digPrs.append((calib[23]<< 8) | calib[22])
        self.digHum.append( calib[24] )
        self.digHum.append((calib[26]<< 8) | calib[25])
        self.digHum.append( calib[27] )
        self.digHum.append((calib[28]<< 4) | (0x0F & calib[29]))
        self.digHum.append((calib[30]<< 4) | ((calib[29] >> 4) & 0x0F))
        self.digHum.append( calib[31] )

        for i in range(1,2):
            if self.digTmp[i] & 0x8000:
                self.digTmp[i] = (-self.digTmp[i] ^ 0xFFFF) + 1

        for i in range(1,8):
            if self.digPrs[i] & 0x8000:
                self.digPrs[i] = (-self.digPrs[i] ^ 0xFFFF) + 1

        for i in range(0,6):
            if self.digHum[i] & 0x8000:
                self.digHum[i] = (-self.digHum[i] ^ 0xFFFF) + 1


    def updateValue(self):
        while True:
            try:
                data = self.bus.read_i2c_block_data(ADDRESS, 0xF7, 8)  # Read 8 Bytes
                prs_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
                tmp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
                hum_raw = (data[6] << 8) | data[7]
                #print(prs_raw, tmp_raw, hum_raw)
                self.prs = self.compensatePrs(prs_raw)
                self.tmp = self.compensateTmp(tmp_raw)
                self.hum = self.compensateHum(hum_raw)
            except:
                if DEBUG: printDateMsg("Error: bme280(1)")
            time.sleep(READ_INT)


    def compensatePrs(self, adc_P):
        pressure = 0.0

        v1 = (self.t_fine / 2.0) - 64000.0
        v2 = (((v1 / 4.0) * (v1 / 4.0)) / 2048) * self.digPrs[5]
        v2 = v2 + ((v1 * self.digPrs[4]) * 2.0)
        v2 = (v2 / 4.0) + (self.digPrs[3] * 65536.0)
        v1 = (((self.digPrs[2] * (((v1 / 4.0) * (v1 / 4.0)) / 8192)) / 8) \
            + ((self.digPrs[1] * v1) / 2.0)) / 262144
        v1 = ((32768 + v1) * self.digPrs[0]) / 32768

        if v1 == 0:
            return 0.0
        pressure = ((1048576 - adc_P) - (v2 / 4096)) * 3125
        if pressure < 0x80000000:
            pressure = (pressure * 2.0) / v1
        else:
            pressure = (pressure / v1) * 2
        v1 = (self.digPrs[8] * (((pressure / 8.0) * (pressure / 8.0)) / 8192.0)) / 4096
        v2 = ((pressure / 4.0) * self.digPrs[7]) / 8192.0
        pressure = pressure + ((v1 + v2 + self.digPrs[6]) / 16.0)

        return pressure/100


    def compensateTmp(self, adc_T):
        v1 = (adc_T / 16384.0 - self.digTmp[0] / 1024.0) * self.digTmp[1]
        v2 = (adc_T / 131072.0 - self.digTmp[0] / 8192.0) \
            * (adc_T / 131072.0 - self.digTmp[0] / 8192.0) * self.digTmp[2]
        self.t_fine = v1 + v2
        temperature = self.t_fine / 5120.0

        return temperature


    def compensateHum(self, adc_H):
        var_h = self.t_fine - 76800.0
        if var_h != 0:
            var_h = (adc_H - (self.digHum[3] * 64.0 \
                + self.digHum[4]/16384.0 * var_h)) \
                * (self.digHum[1] / 65536.0 * (1.0 + self.digHum[5] \
                / 67108864.0 * var_h \
                * (1.0 + self.digHum[2] / 67108864.0 * var_h)))
        else:
            return 0.0
        var_h = var_h * (1.0 - self.digHum[0] * var_h / 524288.0)
        if var_h > 100.0:
            var_h = 100.0
        elif var_h < 0.0:
            var_h = 0.0

        return var_h


    def logValue(self):
        while True:
            time.sleep(LOG_INT)
            printDateMsg(self.stringValue())

    def getHum(self):
        return self.hum

    def getTmp(self):
        return self.tmp

    def getPrs(self):
        return self.prs

    def stringValue(self):
        return  "Humidity: " + str(self.getHum()) + "％, " \
            + "Temparature: " + str(self.getTmp()) + "C, " \
            + "Pressure: " + str(self.getPrs()) + "hPa"

    def displayValue(self):
        print self.stringValue()



def main_loop():
    while True:
        thermo.displayValue()
        time.sleep(1)


if __name__ == '__main__':
    bus = smbus.SMBus(1)
    thermo = Thermo(bus)

    try:
        main_loop()
    except KeyboardInterrupt:
        print "Keyboard Interrupt"
# ============= EOF ======================
