#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from typing import Any
from datetime import datetime
import sdm_modbus

port = 'COM18'
baudrate = 9600
parity = 'N'

class MeterReader(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
    
    def __getattr__(self, __name: str) -> Any:
        if __name in self.registers:
            return self.read(__name)
        else:
            raise AttributeError(f'Class {self.__class__.__name__} has no attribute {__name}.')

class SDM120(sdm_modbus.SDM120, MeterReader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registers |= {
            "serial_number": (0xFC00, 2, sdm_modbus.meter.registerType.HOLDING, sdm_modbus.meter.registerDataType.UINT32, int, "Serial number", "", 1, 1),
            "meter_code": (0xFC02, 1, sdm_modbus.meter.registerType.HOLDING, sdm_modbus.meter.registerDataType.INT16, int, "Meter code", "", 1, 1), # dtype should be UINT16, but it is not implemented in sdm_modbus package yet
            "software_version": (0xFC02, 1, sdm_modbus.meter.registerType.HOLDING, sdm_modbus.meter.registerDataType.INT16, int, "Software version", "", 1, 1), # dtype should be UINT16, but it is not implemented in sdm_modbus package yet
        }

class SDM72(sdm_modbus.SDM72, MeterReader):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def main(argv):
    modbus = sdm_modbus.Meter(device=port, baud=baudrate, parity=parity)
    if not modbus.connect():
        print(f'Unable to connect to port {port}.')
        return -1
    try:
        meters = {
            'front_flat' : SDM120(parent=modbus, unit=1),
            'rear_flat'  : SDM120(parent=modbus, unit=2),
            #'workroom'   : SDM72 (parent=modbus, unit=3)
        }
        for name, meter in meters.items():
            print(f'Meter {name }: {meter.serial_number} sw v{meter.software_version} @ {meter.unit or "broadcast"}')
        while True:
            print(f'{datetime.now():%d.%m.%Y %H:%M:%S.%f}', end='')
            for name, meter in meters.items():
                try:
                    print(f'\t{name} {meter.voltage:5.1f} V, {meter.current:5.2f} A, {meter.power_active:6.1f} W, {meter.power_factor:+5.3f}, {meter.frequency:5.2f} Hz, {meter.total_energy_active:10.3f} kWh', end='')
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f'Communication with meter {name} failed due to {e}.')
            print()
    except KeyboardInterrupt:
        print('\nExit')
    finally:
        modbus.disconnect()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
