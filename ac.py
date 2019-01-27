#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import datetime
import json
import copy

DEBUG = True

#=========================================
# Print a message with time
#=========================================
def print_date_msg(msg):
    if DEBUG:
        d = datetime.datetime.today()
        print d.strftime('%Y/%m/%d %H:%M:%S') + ' [AC  ] ' + msg


#=========================================
# Class to send signals to AC or Light
#=========================================
class Controller():

    def  __init__(self):
        self.command_str = '/usr/bin/irsend -#{} SEND_ONCE {} {}'

    def send_ir(self, target, command, n=1):
        cmd = self.command_str.format(n, target, command)
        try:
            subprocess.call(cmd, shell=True)
            print_date_msg('executed'.format(cmd))
        except:
            print_date_msg('Error: {}'.format(cmd))



#=========================================
# Class to handle configuration files
#=========================================
class Configuration():
    def __init__(self):
        self.conf_file = '/etc/airalarm.conf'     # general configuration file
        self.default_values = {"alarm_on": False,
                               "alarm_time": {
                                   "hour": 7,
                                   "minute": 30
                               },
                               "alarm_window": 30
                           }
        self.conf_values = self.read_conf() # Load previous configurations

    def read_conf(self):
        try:
            with open(self.conf_file, 'r') as f:
                conf_values = json.load(f)
                if self.is_valid_values(conf_values):
                    return conf_values
                else:
                    print_date_msg("Invalid values")
                    return self.defalut_values
        except:
            print_date_msg("Read Error: " + self.conf_file)
            return self.default_values

    def write_conf(self):
        try:
            with open(self.conf_file, 'w') as f:
                json.dump(self.conf_values, f,
                          ensure_ascii=False, indent=4,
                          sort_keys=True, separators=(',', ': '))
                return True
        except:
            print_date_msg("Write Error: " + self.conf_file)
            return False

    def get_conf(self):
        return self.conf_values

    def set_conf(self, **kargs):
        tmp_values = copy.deepcopy(self.conf_values)
        for key, value in kargs.items():
            tmp_values[key] = value
        is_valid = self.is_valid_values(tmp_values)
        print(tmp_values)
        if is_valid:
            self.conf_values = tmp_values
            return True
        else:
            return False

    # Check if args are valid
    def is_valid_values(self, dict_a):
        if len(dict_a) != 3:
            return False

        if not isinstance(dict_a['alarm_on'], bool):
            return False

        if isinstance(dict_a['alarm_time']['hour'], int) and \
           0 <= dict_a['alarm_time']['hour'] <= 23:
            pass
        else:
            return False

        if isinstance(dict_a['alarm_time']['minute'], int) and \
           0 <= dict_a['alarm_time']['minute'] <= 59:
            pass
        else:
            return False

        if isinstance(dict_a['alarm_window'], int) and \
           0 <= dict_a['alarm_window'] <= 59:
            pass
        else:
            return False

        return True

    # Return Example: "08:00"
    def get_str_alarm_time(self):
        tmp_time = self.conf_values['alarm_time']
        hour_str = str(tmp_time['hour']).zfill(2)
        minute_str = str(tmp_time['minute']).zfill(2)
        return hour_str + ':' + minute_str



if __name__ == '__main__':
    conf = Configuration()
    ctrl = Controller()

    print('======= Class Configuration ======')
    print('1. Check get_conf()')
    print(conf.get_conf())
    print('')

    print('2. Check get_str_alarm_time()')
    print(conf.get_str_alarm_time())
    print('')

    print('3. Chech set_conf()')
    print(conf.set_conf(alarm_time={'hour':11, 'minute':00}, alarm_window=5))
    print(conf.get_conf())
    print('')

    print('5. Chech write_conf()')
    print(conf.write_conf())
    print('')

    print('======= Class Controller ======')
    ctrl.send_ir('light', 'switch')
    # print(ctrl.get_preset())
    # ctrl.enqueue('p_on')
    # ctrl.enqueue('p_a')
    # ctrl.enqueue('w_high')
    # print(ac_ctrl.get_preset())
    #ac_ctrl.dequeue_all()

#================== EOF =========================
