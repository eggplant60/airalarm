#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import datetime
import sys
import threading
#import signal

import RPi.GPIO as gpio
import smbus
from flask import Flask, jsonify, request, render_template
import numpy as np
import psycopg2   # handle PostgreSQL

# Private Library
from sensors import Sensors
import raspi_lcd
import ac
from copy_from_csv import get_connection

# Global variables
DEBUG = False
PIN_BACKLIGHT = raspi_lcd.PIN_BACKLIGHT


#=========================================
# Print a message with time
#=========================================
def now_str(short=False):
    if not short:
        return datetime.datetime.today().strftime('%Y-%m-%dT%H:%M:%S')
    else:
        return datetime.datetime.today().strftime('%H:%M:%S')


def print_date_msg(msg):
    print(now_str() + ' [MAIN] ' + msg)


def print_date_err(msg):
    sys.stderr.write(now_str() + ' [MAIN] ' + msg + '\n')


#=========================================
# After the script start, match the actual preset of aircon
# and the internal variables.
#=========================================
def match_preset_variables():
    ac_ctrl.enqueue('p_on')
    ac_ctrl.enqueue('t_' + str(acc.get_conf('ctrl_temp')))
    ac_ctrl.enqueue('w_low')


#=========================================
# Display information on LCD, and control its backlignt
#=========================================
class Task_disp():
    def __init__(self):
        self.week = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        self.lux_sw_bl = 50.0    # [Lux], BL = Back Light

    def float2str4(self, value):
        if value == 0.0:
            return '--.-'
        else:
            return str(value)[0:4]

    def update(self):
        # Get datetime, humidity, temperature, pressure, illuminance
        values = sensors.get_values()
        time    = values["date"]
        hum_str, tmp_str, prs_str, lux_str = (self.float2str4(values[key]) \
                                              for key in ["humidity",
                                                          "temperature",
                                                          "pressure",
                                                          "illuminance"])

        alarm_str = '*' if acc.get_conf('alarm_on') == 'on' else ' '

        # Generate strings for LCD
        row1 = ' %02d:%02d:%02d %s%s' \
               % (time.hour, time.minute, time.second, \
                  acc.get_str_alarm_time(), alarm_str)
        row2 = ' %s %s %s' % (hum_str, tmp_str, prs_str)
        lcd.display_messages([row1, row2])

        # Turn off backlight depending on luminous intensity
        lcd.switch_backlight(values["illuminance"] > self.lux_sw_bl)


#=========================================
# Send Ir signals to aircon
# Task 1. Power on aircon if it is alarm time
# Task 2. Power off aircon if it is dark
#=========================================
class Task_ir():
    def __init__(self):
        self.past_lux = sensors.get_values()["illuminance"]
        self.lux_sw_air = 50.0    # [Lux]

    def execute(self):
        self.check_alarm()
        self.check_lux()
        ac_ctrl.dequeue_all(n_cmd=2) # execute commands

    def check_alarm(self):
        if acc.get_conf('alarm_on') == 'off':
            return
        d = datetime.datetime.today()
        a_time = acc.get_conf('alarm_time')
        if d.hour == a_time['hour'] and d.minute == a_time['minute']:
            mode.reset_history() # reset
            #ac_ctrl.enqueue('p_on')
            self.power_on_set_temp()
            acc.set_conf(alarm_on='off') # Clear flag
            acc.write_conf()
            print_date_msg("=== Power ON! ===")


    def check_lux(self):
        if acc.get_conf('lux_on') == 'off':
            return

        lumino_value = sensors.get_values()["illuminance"]
        # 照明が切れたとき
        if lumino_value < self.lux_sw_air and \
           self.past_lux >= self.lux_sw_air:
            ac_ctrl.enqueue('p_off')
        # 照明が付いたとき
        elif lumino_value >= self.lux_sw_air and \
             self.past_lux < self.lux_sw_air:
            #ac_ctrl.enqueue('p_on') # issue: preset temp in AC is reset
            self.power_on_set_temp()
        self.past_lux = lumino_value

    def power_on_set_temp(self):
        ac_ctrl.enqueue('p_on')
        ac_ctrl.enqueue('t_' + str(acc.get_conf('ctrl_temp'))) # work around


#=========================================
# main loop
#=========================================
def main_loop():
    LOOP_DELAY = 0.1
    match_preset_variables()
    ac_ctrl.dequeue_all() # execute commands
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
    log_delay = 600
    log_file  = '/home/naoya/airalarm/log.csv' # DBに登録できなかったときの予備
    table_name = 'environment'
    time.sleep(10) # waiting for starting up devices

    def insert_log(table_name):
        with get_connection() as con:
            with con.cursor() as cur:
                sql = "INSERT INTO " + table_name + \
                      """ (date,humidity,temperature,pressure,illuminance) 
                          VALUES(%s, %s, %s, %s, %s)"""
                values = sensors.get_values()
                cur.execute(sql,
                            (values[key]
                             for key in ["date", "humidity", "temperature", "pressure", "illuminance"])
                )
                con.commit()

    def write_log(log_file):
        with open(log_file, 'a') as f:
            values = sensors.get_values()
            float2str6 = lambda x: str(x)[0:6]
            line = ','.join([now_str()] + \
                            [float2str6(values[key])
                             for key in ["humidity", "temperature", "pressure", "illuminance"]]
                            ) + '\n'
            f.write(line)

    while True:
        #print_date_msg('logging...') # 出力が多すぎるので抑制
        try:
            insert_log(table_name)
        except:
            write_log(log_file)
        time.sleep(log_delay)


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

            with open('/home/naoya/airalarm/pid.csv', 'a') as f:
                csv_line = now_str(short=True)
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
            'ctrl_temp'   : acc.get_conf('ctrl_temp'),
            'lux_sw_on'  : sw_initial_value('lux_on'),
            'lux_sw_off' : sw_initial_value('lux_on', invert=True),
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
                         ctrl_temp=int(request.form['ctrl_temp']),
                         lux_on=request.form['lux_sw'],
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
    return jsonify(sensors.get_values()), 200


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
    conf_type = ['alarm_on', 'alarm_time', 'ctrl_on', 'ctrl_temp', 'lux_on']
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
    sensors = Sensors(bus)

    # LCD Initialization
    lcd = raspi_lcd.LCDController(bus, PIN_BACKLIGHT)
    lcd.initialize_display()
    lcd.display_messages(["RaspberryPi Zero", "   Air Alarm"])
    time.sleep(1)

    def start_thread(target):
        t = threading.Thread(target=target)
        t.setDaemon(True)
        t.start()
        return t

    # 以下の処理はデーモン化されており、エラーを吐いても全体の処理は止まらない
    # デーモンスレッドのみになったときは自動で終了する
    tl = start_thread(log_loop)    # Thread for logging
    tw = start_thread(webapi_loop) # Thread for Web API
    tc = start_thread(ctrl_loop)   # Thread for controller

    try:
        main_loop()
    except KeyboardInterrupt:
        print_date_msg("Catch Signal")
    finally:
        # 以下終了処理
        acc.write_conf()
        lcd.display_messages(["Goodbye!", ""])
        time.sleep(1)
        bus.close()
        gpio.cleanup()
        print_date_msg("Terminal Process is Complete.")
        print_date_err("Terminal Process is Complete.")
        sys.exit(0)

    #signal.signal(signal.SIGTERM, signal_handler)
    #signal.signal(signal.SIGINT,  signal_handler)
# ================== EOF ==========================
