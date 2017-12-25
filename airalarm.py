#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import datetime
import sys
import subprocess
import threading

import RPi.GPIO as gpio
import smbus
from flask import Flask, jsonify, request, render_template
import requests


# Private Library
import bme280
import raspi_lcd
import tsl2561
import aaconf
import controller


# Global variables
DEBUG = False
LOOP_DELAY = 0.1
DELTA_TMP = 0.5
LOG_DELAY = 600
PIN_BACKLIGHT = raspi_lcd.PIN_BACKLIGHT
LUX_SW_BL = 100    # [Lux]
LOG_FILE = '/home/naoya/airalarm/log.csv'


#=========================================
# Print a message with time
#=========================================
def print_date_msg(msg):
    d = datetime.datetime.today()
    print d.strftime('%Y/%m/%d %H:%M:%S') + ' [MAIN] ' + msg

    
#=========================================
# Print an error with time
#=========================================
def print_date_err(msg):
    d = datetime.datetime.today()
    sys.stderr.write(d.strftime('%Y/%m/%d %H:%M:%S') \
                     + ' [MAIN] ' + msg + '\n')

    
#=========================================
# Display information on LCD, and control its backlignt
#=========================================

def task_disp():
    WEEK = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    
    d = datetime.datetime.today()
    # Get humidity, tempareture, pressure, lumino
    hum_str = str(thermo.get_hum())[0:4]
    tmp_str = str(thermo.get_tmp())[0:4]
    prs_str = str(thermo.get_prs())[0:4]
    lux_str = str(lumino.get_lux())[0:4]

    if hum_str == '0.0' and tmp_str == '0.0':
        hum_str = '--.-'
        tmp_str = '--.-'

    if conf.get_conf('alarm_on') == 'on':
        alarm_str = '*'
    else:
        alarm_str = ' '
        
    # Generate strings for LCD
    str1 = ' %02d:%02d:%02d %s%s' \
           %(d.hour, d.minute, d.second, \
             conf.get_str_alarm_time(), alarm_str)
    str2 = ' %s %s %s' \
           %(hum_str, tmp_str, prs_str)
    lcd.display_messages([str1, str2])

    # Turn off backlight depending on luminous intensity
    if lumino.get_lux() > LUX_SW_BL:
        lcd.switch_backlight(True)
    else:
        lcd.switch_backlight(False)



#=========================================
# Send Ir signals to aircon
# 1. Power on aircon if it is alarm time
# 2. Turn up/down aircon depending on room temparature
#=========================================
def task_ir():
    # 1.
    if conf.get_conf('alarm_on') == 'on':
        d = datetime.datetime.today()
        a_time = conf.get_conf('alarm_time')       
        if d.hour == a_time['hour'] and d.minute == a_time['minute']:
            ctrl_air.enqueue('p_on')
            conf.set_conf(alarm_on='off') # Clear flag
            conf.write_conf()
            print_date_msg("=== Power ON! ===")

    # 2. 
    # elif conf.ctrlOn:
    #     if thermo.getTmp() < conf.ctrlTemp-DELTA_TMP:
    #         if not(conf.turnedOn):
    #             print_date_msg("Control:ON")
    #             aircon_on()
    #             conf.turnedOn = True
    #     elif thermo.getTmp() > conf.ctrlTemp+DELTA_TMP:
    #         if conf.turnedOn:
    #             print_date_msg("Control:OFF")
    #             aircon_off()
    #             conf.turnedOn = False
   
    ctrl_air.dequeue_all() # execute commands



#=========================================
# main loop
#=========================================
def main_loop():

    while True:
        task_ir()    # Send ir signal to aircon
        task_disp()  # Display on LCD
        time.sleep(LOOP_DELAY)

        

#=========================================
# logging loop
#=========================================
def log_loop():
    time.sleep(10) # waiting for starting up devices 
    while True:
        print_date_msg('logging...')
        with open(LOG_FILE, 'a') as f:
            str_list = [datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S')]
            str_list.append( str(thermo.get_hum())[0:6] )
            str_list.append( str(thermo.get_tmp())[0:6] )
            str_list.append( str(thermo.get_prs())[0:6] )
            str_list.append( str(lumino.get_lux())[0:6] )
            line = ','.join(str_list) + '\n'
            f.write(line)
        time.sleep(LOG_DELAY)

        

#=========================================
# Web API
#=========================================
app = Flask(__name__)

def webapi_loop():
    app.run(host='192.168.11.204', port=80)

    
def sw_initial_value(key, invert=False):
    if not invert:
        return "selected" if conf.get_conf(key) == 'on' else ""
    else:
        return "selected" if conf.get_conf(key) == 'off' else ""

    
def return_preset():
    return {'alarm_sw_on' : sw_initial_value('alarm_on'),
            'alarm_sw_off': sw_initial_value('alarm_on', invert=True),
            'alarm_time'  : conf.get_str_alarm_time(),
            'ctrl_sw_on'  : sw_initial_value('ctrl_on'),
            'ctrl_sw_off' : sw_initial_value('ctrl_on', invert=True),
            'ctrl_temp'   : conf.get_conf('ctrl_temp')
    }


@app.route('/app/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', preset=return_preset(), submit=False)


@app.route('/app/post', methods=['POST'])
def post():
    try:
        time_list = request.form['alarm_time'].split(':')
        
        t = conf.set_conf(alarm_on=request.form['alarm_sw'],
                            alarm_time={
                                'hour': int(time_list[0]),
                                'minute': int(time_list[1])
                            },
                            ctrl_on=request.form['ctrl_sw'],
                            ctrl_temp=int(request.form['ctrl_temp'])
        )
        if t:
            conf.write_conf()
        else:
            print_date_err('Missing update of conf')
        return render_template('index.html', preset=return_preset(), submit=True)
                          
    except:
        return redirect(url_for('index'))

    
@app.route('/app/values', methods=['GET'])
def get_values():
    response = {
        'date': datetime.datetime.today(),
        'temp': thermo.get_tmp(),
        'hum' : thermo.get_hum(),
        'lux' : lumino.get_lux(),
        'prs' : thermo.get_prs(),
    }
    return jsonify(response), 200


@app.route('/app/ctrl', methods=['POST'])
def post_ctrl():

    if request.headers['Content-Type'] != 'application/json':
        print(request.headers['Content-Type'])
        return 'Missing values', 400
    
    ctrls = request.json

    ctrls_queued = []
    for key, value in ctrls.items():
        if key == 'power':
            result = ctrl_air.enqueue('p_' + value)
        elif key == 'target_temp':
            result = ctrl_air.enqueue('t_' + str(value))
        elif key == 'wind_amount':
            result = ctrl_air.enqueue('w_' + value)
        else:
            continue

        if result == True:
            ctrls_queued.append({key:value})
        
    if not ctrls_queued:
        return 'Missing values', 400
    
    response = {'message': 'Ctrls are queued.',
                'queued': ctrls_queued}
    return jsonify(response), 201


@app.route('/app/conf', methods=['POST'])
def post_configurations():

    if request.headers['Content-Type'] != 'application/json':
        print(request.headers['Content-Type'])
        return 'Missing values', 400
    
    confs = request.json

    # Check that the required fields are in the POST'ed data
    conf_type = ['alarm_on', 'alarm_time', 'ctrl_on', 'ctrl_temp']
    if not any(k in confs.keys() for k in conf_type):
        return 'Missing values', 400

    confs_previous = conf.get_all_conf()
    for key, value in confs.items():
        conf.set_conf(key=value)
        
    conf.write_conf()

    response = {'message': 'Confs are changed.',
                'confs_previous': confs_previous,
                'confs_now'     : conf.get_all_conf()}
    return jsonify(response), 201



#=========================================
# Initialize and Generate
#=========================================
if __name__ == '__main__':

    # Initialize GPIO, conf, bus, ctrl
    gpio.setwarnings(False)
    gpio.setmode(gpio.BCM)        # Use BCM GPIO numbers
    conf = aaconf.AirAlarmConf()  # Load previous configurations
    bus = smbus.SMBus(1)          # I2C bus shared by devices
    ctrl_air = controller.CtrlAircon()

    # Sensor Initialization
    thermo = bme280.Thermo(bus)
    lumino = tsl2561.Lumino(bus)

    # LCD Initialization
    lcd = raspi_lcd.LCDController(bus, PIN_BACKLIGHT)
    lcd.initialize_display()
    lcd.display_messages(["RasbperryPi Zero", "Air Alarm"])
    time.sleep(1)
    
    if DEBUG:
        print_date_msg("Checking stdout...")
        print_date_err("Checking stderr...")

    # Thread for logging
    tl = threading.Thread(target=log_loop)
    tl.setDaemon(True)
    tl.start()
    
    # Thread for Web API
    tw = threading.Thread(target=webapi_loop)
    tw.setDaemon(True)
    tw.start()
    
    main_loop()
    try:
        main_loop()
    except KeyboardInterrupt:
        if DEBUG: print_date_msg("Keyboard Interrupt")
    finally:
        conf.write_conf()
        bus.close()
        lcd.display_messages(["Goodbye!", ""])
        time.sleep(1)
        gpio.cleanup()
# ================== EOF ==========================
