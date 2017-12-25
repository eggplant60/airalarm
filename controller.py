#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import datetime


#=========================================
# Print a message with time
#=========================================
def print_date_msg(msg):
    d = datetime.datetime.today()
    print d.strftime('%Y/%m/%d %H:%M:%S') + ' [CTRL] ' + msg


class CtrlAircon():

   def  __init__(self):
      self.work_dir = '/home/naoya/airalarm/ir'   
      self.dict_cmd = {}
      for cmd in os.listdir(os.path.join(self.work_dir, 'data')):
         self.dict_cmd[cmd] = './send.sh data/{}  > /dev/null'.format(cmd)
      
      self.queue = []

      
   def send_ir(self, cmd):
      time.sleep(0.5)
      subprocess.call(cmd, shell=True, cwd=self.work_dir)
      time.sleep(0.5)
      subprocess.call(cmd, shell=True, cwd=self.work_dir)
      time.sleep(0.5)
      subprocess.call(cmd, shell=True, cwd=self.work_dir)
      
      
   def enqueue(self, cmd):
      try:
         self.queue.append(self.dict_cmd[cmd])
         ret = True
      except:
         print_date_msg('This command does not exist.')
         ret = False
      return ret
   
         
   def dequeue_all(self):
      while self.queue:
         cmd = self.queue.pop(0)
         self.send_ir(cmd)
         print_date_msg('{} are executed.'.format(cmd))
