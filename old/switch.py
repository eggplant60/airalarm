#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import threading
import RPi.GPIO as GPIO

DEBUG_MODE = False
SW_PIN = 20
#
E_EDGE_BIT = 0x01
R_EDGE_BIT = 0x02
F_EDGE_BIT = 0x04
#
L_PRESS_BIT = 0x01
L_PRESS_CNT_MAX = 30
#
POLLING_INT = 0.05


class Switch():
    def __init__(self, PIN):
        # Set GPIO pin input and pull-down
        GPIO.setup(PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        # Generate Thread and Flag
        self.sw_event = threading.Event()
        self.stop_event = threading.Event()
        self.running_flag = threading.Event()
        self.thread = threading.Thread(target = self.run)

        # Initialize Variable
        self.__pin = PIN
        self.__status = False
        self.__edgeFlag = 0x00
        self.__longFlag = 0x00
        self.__longPressCnt = 0

        # Start
        self.running_flag.set()
        self.thread.start()

    def getEdgeFlag(self):
        return  self.__edgeFlag

    def clearEdgeFlag(self):
        self.__edgeFlag = 0x00

    def getLongFlag(self):
        return  self.__longFlag

    def clearLongFlag(self):
        self.__longFlag = 0x00
        self.__longPressCnt = 0

    def run(self):
        while not self.stop_event.is_set():

            self.running_flag.wait()
            tmp_status = GPIO.input(self.__pin)

            # Rising Edge
            if  tmp_status == True and self.__status == False:
                self.__edgeFlag |= (E_EDGE_BIT | R_EDGE_BIT)
                self.__longPressCnt = 0
                self.sw_event.set()

            # Falling Edge
            elif tmp_status == False and self.__status == True:
                self.__edgeFlag |= (E_EDGE_BIT | F_EDGE_BIT)
                self.__longPressCnt = 0
                self.sw_event.set()

            # Continuous High
            elif tmp_status == True and self.__status == True:
                self.__longPressCnt += 1
                if self.__longPressCnt == L_PRESS_CNT_MAX: # only first time
                    self.__longFlag |= (L_PRESS_BIT)
                    self.sw_event.set()
                    self.__longPressCnt = 0

            # Continuous Lown
            elif tmp_status == False and self.__status == False:
                self.__longPressCnt = 0

            self.__status = tmp_status # Update Switch Status
            time.sleep(POLLING_INT)

        if DEBUG_MODE:
            print " break run loop"

    def stop(self):
        if DEBUG_MODE:
            print "Stop Thread"

        self.stop_event.set()
        self.thread.join()

    def suspend(self):
        self.running_flag.clear()

    def resume(self):
        self.running_flag.set()



def main_loop():

    while True:
        if s1.sw_event.is_set():
            print "----------------------"
            print "E: " + str(s1.getEdgeFlag() & E_EDGE_BIT)
            print "R: " + str(s1.getEdgeFlag() & R_EDGE_BIT)
            print "F: " + str(s1.getEdgeFlag() & F_EDGE_BIT)
            print "L: " + str(s1.getLongFlag() & L_PRESS_BIT)
            s1.clearEdgeFlag()
            s1.clearLongFlag()
            s1.sw_event.clear()

        time.sleep(0.1)


if __name__ == '__main__':

    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)       # Use BCM GPIO numbers

    s1 = Switch(SW_PIN)

    try:
        main_loop()
    except KeyboardInterrupt:
        print "Keyboard Interrupt"
    finally:
        s1.stop()
        GPIO.cleanup()
        print "Good Bye!"
