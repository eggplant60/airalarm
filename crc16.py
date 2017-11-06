#!/bin/python
#import numpy as np

def crc16(data):
    '''
    CRC-16-CCITT Algorithm
    '''
    data = bytearray(data)
    poly = 0xA001
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(0, 8):
            if (crc & 0x01):
                crc = (crc >> 1) ^ poly
            else:
                crc >>= 1
    return crc

if __name__ == '__main__':
    data = [3, 4, 1, 112, 0, 238]
    print(data)
    #print(crc16(b'\x03\x04\x01\xF4\x00\xFA'))
    #print(crc16(b'\x10\x10\x02\x01\x02'))
    crc = crc16(data)

    print('hex: ' + hex(crc))
    print('[%d, %d]' % (crc & 0xFF, crc >> 8))

