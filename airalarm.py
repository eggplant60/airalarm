#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import datetime
import sys
import subprocess
import threading
# handle hardware
#import am2320 as thermomiter
import bme280 as thermomiter
import raspi_lcd as lcd
import tsl2561 as luminometer
import RPi.GPIO as GPIO
import smbus
# handle configuration files
import aaconf as aac

# Global variables
DEBUG = False
LOOP_DELAY = 0.1
DELTA_TMP = 0.5
LOG_DELAY = 600
ON_CMD = 'cd /home/naoya/airalarm/ir; ./sendir pon.data 3 24 > /dev/null'
OFF_CMD = 'cd /home/naoya/airalarm/ir; ./sendir poff.data 3 24 > /dev/null'
#UP_CMD = 'ir/sendir ir/tup.data 3 24'
#DOWN_CMD = 'ir/sendir ir/tdown.data 3 24'
PIN_BACKLIGHT = lcd.PIN_BACKLIGHT
LUX_SW_BL = 100    # [Lux]
LOG_FILE = '/home/naoya/airalarm/log.csv'



#=========================================
# Print a message with time
#=========================================
def printDateMsg(msg):
    d = datetime.datetime.today()
    print d.strftime('%Y/%m/%d %H:%M:%S') + ' [MAIN] ' + msg

#=========================================
# Print an error with time
#=========================================
def printDateErr(msg):
    d = datetime.datetime.today()
    sys.stderr.write(d.strftime('%Y/%m/%d %H:%M:%S') \
                     + ' [MAIN] ' + msg + '\n')

#=========================================
# Display information on LCD, and control its backlignt
#=========================================
WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
def taskDisp():
    d = datetime.datetime.today()
    # Get humidity, tempareture, pressure, lumino
    hum_str = str(thermo.getHum())[0:4]
    tmp_str = str(thermo.getTmp())[0:4]
    prs_str = str(thermo.getPrs())[0:4]
    lux_str = str(lumino.getLux())[0:4]

    if hum_str == '0.0' and tmp_str == '0.0':
        hum_str = '--.-'
        tmp_str = '--.-'

    if conf.dispMode == "CTRL":
        # Generate strings for LCD
        str1 = '%02d/%02d %02d:%02d:%02d' \
                %(d.month, d.day, d.hour, d.minute, d.second)
        t_ctrlTemp = conf.ctrlTemp if conf.ctrlTemp < 100 else 99
        str2 = hum_str + "%," + tmp_str + "C " + str(t_ctrlTemp) + "C"
        if conf.ctrlOn == True:
            str2 += '*'

    elif conf.dispMode == "ALARM":
        # str1 = '%4d/%02d/%02d (%s)' \
        #         %(d.year, d.month, d.day, WEEK[d.weekday()])
        # str2 = '%02d:%02d:%02d  %02d:%02d' \
        #         %(d.hour, d.minute, d.second, \
        #         conf.alarmTime.hour, conf.alarmTime.minute)

        if conf.alarmOn == True:
            alarm = '*'
        else:
            alarm = ' '
        # Generate strings for LCD
        str1 = ' %02d:%02d:%02d %02d:%02d%s' \
                %(d.hour, d.minute, d.second, \
                  conf.alarmTime.hour, conf.alarmTime.minute, alarm)
        str2 = ' %s %s %s' \
               %(hum_str, tmp_str, prs_str)

    #if not thermo.com_i2c: # to avoid conflict with am2320
    lcd.display_messages([str1, str2])

    ### Todo: Turn on/off Backlight < conf.dispOn
    #lcd.switch_backlight(conf.dispOn)

    # Turn off backlight when
    if lumino.getLux() > LUX_SW_BL:
        lcd.switch_backlight(True)
    else:
        lcd.switch_backlight(False)


#=========================================
# check alarm time and send signal to air-conditioner
#=========================================
def taskAlarm():
    if conf.alarmOn:
        d = datetime.datetime.today()
        if d.hour == conf.alarmTime.hour \
                and d.minute == conf.alarmTime.minute:
            conf.alarmOn = False # Turn off
            conf.writeConf(calledCGI=False)
            # if thermo.getTmp() < conf.onTmpMin:
            aircon_on()
            printDateMsg("--- Alarm! ---")


#=========================================
# Control room temparature
# This is a test function.
#=========================================
def taskCtrl():
    if conf.ctrlOn:
        if thermo.getTmp() < conf.ctrlTemp-DELTA_TMP:
            if not(conf.turnedOn):
                printDateMsg("Control:ON")
                aircon_on()
                conf.turnedOn = True
        elif thermo.getTmp() > conf.ctrlTemp+DELTA_TMP:
            if conf.turnedOn:
                printDateMsg("Control:OFF")
                aircon_off()
                conf.turnedOn = False


#=========================================
# Send ir signal to power on air-conditioner
#=========================================
def aircon_on():
    time.sleep(0.5)
    subprocess.call(ON_CMD,shell=True)
    time.sleep(0.5)
    subprocess.call(ON_CMD,shell=True)
    conf.turnedOn = True


#=========================================
# Send ir signal to power off air-conditioner
#=========================================
def aircon_off():
    time.sleep(0.5)
    subprocess.call(OFF_CMD,shell=True)
    time.sleep(0.5)
    subprocess.call(OFF_CMD,shell=True)
    conf.turnedOn = False


#=========================================
# main loop
#=========================================
def main_loop():

    while True:
        taskAlarm() # Alarm at alarmTime
        taskCtrl()  # Temparature Control
        taskDisp()  # Display on LCD
        conf.checkReadConf() # check if conf is updated by CGI
        time.sleep(LOOP_DELAY)


#=========================================
# log loop
#=========================================
def log_loop():
    while True:
        print('logging...')
        with open(LOG_FILE, 'a') as f:
            str_list = [datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S')]
            str_list.append( str(thermo.getHum())[0:6] )
            str_list.append( str(thermo.getTmp())[0:6] )
            str_list.append( str(thermo.getPrs())[0:6] )
            str_list.append( str(lumino.getLux())[0:6] )
            line = ','.join(str_list) + '\n'
            f.write(line)
        time.sleep(LOG_DELAY)


#=========================================
# Initialize and Generate
#=========================================
if __name__ == '__main__':

    # Initialize GPIO, conf, bus
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)      # Use BCM GPIO numbers
    conf = aac.AirAlarmConf()   # Handler of a configuration file
    bus = smbus.SMBus(1)        # i2c bus shared by sensors and lcd
    if DEBUG: print(id(bus))

    # Sensor Initialization
    thermo = thermomiter.Thermo(bus)
    lumino = luminometer.Lumino(bus)

    # LCD  Initialization
    lcd = lcd.LCDController(bus, PIN_BACKLIGHT)
    lcd.initialize_display()
    lcd.display_messages(["RasbperryPi Zero", "Air Alarm"])
    time.sleep(1)

    if DEBUG:
        printDateMsg("Checking stdout...")
        printDateErr("Checking stderr...")

    tl = threading.Thread(target=log_loop)
    tl.setDaemon(True)
    tl.start()

    try:
        main_loop()
    except KeyboardInterrupt:
        if DEBUG: printDateMsg("Keyboard Interrupt")
    finally:
        #conf.writeConf()    # save configuration
        bus.close()
        lcd.display_messages(["Goodbye!", ""])
        time.sleep(1)
        GPIO.cleanup()
# ================== EOF ==========================
