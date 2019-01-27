#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
from datetime import datetime, timedelta
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
import buzzer
import raspi_lcd
import ac
from copy_from_csv import get_connection

# Global variables
DEBUG = False


#=========================================
# Print a message with time
#=========================================
def now_str(short=False):
    if not short:
        return datetime.today().strftime('%Y-%m-%dT%H:%M:%S')
    else:
        return datetime.today().strftime('%H:%M:%S')


def print_date_msg(msg):
    print(now_str() + ' [MAIN] ' + msg)


def print_date_err(msg):
    sys.stderr.write(now_str() + ' [MAIN] ' + msg + '\n')


# #=========================================
# # After the script start, match the actual preset of aircon
# # and the internal variables.
# #=========================================
# def match_preset_variables():
#     ac_ctrl.enqueue('p_on')
#     ac_ctrl.enqueue('t_' + str(acc.get_conf('ctrl_temp')))
#     ac_ctrl.enqueue('w_low')


#============================================
# Display information on LCD (with backlignt)
#============================================
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

        alarm_time = conf.get_str_alarm_time() \
                     if conf.get_conf()['alarm_on'] else '--:-- '

        # Generate strings for LCD
        row1 = ' %02d:%02d:%02d %s' \
               % (time.hour, time.minute, time.second, alarm_time)
        row2 = ' %s %s %s' % (hum_str, tmp_str, prs_str)
        lcd.display_messages([row1, row2])

        # Turn off backlight depending on luminous intensity
        lcd.switch_backlight(values["illuminance"] > self.lux_sw_bl)


#============================================
# Send Ir signals to light
# Task 1. Power on aircon when alarm time
# Task 2. Power off aircon when it is dark
#============================================
class Task_alarm():
    def __init__(self):
        self.th_lux = 50.0    # [Lux]
        self.is_set_buzzer = False

    def alarm(self):
        self.conf_now = conf.get_conf()
        if not self.conf_now['alarm_on']: # 機能がOFF
            return
        # 時刻を比較
        now_m = datetime.today()
        a_time = self.conf_now['alarm_time']
        if now_m.hour == a_time['hour'] and now_m.minute == a_time['minute']:
            self.switch_light()
            self.set_buzzer()
            #print_date_msg("=== Power ON! ===")
            #conf.set_conf(alarm_on=False) # Clear flag
            #conf.write_conf()
        else:
            self.is_set_buzzer = False

    def switch_light(self):
        if sensors.get_values()["illuminance"] <  self.th_lux: # 電気が消えている
            ctrl.send_ir('light', 'switch')
            time.sleep(4) # 照明が付いた状態をセンサーが取得するまで待つ

    def set_buzzer(self):
        if not self.is_set_buzzer:
            buzzer.sound_n_sec(self.conf_now["alarm_window"])
            self.is_set_buzzer = True
            
    # def check_lux(self):
    #     if acc.get_conf('lux_on') == 'off':
    #         return
    #     lumino_value = sensors.get_values()["illuminance"]
    #     # 照明が切れたとき
    #     if lumino_value < self.lux_sw_air and \
    #        self.past_lux >= self.lux_sw_air:
    #         ac_ctrl.enqueue('p_off')
    #     # 照明が付いたとき
    #     elif lumino_value >= self.lux_sw_air and \
    #          self.past_lux < self.lux_sw_air:
    #         #ac_ctrl.enqueue('p_on') # issue: preset temp in AC is reset
    #         self.power_on_set_temp()
    #     self.past_lux = lumino_value

    # def power_on_set_temp(self):
    #     ac_ctrl.enqueue('p_on')
    #     ac_ctrl.enqueue('t_' + str(acc.get_conf('ctrl_temp'))) # work around


#=========================================
# main loop
#=========================================
def main_loop():
    LOOP_DELAY = 0.1
    #match_preset_variables()
    #ac_ctrl.dequeue_all() # execute commands
    task_alarm = Task_alarm()
    task_disp  = Task_disp()
    while True:
        task_alarm.alarm()   # Send ir signal to light
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
                             for key in ["date",
                                         "humidity",
                                         "temperature",
                                         "pressure",
                                         "illuminance"
                                     ]))
                con.commit()

    def write_log(log_file):
        with open(log_file, 'a') as f:
            values = sensors.get_values()
            float2str6 = lambda x: str(x)[0:6]
            line = ','.join([now_str()] + \
                            [float2str6(values[key])
                             for key in ["humidity",
                                         "temperature",
                                         "pressure",
                                         "illuminance"]
                         ]) + '\n'
            f.write(line)

    while True:
        #print_date_msg('logging...') # 出力が多すぎるので抑制
        try:
            insert_log(table_name)
        except:
            write_log(log_file)
        time.sleep(log_delay)



#=========================================
# Web API
#=========================================
app = Flask(__name__)

def webapi_loop(host = '192.168.11.204', port = 80):
    app.run(host=host, port=port)


def return_preset():
    return {'alarm_on' : 'selected' if conf.get_conf()['alarm_on'] else '',
            'alarm_off': 'selected' if not conf.get_conf()['alarm_on'] else '',
            'alarm_time'  : conf.get_str_alarm_time(),
            'alarm_window': conf.get_conf()['alarm_window'],
    }


# index page
@app.route('/app/', methods=['GET', 'POST'])
def index():
    return render_template('index.html',
                           preset=return_preset(),
                           submit=False)


# submit page
@app.route('/app/post', methods=['POST'])
def post():
    try:
        time_list = request.form['alarm_time'].split(':')
        t = conf.set_conf(alarm_on = True if request.form['alarm_sw'] == 'on' else False,
                          alarm_time = {
                              'hour': int(time_list[0]),
                              'minute': int(time_list[1])
                          },
                          alarm_window = int(request.form['alarm_window']),
                      )
        if t:
            conf.write_conf()
        else:
            print_date_err('Missing update of conf')
        return render_template('index.html', preset=return_preset(), submit=True)
    except:
        return redirect(url_for('index'))


# REST API for getting values
@app.route('/app/values', methods=['GET'])
def get_values():
    return jsonify(sensors.get_values()), 200



# REST API for posting the configurations (ex. alarm time)
@app.route('/app/conf', methods=['POST'])
def post_configurations():

    if request.headers['Content-Type'] != 'application/json':
        print(request.headers['Content-Type'])
        return 'Missing content-type', 400
    
    posted_conf   = request.json
    previous_conf = conf.get_conf()
    if conf.set_conf(**posted_conf):
        conf.write_conf()
        response = {'message': 'Confs are changed.',
                    'previous_conf': previous_conf,
                    'now_conf'     : conf.get_conf()
        }
        return jsonify(response), 201
    else:
        return 'Missing values', 400


#=========================================
# Initialize and Generate
#=========================================
if __name__ == '__main__':

    # Initialize GPIO and so on.
    gpio.setwarnings(False)
    gpio.setmode(gpio.BCM)        # Use BCM GPIO numbers
    conf = ac.Configuration()     # Load previous configurations
    ctrl = ac.Controller()
    #mode = Ctrl_PID()
    bus = smbus.SMBus(1)          # I2C bus shared by devices

    # Sensor Initialization
    sensors = Sensors(bus)

    # Buzzer Initializatin
    buzzer = buzzer.Buzzer(buzzer.PIN)

    # LCD Initialization
    lcd = raspi_lcd.LCDController(bus, raspi_lcd.PIN_BACKLIGHT)
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
    #tc = start_thread(ctrl_loop)   # Thread for controller

    main_loop()
    try:
        main_loop()
    except KeyboardInterrupt:
        print_date_msg("Catch Signal")
    finally:
        # 以下終了処理
        conf.write_conf()
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
