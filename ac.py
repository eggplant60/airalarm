#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import datetime
import json
import copy

DEBUG = False

#=========================================
# Print a message with time
#=========================================
def print_date_msg(msg):
    d = datetime.datetime.today()
    print d.strftime('%Y/%m/%d %H:%M:%S') + ' [AC  ] ' + msg


#=========================================
# Class to send signals to the AC
#=========================================
class Controller():

    def  __init__(self):
        self.work_dir = '/home/naoya/airalarm/ir'   
        self.__preset_dict = {'power' : 'on',
                              'target_temp' : 25,
                              'wind_amount' : 'low',
        }
        self.dict_cmd = {}
        for cmd in os.listdir(os.path.join(self.work_dir, 'data')):
            self.dict_cmd[cmd] = './send.sh data/{} > /dev/null'.format(cmd)   
        self.queue = []

    def get_preset(self):
        return self.__preset_dict
        
    def enqueue(self, cmd):
        try:
            self.queue.append(self.dict_cmd[cmd])
            if cmd[:2] == 'p_':
                self.__preset_dict['power'] = cmd[2:]
                if DEBUG: print(self.__preset_dict['power'])
            elif cmd[:2] == 't_':
                self.__preset_dict['target_temp'] = int(cmd[2:])
                if DEBUG: print(self.__preset_dict['target_temp'])
            elif cmd[:2] == 'w_':
                self.__preset_dict['wind_amount'] = cmd[2:]
                if DEBUG: print(self.__preset_dict['wind_amount'])
            ret = True
            
        except:
            print_date_msg('This command does not exist.')
            ret = False
        return ret
            
    def dequeue_all(self, n_cmd=2):
        while self.queue:
            cmd = self.queue.pop(0)
            self.send_ir(cmd, n_cmd)
            print_date_msg('{} will be executed...'.format(cmd))
            
    def send_ir(self, cmd, n_cmd):
        for _ in range(n_cmd):
            time.sleep(0.5)
            subprocess.call(cmd, shell=True, cwd=self.work_dir)



#=========================================
# Class to handle configuration files
#=========================================
class AlarmCtrlConf:
    def __init__(self):
        self.conf_file = '/etc/airalarm.conf'     # general configuration file
        # Initialize variables

        self.__conf_dict = {'alarm_on'  : 'off',
                            'alarm_time': {'hour': 7, 'minute': 30},
                            'ctrl_on'   : 'off',
                            'ctrl_temp' : 24, # target temp
        }
        self.read_conf()        # Load previous configurations

    # Usage: v1, v2, ... = get_conf('key1', 'key2', ...)
    def get_conf(self, *keys):
        ret_list = []
        for key in keys:
            try:
                ret_list.append(self.__conf_dict[key])
            except:
                print_date_msg('Missing keys.')
                return None

        if len(ret_list) == 1:
            return ret_list[0]
        else:
            return ret_list

    # Return Example: "08:00"
    def get_str_alarm_time(self):
        hour_str = str(self.__conf_dict['alarm_time']['hour']).zfill(2)
        minute_str = str(self.__conf_dict['alarm_time']['minute']).zfill(2)
        return hour_str + ':' + minute_str
    
    def get_all_conf(self):
        return self.__conf_dict

    # Usage: get_conf(key1=value1, key2=value2, ...)
    def set_conf(self, **kwargs):
        temp_dict = copy.deepcopy(self.__conf_dict)
        try:
            for key, value in kwargs.items():
                temp_dict[key] = value
        except:
            return False

        if not self.check_conf(temp_dict):
            return False

        self.__conf_dict = copy.deepcopy(temp_dict)
        return True

    # Check if args are valid
    def check_conf(self, dict_a):
        if len(dict_a) != 4:
            return False

        if dict_a['alarm_on'] != 'on' and dict_a['alarm_on'] != 'off':
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

        if dict_a['ctrl_on'] != 'on' and dict_a['ctrl_on'] != 'off':
            return False

        if isinstance(dict_a['ctrl_temp'], int) and \
           18 <= dict_a['ctrl_temp'] <= 30:
            pass
        else:
            return False

        return True
                 
    # Load previous __conf_dict at start up
    def read_conf(self):
        try:
            with open(self.conf_file, 'r') as f:
                temp_dict = json.load(f)                
                if not self.check_conf(temp_dict):
                    raise
                self.__conf_dict = copy.deepcopy(temp_dict)
        except:
            print_date_msg("Read Error: " + self.conf_file)

    # Write __conf_dict when values are changed
    def write_conf(self):
        
        try:
            with open(self.conf_file, 'w') as f:
                json.dump(self.__conf_dict, f,
                          ensure_ascii=False, indent=4,
                          sort_keys=True, separators=(',', ': '))
        except:
            print_date_msg("Write Error: " + self.conf_file)



if __name__ == '__main__':
    acc = AlarmCtrlConf()
    ac_ctrl = Controller()

    print('======= Class AlarmCtrlConf ======')
    print('1. Check read_conf()')
    print(acc.get_conf('alarm_on', 'alarm_time', 'ctrl_on', 'ctrl_temp'))

    print('2. Check get_conf()')
    print(acc.get_conf('alarm_on'))
    print(acc.get_conf('alarm_time'))

    print('3. Check get_str_alarm_time()')
    print(acc.get_str_alarm_time())

    print('4. Chech set_conf()')
    print(acc.set_conf(alarm_time={'hour':7, 'minute':30}, alarm_on='on', ctrl_temp=24))
    print(acc.get_conf('alarm_on', 'alarm_time', 'ctrl_on', 'ctrl_temp'))

    # print('5. Chech write_conf()')
    # print(acc.write_conf())

    print('======= Class Controller ======')
    print(ac_ctrl.get_preset())
    ac_ctrl.enqueue('p_on')
    ac_ctrl.enqueue('p_a')
    ac_ctrl.enqueue('w_high')
    print(ac_ctrl.get_preset())
    ac_ctrl.dequeue_all()
    
    
#================== EOF =========================
