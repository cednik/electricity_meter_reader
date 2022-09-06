#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from argparse import ArgumentParser
from typing import Any
from datetime import datetime
import sdm_modbus

baudrate = 9600
parity = 'N'

class MeterReader(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registers |= {
            "serial_number": (0xFC00, 2, sdm_modbus.meter.registerType.HOLDING, sdm_modbus.meter.registerDataType.UINT32, int, "Serial number", "", 1, 1),
            "meter_code": (0xFC02, 1, sdm_modbus.meter.registerType.HOLDING, sdm_modbus.meter.registerDataType.INT16, int, "Meter code", "", 1, 1), # dtype should be UINT16, but it is not implemented in sdm_modbus package yet
            "software_version": (0xFC02, 1, sdm_modbus.meter.registerType.HOLDING, sdm_modbus.meter.registerDataType.INT16, int, "Software version", "", 1, 1), # dtype should be UINT16, but it is not implemented in sdm_modbus package yet
        }
    
    def __getattr__(self, name: str) -> Any:
        if name in self.registers:
            return self.read(name)
        else:
            raise AttributeError(f'Class {self.__class__.__name__} has no attribute {name}.')

class SDM120(MeterReader, sdm_modbus.SDM120):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class SDM72(MeterReader, sdm_modbus.SDM72):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

def main(argv):
    parser = ArgumentParser(os.path.basename(argv[0]))
    parser.add_argument('port')
    config = parser.parse_args(argv[1:])

    modbus = sdm_modbus.Meter(device=config.port, baud=baudrate, parity=parity)
    if not modbus.connect():
        print(f'Unable to connect to port {config.port}.')
        return -1
    try:
        meters = {
            'front_flat' : SDM120(parent=modbus, unit=1),
            'rear_flat'  : SDM120(parent=modbus, unit=2),
            'workroom'   : SDM72 (parent=modbus, unit=3)
        }
        t = datetime.now()
        print(f'{t:%d.%m.%Y %H:%M:%S.%f}')
        for name, meter in meters.items():
            print(f'Meter {name }: {meter.serial_number} sw v{meter.software_version} @ {meter.unit or "broadcast"}')
            print(f'\tdemand: time {meter.demand_time}, period {meter.demand_period}')
            if isinstance(meter, SDM120):
                print(f'\t\t total_demand_power_active         {meter.total_demand_power_active:6.1f} W')
                print(f'\t\t maximum_total_demand_power_active {meter.maximum_total_demand_power_active:6.1f} W')
                print(f'\t\t total_demand_current              {meter.total_demand_current:5.2f} A')
                print(f'\t\t maximum_total_demand_current      {meter.maximum_total_demand_current:5.2f} A')
            elif isinstance(meter, SDM72):
                pass
            else:
                print(f'Unknown meter type {meter.__class__.__name__}')
        return 0
        while True:
            t = datetime.now()
            print(f'{t:%d.%m.%Y %H:%M:%S.%f}', end='')
            for name, meter in meters.items():
                if name == 'workroom':
                    continue
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
