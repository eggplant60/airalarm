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
import numpy as np


# Private Library
import bme280
import raspi_lcd
import tsl2561
import ac


# Global variables
DEBUG = False
PIN_BACKLIGHT = raspi_lcd.PIN_BACKLIGHT


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
class Task_disp():
    def __init__(self):
        self.week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        self.lux_sw_bl = 100    # [Lux], BL = Back Light
        
    def update(self):
        d = datetime.datetime.today()
        # Get humidity, tempareture, pressure, lumino
        hum_str = str(thermo.get_hum())[0:4]
        tmp_str = str(thermo.get_tmp())[0:4]
        prs_str = str(thermo.get_prs())[0:4]
        lux_str = str(lumino.get_lux())[0:4]

        if hum_str == '0.0' and tmp_str == '0.0':
            hum_str = '--.-'
            tmp_str = '--.-'

        if acc.get_conf('alarm_on') == 'on':
            alarm_str = '*'
        else:
            alarm_str = ' '
        
        # Generate strings for LCD
        str1 = ' %02d:%02d:%02d %s%s' \
               %(d.hour, d.minute, d.second, \
                 acc.get_str_alarm_time(), alarm_str)
        str2 = ' %s %s %s' \
               %(hum_str, tmp_str, prs_str)
        lcd.display_messages([str1, str2])

        # Turn off backlight depending on luminous intensity
        if lumino.get_lux() > self.lux_sw_bl:
            lcd.switch_backlight(True)
        else:
            lcd.switch_backlight(False)


        
#=========================================
# Send Ir signals to aircon
# Task 1. Power on aircon if it is alarm time
# Task 2. Turn up/down aircon depending on room temparature
# Task 3. Power off aircon if it is dark
#=========================================
class Task_ir():
    def __init__(self):
        self.past_lux = lumino.get_lux()
        self.lux_sw_air = 50    # [Lux]

    def execute(self):
        self.check_alarm()
        self.check_lux()
        ac_ctrl.dequeue_all(n_cmd=2) # execute commands

    def check_alarm(self):
        if acc.get_conf('alarm_on') == 'on':
            d = datetime.datetime.today()
            a_time = acc.get_conf('alarm_time')       
            if d.hour == a_time['hour'] and d.minute == a_time['minute']:
                mode.reset_history() # reset
                ac_ctrl.enqueue('p_on')
                acc.set_conf(alarm_on='off') # Clear flag
                acc.write_conf()
                print_date_msg("=== Power ON! ===")

    # Task 2
    # the commands are queued in ctrl_loop()

    def check_lux(self):
        if lumino.get_lux() < self.lux_sw_air and \
           self.past_lux >= self.lux_sw_air:
            ac_ctrl.enqueue('p_off')
        elif lumino.get_lux() >= self.lux_sw_air and \
             self.past_lux < self.lux_sw_air:
            ac_ctrl.enqueue('p_on')
        self.past_lux = lumino.get_lux()





#=========================================
# main loop
#=========================================
def main_loop():
    LOOP_DELAY = 0.1
    
    # first time, match the actual preset of aircon and the internal variables
    def match_preset_variables():
        ac_ctrl.enqueue('p_on')
        ac_ctrl.enqueue('t_' + str(acc.get_conf('ctrl_temp')))
        ac_ctrl.enqueue('w_low')
        ac_ctrl.dequeue_all() # execute commands

    match_preset_variables()
    task_ir = Task_ir()
    task_disp = Task_disp()
    while True:
        task_ir.execute()    # Send ir signal to aircon
        task_disp.update()   # Display on LCD
        time.sleep(LOOP_DELAY)

        

#=========================================
# logging loop
#=========================================
def log_loop():
    LOG_DELAY = 600
    LOG_FILE = '/home/naoya/airalarm/log.csv'
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
# control loop
#=========================================
def ctrl_loop():
    time.sleep(10) # waiting for starting up devices
    
    while True:
        if acc.get_conf('ctrl_on') == 'on' \
           and ac_ctrl.get_preset()['power'] == 'on':
            #print_date_msg('ctrl starts.')
            mode.update_control()
            
        time.sleep(mode.dt)

        
class Ctrl_PID():
    def __init__(self):
        self.dt = 30
        self.kf = 22.0/23.0 # gain ajustment is needed
        self.kp = 0.8  # over 1.0 is NG
        self.ki = 0.05
        self.kd = 1.2
        self.ek_sum = 0.0
        self.ek_past = 0.0
        self.update_cnt = 0

    def update_control(self):
        rk = acc.get_conf('ctrl_temp')
        yk = thermo.get_tmp()
        ek = rk - yk

        if self.update_cnt % 2 == 1:
            dek = ek - self.ek_past
            uk = self.kf * rk + self.kp * ek \
                 + self.ki * self.ek_sum + self.kd * dek
            uk_clipped = np.clip(int(round(uk)), 18, 30)

            with open('/home/naoya/airalarm/pi.csv', 'a') as f:
                csv_line = datetime.datetime.today().strftime('%H:%M:%S')
                csv_line +=  ', {}, {}, {}, {}, {}, {}, {}\n'.\
                             format(rk,yk,ek,uk,uk_clipped, self.ek_sum, dek)
                f.write(csv_line)

            if uk_clipped != ac_ctrl.get_preset()['target_temp']:
                cmd_str = 't_' + str(uk_clipped)
                ac_ctrl.enqueue(cmd_str)
                print_date_msg('preset: {}'.\
                               format(ac_ctrl.get_preset()['target_temp']))
                
        self.ek_sum += ek
        self.ek_past = ek
        self.update_cnt += 1
        if abs(self.ek_sum) > 100:
            self.reset_history()

    def reset_history(self):
        self.ek_sum = 0.0
        self.ek_past = 0.0

        
class Ctrl_UpDown():
    def __init__(self):
        self.dt = 60
        self.delta_up = 1.0
        self.delta_dn = 0.5

    def update_control(self):
        rk = acc.get_conf('ctrl_temp')
        yk = thermo.get_tmp()
            
        if rk + self.delta_up <= yk:
            uk = np.clip(ac_ctrl.get_preset()['target_temp'] - 1, 18, 30)            
        elif yk + self.delta_dn <= rk:
            uk = np.clip(ac_ctrl.get_preset()['target_temp'] + 1, 18, 30)
        else:
            uk = np.clip(ac_ctrl.get_preset()['target_temp'], 18, 30)

        if uk != ac_ctrl.get_preset()['target_temp']:
            cmd_str = 't_' + str(uk)
            ac_ctrl.enqueue(cmd_str)
            print_date_msg('preset: {}'.format(ac_ctrl.get_preset()['target_temp']))
        
        with open('/home/naoya/airalarm/updown.csv', 'a') as f:
            csv_line = datetime.datetime.today().strftime('%H:%M:%S')
            csv_line +=  ', {}, {}, {}\n'.format(rk, yk, uk)
            f.write(csv_line)
        

#=========================================
# Web API
#=========================================
app = Flask(__name__)

def webapi_loop():
    app.run(host='192.168.11.204', port=80)

    
def sw_initial_value(key, invert=False):
    if not invert:
        return "selected" if acc.get_conf(key) == 'on' else ""
    else:
        return "selected" if acc.get_conf(key) == 'off' else ""

    
def return_preset():
    return {'alarm_sw_on' : sw_initial_value('alarm_on'),
            'alarm_sw_off': sw_initial_value('alarm_on', invert=True),
            'alarm_time'  : acc.get_str_alarm_time(),
            'ctrl_sw_on'  : sw_initial_value('ctrl_on'),
            'ctrl_sw_off' : sw_initial_value('ctrl_on', invert=True),
            'ctrl_temp'   : acc.get_conf('ctrl_temp')
    }


# index page
@app.route('/app/', methods=['GET', 'POST'])
def index():
    return render_template('index.html', preset=return_preset(), submit=False)


# submit page
@app.route('/app/post', methods=['POST'])
def post():
    try:
        time_list = request.form['alarm_time'].split(':')
        t = acc.set_conf(alarm_on=request.form['alarm_sw'],
                         alarm_time={
                             'hour': int(time_list[0]),
                             'minute': int(time_list[1])
                         },
                         ctrl_on=request.form['ctrl_sw'],
                         ctrl_temp=int(request.form['ctrl_temp'])
        )
        if t:
            acc.write_conf()
        else:
            print_date_err('Missing update of conf')
        return render_template('index.html', preset=return_preset(), submit=True)

    except:
        return redirect(url_for('index'))


# REST API for getting values
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


# REST API for getting preset of aircon
@app.route('/app/preset', methods=['GET'])
def get_preset():
    return jsonify(ac_ctrl.get_preset()), 200


# REST API for posting commands to aircon directly
@app.route('/app/ctrl', methods=['POST'])
def post_ctrl():

    if request.headers['Content-Type'] != 'application/json':
        print(request.headers['Content-Type'])
        return 'Missing values', 400
    
    ctrls = request.json

    ctrls_queued = []
    for key, value in ctrls.items():
        if key == 'power':
            result = ac_ctrl.enqueue('p_' + value)
        elif key == 'target_temp':
            result = ac_ctrl.enqueue('t_' + str(value))
        elif key == 'wind_amount':
            result = ac_ctrl.enqueue('w_' + value)
        else:
            continue

        if result == True:
            ctrls_queued.append({key:value})
            ac_ctrl.get_preset()[key] = value
        
    if not ctrls_queued:
        return 'Missing values', 400
    
    response = {'message': 'Ctrls are queued.',
                'queued': ctrls_queued}
    return jsonify(response), 201


# REST API for posting the configurations (ex. alarm time)
@app.route('/app/conf', methods=['POST'])
def post_configurations():

    if request.headers['Content-Type'] != 'application/json':
        print(request.headers['Content-Type'])
        return 'Missing values', 400
    
    posted_confs = request.json

    # Check that the required fields are in the POST'ed data
    conf_type = ['alarm_on', 'alarm_time', 'ctrl_on', 'ctrl_temp']
    if not any(k in posted_confs.keys() for k in conf_type):
        return 'Missing values', 400

    confs_previous = acc.get_all_conf()
    for key, value in posted_confs.items():
        acc.set_conf(key=value)
        
    acc.write_conf()

    response = {'message': 'Confs are changed.',
                'confs_previous': confs_previous,
                'confs_now'     : acc.get_all_conf()}
    return jsonify(response), 201



#=========================================
# Initialize and Generate
#=========================================
if __name__ == '__main__':

    # Initialize GPIO and so on.
    gpio.setwarnings(False)
    gpio.setmode(gpio.BCM)        # Use BCM GPIO numbers
    acc = ac.AlarmCtrlConf()      # Load previous configurations
    ac_ctrl = ac.Controller()
    mode = Ctrl_PID()
    bus = smbus.SMBus(1)          # I2C bus shared by devices

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

    # Thread for controller
    tc = threading.Thread(target=ctrl_loop)
    tc.setDaemon(True)
    tc.start()

    main_loop()
    try:
        main_loop()
    except KeyboardInterrupt:
        if DEBUG: print_date_msg("Keyboard Interrupt")
    finally:
        acc.write_conf()
        bus.close()
        lcd.display_messages(["Goodbye!", ""])
        time.sleep(1)
        gpio.cleanup()
# ================== EOF ==========================
