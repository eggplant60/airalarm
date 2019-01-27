#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import RPi.GPIO as GPIO
import threading

PIN = 21
DEBUG = False

class Buzzer:
    def __init__(self, pin):
        self.pin = pin
        self.is_sound = False
        GPIO.setup(self.pin, GPIO.OUT)

    def sound_n_sec(self, sec):
        # 既に起動中なら処理しない
        if self.is_sound:
            return
        self.t_sec = threading.Thread(target=self.sound_n_sec_base, args=(sec,))
        self.t_sec.setDaemon(True)
        self.t_sec.start()

    def sound_n_sec_base(self, sec):
        self.sound_duty()
        time.sleep(sec)
        self.stop()

    def sound_duty(self):
        self.t_duty = threading.Thread(target=self.sound_duty_base)
        self.t_duty.setDaemon(True)
        self.t_duty.start()

    def sound_duty_base(self, duty=0.5, interval=0.2):
        on_time  = duty * interval
        off_time = (1.0-duty) * interval
        self.is_sound = True
        while self.is_sound:
            GPIO.output(self.pin, True)
            time.sleep(on_time)
            GPIO.output(self.pin, False)
            time.sleep(off_time)

    def stop(self):
        self.is_sound = False
        GPIO.output(self.pin, False)


def main():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)       # Use BCM GPIO numbers

    buzzer = Buzzer(PIN)
    for i in range(2):
        buzzer.sound_n_sec(2)
        print('Start Thread %d' % i)
        time.sleep(1)

    time.sleep(3)
    GPIO.cleanup()


if __name__ == '__main__':
    main()
