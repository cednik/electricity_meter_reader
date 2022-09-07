#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
from argparse import ArgumentParser, Namespace
from typing import Any
from datetime import datetime
import logging
import logging.handlers as Handlers

sys.path.insert(1, os.path.join('sdm_modbus', 'src'))

import sdm_modbus

baudrate = 9600
parity = 'N'

class MeterReader(object):
    formats = {
        'voltage'  :  '5.1f',
        'current'  :  '5.2f',
        'energy'   : '10.3f',
        'power'    :  '6.1f',
        'factor'   : '+5.3f',
        'phase'    : '+5.3f',
        'frequency':  '5.2f'
    }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.registers |= {
            "serial_number": (0xFC00, 2, sdm_modbus.meter.registerType.HOLDING, sdm_modbus.meter.registerDataType.UINT32, int, "Serial number", "", self._unit_id_bank, 1),
            "meter_code": (0xFC02, 1, sdm_modbus.meter.registerType.HOLDING, sdm_modbus.meter.registerDataType.INT16, int, "Meter code", "", self._unit_id_bank, 1), # dtype should be UINT16, but it is not implemented in sdm_modbus package yet
            "software_version": (0xFC03, 1, sdm_modbus.meter.registerType.HOLDING, sdm_modbus.meter.registerDataType.INT16, int, "Software version", "", self._unit_id_bank, 1), # dtype should be UINT16, but it is not implemented in sdm_modbus package yet
        }
        for key in self.registers:
            self.registers[key] = list(self.registers[key])
            fmt = Namespace(fmt='', unit=self.registers[key][-3], to_str=None)
            if 'factor' in key:
                fmt.fmt = MeterReader.formats['factor']
            else:
                for k, v in MeterReader.formats.items():
                    if k in key:
                        fmt.fmt = v
            fmt.to_str = lambda v, fmt=fmt: f'{v:{fmt.fmt}} {fmt.unit}'
            self.registers[key][-3] = fmt
    
    def __getattr__(self, name: str) -> Any:
        if name in self.registers:
            return self.read(name)
        else:
            raise AttributeError(f'Class {self.__class__.__name__} has no attribute {name}.')

    def _change_bank(self, bank, *regs):
        for reg in regs:
            self.registers[reg][-2] = bank

    def read(self, key, scaling=False):
        if isinstance(key, str):
            return super().read(key, scaling)
        else:
            try:
                registers_backup = self.registers
                results = {}
                for rtype in (sdm_modbus.meter.registerType.INPUT, sdm_modbus.meter.registerType.HOLDING):
                    self.registers = {k: v for k, v in registers_backup.items() if k in key and v[2] == rtype}
                    results |= self.read_all(rtype, scaling)
                return results
            finally:
                self.registers = registers_backup

    def get_fmt(self, key):
        return self.registers[key][-3]

class SDM120(MeterReader, sdm_modbus.SDM120):
    def __init__(self, *args, **kwargs):
        self._unit_id_bank = 4
        super().__init__(*args, **kwargs)
        self._change_bank(2, 'frequency',
                             'import_energy_active',
                             'export_energy_active',
                             'import_energy_reactive',
                             'export_energy_reactive' )
        self.interesting_holdings = []

class SDM72(MeterReader, sdm_modbus.SDM72):
    def __init__(self, *args, **kwargs):
        self._unit_id_bank = 4
        super().__init__(*args, **kwargs)
        self._change_bank(5, 'neutral_current')
        self._change_bank(6, 'total_energy_active', 'total_energy_reactive')
        self._change_bank(2, 'system_power')
        self._change_bank(3, 'p1_divisor')
        # batch 1 apears to be too long for meter, so it returns None.
        # Therefore it has to be split:
        # add 1 to batch id of every INPUT register from l3_power_factor (excluded) down
        # (demand_time is the first HOLDING register).
        increment = False
        for k, v in self.registers.items():
            if increment:
                if k == 'demand_time':
                    break
                v[-2] += 1
            else:
                if k == 'l3_power_factor':
                    increment = True
        self.interesting_holdings = [
            'system_voltage',
            'system_current',
            'system_power'
        ]
    def read(self, key, scaling=False):
        return super().read(key, scaling)


def main(argv):
    parser = ArgumentParser(os.path.basename(argv[0]))
    parser.add_argument('port')
    config = parser.parse_args(argv[1:])

    logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)8s %(message)s', datefmt='%d.%m.%Y %H:%M:%S')
    log = logging.getLogger("pymodbus")
    log.setLevel(logging.DEBUG)
    #h = Handlers.DatagramHandler("localhost", 12345)
    #h = Handlers.SocketHandler("localhost", 12345)
    #h = logging.StreamHandler()
    #h.setLevel(logging.DEBUG)
    #log.addHandler(h)
    log.info('Log start')

    modbus = sdm_modbus.Meter(device=config.port, baud=baudrate, parity=parity)
    if not modbus.connect():
        print(f'Unable to connect to port {config.port}.')
        return -1
    try:
        meters = {
            'front_flat' : SDM120(parent=modbus, unit=1),
            'rear_flat ' : SDM120(parent=modbus, unit=2),
            'workroom  ' : SDM72 (parent=modbus, unit=3)
        }
        try:
            #output = open('test.txt', 'w')
            output = sys.stderr
        except Exception as e:
            print(f'Could not open output file, because of {e}. Fallback to stdout.')
            output = sys.stdout
        print(f'{datetime.now():%d.%m.%Y %H:%M:%S.%f}', file=output)
        #for name, meter in meters.items():
            #print(f'Meter {name }: {meter.serial_number} sw v{meter.software_version} @ {meter.unit or "broadcast"}', file=output)
            #print(f'\tdemand: time {meter.demand_time}, period {meter.demand_period}', file=output)
            # if meter.type == 'SDM120':
            #     print(f'\t\t total_demand_power_active         {meter.total_demand_power_active:6.1f} W')
            #     print(f'\t\t maximum_total_demand_power_active {meter.maximum_total_demand_power_active:6.1f} W')
            #     print(f'\t\t total_demand_current              {meter.total_demand_current:5.2f} A')
            #     print(f'\t\t maximum_total_demand_current      {meter.maximum_total_demand_current:5.2f} A')
            # elif meter.type == 'SDM72':
            #     pass
            # else:
            #     print(f'Unknown meter type {meter.type}')
        while True:
            print(f'{datetime.now():%d.%m.%Y %H:%M:%S.%f}', end='', file=output)
            for name, meter in meters.items():
                try:
                    t = datetime.now()
                    print(f'{t:%d.%m.%Y %H:%M:%S.%f} Reading {name} INPUT ...', end = '')
                    values = meter.read_all(sdm_modbus.meter.registerType.INPUT)
                    t = datetime.now()
                    print(f' {t:%d.%m.%Y %H:%M:%S.%f} HOLDING ...', end = '')
                    values |= meter.read(meter.interesting_holdings)
                    t = datetime.now()
                    print (f' done at {t:%d.%m.%Y %H:%M:%S.%f}.')
                    print(f'\t\t{t:%d.%m.%Y %H:%M:%S.%f} {name} {", ".join([f"{k} = {meter.get_fmt(k).to_str(v)}" for k, v in values.items()])}', end='', file=output)
                except KeyboardInterrupt:
                    raise
                except Exception as e:
                    print(f' Communication with meter {name} failed due to {e}.', file=output)
                print(file=output)
            print(file=output)
            print()
            break
    except KeyboardInterrupt:
        print('\nExit')
    finally:
        modbus.disconnect()
        if output not in (sys.stdout, sys.stderr):
            output.close()
    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))
