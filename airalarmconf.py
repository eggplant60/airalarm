#!/usr/bin/python
# -*- coding: utf-8 -*-

import datetime
import os

ADEBUG = True

#=========================================
# Path
#=========================================
CONF_FILE = '/etc/airalarm.conf'     # general configuration file
CGI_UPDATE = '/tmp/cgi_update.tmp'   # temporary file created after update of conf

#=========================================
# Class of (single) configuration parameter
#=========================================
# class ConfItem:
#     def __init__(self, _name, _onoff, _value):
#         self.name = _name
#         self.onoff = _onoff
#         self.value = _value
#
#     def str2Value(self):
#         return
#
#     def returnLine(self):
#         return

#=========================================
# Class to handle configuration files
#=========================================
class AirAlarmConf:
    def __init__(self):
        # Initialize variables
        self.alarmOn = False
        self.alarmTime = datetime.datetime(2017,1,1,7,0,0)
        self.ctrlOn = False
        self.ctrlTemp = 20
        self.dispOn = False # Backlight
        self.dispMode = "ALARM"
        #
        self.aircon_on = False  # True if aircon turns on
        self.readConf()

    # Executed in initailization of airalrm.py and in CGI script
    def readConf(self):
        onoff2b = lambda s: True if s == "ON" else False
        try:
            with open(CONF_FILE, 'r') as csvf:
                for line in csvf.readlines():
                    tmp = line.rstrip('\n')     # get rid of return code
                    str_list = tmp.split(',')   # Convert CSV form into list
                    if ADEBUG: print str_list

                    if str_list[0] == "ALARM":
                        self.alarmOn = onoff2b(str_list[1])
                        self.alarmTime = datetime.datetime.strptime(str_list[2], '%H:%M')
                    elif str_list[0] == "CTRL":
                        self.ctrlOn = onoff2b(str_list[1])
                        self.ctrlTemp = int(str_list[2])
                    elif str_list[0] == "DISP":
                        self.dispOn = onoff2b(str_list[1])
                        self.dispMode = str_list[2]
        except:
            print "Read Error: " + CONF_FILE

    # check temporary file created by CGI and read conf
    def checkReadConf(self):
        if os.path.exists(CGI_UPDATE):
            if ADEBUG: print "Conf is updated by CGI, reading..."
            self.readConf()
            os.remove(CGI_UPDATE)  # clear flag

    # Write configuration file
    # This method should be called in CGI
    def writeConf(self):
        b2onoff = lambda b: "ON" if b else "OFF"
        try:
            with open(CONF_FILE, 'w') as csvf:
                body = "ALARM," + b2onoff(self.alarmOn) + ',' \
                    + self.alarmTime.strftime('%H:%M') + '\n' \
                    + "CTRL," + b2onoff(self.ctrlOn) + ',' \
                    + str(self.ctrlTemp) + '\n' \
                    + "DISP," + b2onoff(self.dispOn) + ',' \
                    + str(self.dispMode)
                csvf.write(body)
        except:
            print "Write Error: " + CONF_FILE
        try:
            with open(CGI_UPDATE, 'w') as wf:
                if ADEBUG: print "CGI_UPDATE is created by CGI"
        except:
            print "Permission Error: " + CGI_UPDATE
#================== EOF =========================
