#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import datetime
import sys
import subprocess
# handle hardware
import am2320 as ht
import raspi_lcd as i2clcd
import RPi.GPIO as GPIO
# handle configuration files
import airalarmconf as aac

# Global variables
DEBUG = True
STU_PRT = False
LOOP_DELAY = 0.1
DELTA_TMP = 0.5
#
ON_CMD = 'cd /home/naoya/airalarm/ir; ./sendir pon.data 3 24 > /dev/null'
OFF_CMD = 'cd /home/naoya/airalarm/ir; ./sendir poff.data 3 24 > /dev/null'
#UP_CMD = 'ir/sendir ir/tup.data 3 24'
#DOWN_CMD = 'ir/sendir ir/tdown.data 3 24'
#
WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

#=========================================
# Display information on LCD (and control backlignt)
#=========================================
def taskDisp():
    d = datetime.datetime.today()

    if conf.dispMode == "CTRL":
        # Get humidity, tempareture
        hum_str = str(thermo.getHum())[0:4]
        tmp_str = str(thermo.getTmp())[0:4]
        # Generate strings for LCD
        str1 = '%02d/%02d %02d:%02d:%02d' \
                %(d.month, d.day, d.hour, d.minute, d.second)
        if hum_str == '0.0' and tmp_str == '0.0':
            hum_str = '--.-'
            tmp_str = '--.-'
        t_ctrlTemp = conf.ctrlTemp if conf.ctrlTemp < 100 else 99
        str2 = hum_str + "%," + tmp_str + "C " + str(t_ctrlTemp) + "C"
        if conf.ctrlOn == True:
            str2 += '*'

    elif conf.dispMode == "ALARM":
        # Generate strings for LCD
        str1 = '%4d/%02d/%02d (%s)' \
                %(d.year, d.month, d.day, WEEK[d.weekday()])
        str2 = '%02d:%02d:%02d  %02d:%02d' \
                %(d.hour, d.minute, d.second, \
                conf.alarmTime.hour, conf.alarmTime.minute)
        if conf.alarmOn == True:
            str2 += '*'

    #if not thermo.com_i2c: # to avoid conflict with am2320
    lcd.display_messages([str1, str2])

    ### Todo: Turn on/off Backlight < aac.dispOn


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
            print "--- Alarm! ---"


#=========================================
# Control room temparature
# This is a test function.
#=========================================
def taskCtrl():
    if conf.ctrlOn:
        if thermo.getTmp() < conf.ctrlTemp-DELTA_TMP:
            if not(conf.turnedOn):
                print "Control:ON"
                aircon_on()
                conf.turnedOn = True
        elif thermo.getTmp() > conf.ctrlTemp+DELTA_TMP:
            if conf.turnedOn:
                print "Control:OFF"
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
        taskDisp()  # Display on LCD
        taskAlarm() # Alarm at alarmTime
        taskCtrl()  # Temparature Control
        conf.checkReadConf() # check if conf is updated by CGI
        time.sleep(LOOP_DELAY)


#=========================================
# Initialize and Generate
#=========================================
if __name__ == '__main__':

    # Initialization
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)      # Use BCM GPIO numbers
    conf = aac.AirAlarmConf()   # to handle configuration file
    # LCD
    lcd = i2clcd.LCDController()
    lcd.initialize_display()
    lcd.display_messages(["RasbperryPi Zero", "Air Alarm"])
    time.sleep(1)
    # Thermometer
    thermo = ht.Thermo()
    thermo.start()

    if DEBUG: sys.stderr.write('Check error stream...\n')

    try:
        main_loop()
    except KeyboardInterrupt:
        if DEBUG: print "Keyboard Interrupt"
    finally:
        #conf.writeConf()    # save configuration
        thermo.stop()
        lcd.display_messages(["Goodbye!", ""])
        GPIO.cleanup()
# ================== EOF ==========================
