#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import struct
from typing import Any
from time import sleep
from datetime import datetime
from pymodbus.client.sync import ModbusSerialClient

port = 'COM18'
baudrate = 9600
parity = 'N'

class ElectricityMeter(object):
    measurements = {
        'voltage'                           : 0x0000,
        'current'                           : 0x0006,
        'activePower'                       : 0x000C,
        'apparentPower'                     : 0x0012,
        'reactivePower'                     : 0x0018,
        'powerFactor'                       : 0x001E,
        'frequency'                         : 0x0046,
        'importActiveEnergy'                : 0x0048,
        'exportActiveEnergy'                : 0x004A,
        'importReactiveEnergy'              : 0x004C,
        'exportReactiveEnergy'              : 0x004E,
        'totalSystemPowerDemand'            : 0x0054,
        'maximumTotalSystemPowerDemand'     : 0x0056,
        'importSystemPowerDemand'           : 0x0058,
        'maximumImportSystemPowerDemand'    : 0x005A,
        'exportSystemPowerDemand'           : 0x005C,
        'maximumExportSystemPowerDemand'    : 0x005E,
        'currentDemand'                     : 0x0102,
        'maximumCurrentDemand'              : 0x0108,
        'totalActiveEnergy'                 : 0x0156,
        'totalReactiveEnergy'               : 0x0158
    }
    def __init__(self, modbus, address=None) -> None:
        self._modbus = modbus
        self._address = address
        self._common_kwargs = {'unit': self._address} if self._address else {}
        
    def __getattr__(self, __name: str) -> Any:
        if __name in ElectricityMeter.measurements:
            return self._read_float(ElectricityMeter.measurements[__name])
        else:
            raise AttributeError(f'Class ElektricityMeter has no attribute {__name}.')

    def _read_float(self, address):
        return struct.unpack('f', struct.pack('HH', *reversed(self._modbus.read_input_registers(address, 2, **self._common_kwargs).registers)))[0]

    def reset_demands(self, value = 0x0000):
        self._modbus.write_registers(0xF010, [value], **self._common_kwargs)

    @property
    def swVersion(self):
        return self._modbus.read_holding_registers(0xFC03, 1, **self._common_kwargs).registers[0]
    
    @property
    def meterCode(self):
        return self._modbus.read_holding_registers(0xFC02, 1, **self._common_kwargs).registers[0]

    @property
    def serilNumber(self):
        return struct.unpack('L', struct.pack('HH', *reversed(self._modbus.read_holding_registers(0xFC00, 2, **self._common_kwargs).registers)))[0]

def main(argv):
    modbus = ModbusSerialClient('rtu', port=port, baudrate=baudrate, parity=parity)
    if not modbus.connect():
        print(f'Unable to connect to port {port}.')
        return -1
    try:
        meter = ElectricityMeter(modbus, 1)
        print(f'Meter {meter.serilNumber} sw v{meter.swVersion} @ {meter._address or "broadcast"}')
        #meter.reset_demands(0xFFFF)
        while True:
            print(f'{datetime.now():%d.%m.%Y %H:%M:%S.%f}\t{meter.voltage:5.1f} V, {meter.current:5.2f} A, {meter.activePower:6.1f} W, {meter.powerFactor:+5.3f} °, {meter.frequency:5.2f} Hz, {meter.totalActiveEnergy:10.3f} kWh; demand: {meter.currentDemand:5.2f} A, max {meter.maximumCurrentDemand:5.2f} A, {meter.totalSystemPowerDemand:10.3f} W, max {meter.maximumTotalSystemPowerDemand:10.3f} W')
            #sleep(0.1)
    except KeyboardInterrupt:
        print('Exit')
    finally:
        modbus.close()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
