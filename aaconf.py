#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import os
import json
import copy

DEBUG = True

#=========================================
# Path
#=========================================

CONF_FILE = '/etc/airalarm.conf'     # general configuration file


#=========================================
# print messages with time
#=========================================
def print_date_msg(msg):
    d = datetime.datetime.today()
    print d.strftime('%Y/%m/%d %H:%M:%S') + ' [CONF] ' + msg

#=========================================
# Class to handle configuration files
#=========================================
class AirAlarmConf:
    def __init__(self):
        # Initialize variables
        self.__conf_dict = {'alarm_on'  : 'off',
                            'alarm_time': {'hour': 7, 'minute': 30},
                            'ctrl_on'   : 'off',
                            'ctrl_temp' : 24, # target temp
        }
        self.read_conf()        # Load previous configurations

        self.preset_dict = {'power' : 'on',
                            'target_temp' : self.get_conf('ctrl_temp'),
                            'wind_amount' : 'auto',
        }
        #self.turned_on = True  
        #self.preset_tmp = 


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
            with open(CONF_FILE, 'r') as f:
                temp_dict = json.load(f)                
                if not self.check_conf(temp_dict):
                    raise
                self.__conf_dict = copy.deepcopy(temp_dict)
        except:
            print_date_msg("Read Error: " + CONF_FILE)


    # Write __conf_dict when values are changed
    def write_conf(self):
        
        try:
            with open(CONF_FILE, 'w') as f:
                json.dump(self.__conf_dict, f,
                          ensure_ascii=False, indent=4,
                          sort_keys=True, separators=(',', ': '))
        except:
            print_date_msg("Write Error: " + CONF_FILE)


if __name__ == '__main__':
    conf = AirAlarmConf()

    print('======= Check read_conf() ========')
    print(conf.get_conf('alarm_on', 'alarm_time', 'ctrl_on', 'ctrl_temp'))

    print('====== Check get_conf() ========')
    print(conf.get_conf('alarm_on'))
    print(conf.get_conf('alarm_time'))

    print('====== Check get_str_alarm_time() ========')
    print(conf.get_str_alarm_time())

    print('====== Chech set_conf() ========')
    print(conf.set_conf(alarm_time={'hour':7, 'minute':30}, alarm_on='on', ctrl_temp=24))
    print(conf.get_conf('alarm_on', 'alarm_time', 'ctrl_on', 'ctrl_temp'))

    print('====== Chech write_conf() ========')
    print(conf.write_conf())

    
#================== EOF =========================
