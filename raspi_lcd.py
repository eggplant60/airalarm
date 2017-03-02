#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys
import time
import smbus
import unicodedata
import datetime

from character_table import INITIALIZE_CODES, LINEBREAK_CODE, RETURNHOME_CODE, CHAR_TABLE

LCD_WIDTH = 16
COMMAND_ADDR = 0x00
DATA_ADDR = 0x80
BUS_NUMBER = 1    # LCD Bus Number (Default: 1)
LCD_ADDR = 0x50   # LCD Address (Default: 0x50)
SLEEP_TIME = 0.01 # Sleep time after initializing display(sec)
DELAY_TIME1 = 0.001 # Delay time between characters(sec)
DELAY_TIME2 = 0.005 # Delay time after return home(sec)

#=========================================
# print messages with time
#=========================================
#def printDateMsg(msg):
#    d = datetime.datetime.today()
#    print d.strftime('%Y/%m/%d %H:%M:%S') + ' [LCDC] ' + msg


class LCDController:
    def __init__(self):
        self.bus = smbus.SMBus(BUS_NUMBER)
        pass

    def send_command(self, command, is_data=True):
        if is_data:
            self.bus.write_i2c_block_data(LCD_ADDR, DATA_ADDR, [command])
        else:
            self.bus.write_i2c_block_data(LCD_ADDR, COMMAND_ADDR, [command])
        time.sleep(DELAY_TIME1)

    def initialize_display(self):
        for code in INITIALIZE_CODES:
            self.send_command(code, is_data=False)

    def send_linebreak(self):
        for code in LINEBREAK_CODE:
            self.send_command(code, is_data=False)

    def send_returnhome(self):
        for code in RETURNHOME_CODE:
            self.send_command(code, is_data=False)

    def normalize_message(self, message):
        if isinstance(message, str):
            message = message.decode('utf-8')
        return unicodedata.normalize('NFKC', message)

    def convert_message(self, message):
        char_code_list = []
        for char in message:
            if char not in CHAR_TABLE:
                error_message = 'undefined character: %s' % (char.encode('utf-8'))
                #printDateMsg(error_message)
                raise ValueError(error_message)
            char_code_list += CHAR_TABLE[char]
        if len(char_code_list) > 16:
            #printDateMsg('Exceeds maximum length of characters for each line: 16')
            raise ValueError('Exceeds maximum length of characters for each line: 16')
        return char_code_list

    def display_one_line(self, message):
        message = self.normalize_message(message)
        message = message.ljust(LCD_WIDTH, " ")
        char_code_list = self.convert_message(message)
        for code in char_code_list:
            self.send_command(code)

    def display_messages(self, message_list):
        #self.initialize_display()
        self.send_returnhome()
        time.sleep(DELAY_TIME2)
        for line_no, message in enumerate(message_list):
            if line_no == 1:
                self.send_linebreak()
            self.display_one_line(message)


def main():
    if not 2 <= len(sys.argv) <= 3:
        print('Usage: python raspi_lcd.py "message for line 1" ["message for line 2"]')
        return
    else:
        lcd = LCDController()
        lcd.initialize_display()
        lcd.display_messages(sys.argv[1:3])
        #lcd.display_one_line(1, sys.argv[1])
        #lcd.display_one_line(2, sys.argv[2])

if __name__ == '__main__':
    main()
