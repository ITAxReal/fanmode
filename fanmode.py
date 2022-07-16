#!/usr/bin/env python3
import os
import sys
from prettytable import PrettyTable


hwmon_path = "/sys/class/hwmon/"


class Fan:

    @staticmethod
    def get_path(platform, id):
        paths = list(os.walk(hwmon_path))[0][1]
        for i in paths:
            if os.path.exists(f"{hwmon_path}{i}/name"):
                with open(f"{hwmon_path}{i}/name") as f:
                    pl_nm = f.read().strip()
                if pl_nm == platform:
                    if os.path.exists(f"{hwmon_path}{i}/pwm{id}"):
                        return f"{hwmon_path}{i}/pwm{id}", f"{hwmon_path}{i}/pwm{id}_enable"

    def __init__(self, fan_spec: list):
        self.name, self.platform, self.id,\
            self.auto, self.manual, self.path = fan_spec
        if not self.path:
            self._find_path()
        else:
            self.mode_path = self.path + '_enable'

    def _find_path(self):
        self.path, self.mode_path = Fan.get_path(self.platform, self.id)

    def _get_mode(self):
        with open(self.mode_path) as f:
            mode = f.read().strip()
        return mode

    @property
    def mode(self):
        mode = self._get_mode()
        if mode == self.auto:
            return f'Auto ({mode})'
        elif mode == self.manual:
            return f'Manual ({mode})'
        else:
            return f'Unknown ({mode})'

    def _set_mode(self, mode):
        os.system(f"echo {mode} > {self.mode_path}")
        return self._get_mode()

    @mode.setter
    def mode(self, mode):
        mode = str(mode).lower()
        nm = None
        if mode == 'auto':
            nm = self.auto
        elif mode == 'man':
            nm = self.manual
        elif mode.isnumeric():
            nm = mode
        else:
            raise ValueError(f"Can't set mode {mode} on {self.name}")
        sm = self._set_mode(nm)
        if sm != nm:
            raise RuntimeError(f"Setting mode {nm} on {self.name} failed (got {sm})!")

    @property
    def pwm(self):
        with open(self.path) as f:
            pwm = f.read().strip()
        return pwm

    @pwm.setter
    def pwm(self, pwm):
        pwm = str(pwm)
        if pwm.isnumeric() and int(pwm) >= 0 and int(pwm) <= 255:
            os.system(f"echo {pwm} > {self.path}")
            if self.pwm != pwm:
                #raise RuntimeError(f"Can't set PWM ({pwm}) on {self.name} ({self.pwm})")
                print(f"[W] PWM setted on {self.name} inaccurately ({pwm} != {self.pwm})")
        else:
            raise ValueError("Invalid PWM value")


fans = [
    #     name   platform  id   auto man  path
    Fan(['cpu', 'nct6798', '2', '5', '1', None]),
    Fan(['cpu_2', 'nct6798', '1', '5', '1', None]),
    Fan(['case', 'nct6798', '3', '5', '1', None]),
    Fan(['gpu', 'amdgpu', '1', '2', '1', None])
]
aliases = {
    'full-case': 'cpu_2+case',
    'all': 'cpu+cpu_2+case+gpu',
    'no-gpu': 'cpu+cpu_2+case',
    'no-cpu': 'cpu_2+case+gpu'
}

modes = {
    'max': 255,
    'high': 190,
    'mid': 127,
    'low': 76,
    'off': 0
}


def get_fan(name):
    for i in fans:
        if i.name == name:
            return i
    raise RuntimeError(f"Fan {name} not found!")


def show(final=False):
    """Shows fans and modes"""
    print("FANS:")
    table = PrettyTable(['Name', 'Mode', 'PWM'])
    table.align = 'l'
    for fan in fans:
        table.add_row([fan.name, fan.mode, fan.pwm])
    print(table)
    if final:
        sys.exit()
    print("\nALIASES:")
    table = PrettyTable(['Name', 'Fans'])
    table.align = 'l'
    for aliase in aliases:
        table.add_row([aliase, aliases[aliase].replace('+', ', ')])
    print(table)
    print("\nMODES:")
    table = PrettyTable(['Name', 'PWM'])
    table.align = 'l'
    for mode in modes:
        table.add_row([mode, modes[mode]])
    table.add_row(['auto', '-'])
    print(table)


def _help(msg=None):
    print("COMMANDS:")
    table = PrettyTable(["Command", 'Syntax', 'Description'])
    table.align = 'l'
    table.add_row(['set', 'set <fans> <mode/pwm> <value>', 'Set fan mode/pwm'])
    table.add_row(['info | show', 'info/show', 'Show fans and modes'])
    table.add_row(['default', 'default', 'Set auto mode on all fans'])
    table.add_row(['fans', 'fans', 'Show fans'])
    table.add_row(['help', 'help', 'Show this message'])
    print(table)
    table = PrettyTable(['Examples'])
    table.align = 'l'
    table.add_row(["fanmode set full-case mode high"])
    table.add_row(["fanmode set cpu+case pwm 100"])
    table.add_row(["fanmode set cpu+case mode auto"])
    print(table, end='\n\n')
    if msg:
        print(f"\nError: {msg}")
    else:
        show()
    sys.exit()


def _set():
    try:
        _fans = sys.argv[2]
    except IndexError:
        _help("Fans not set")
    if _fans in aliases:
        _fans = aliases[_fans]
    _fans = [get_fan(fan) for fan in _fans.split('+')]
    try:
        action = sys.argv[3]
    except IndexError:
        _help("Mode/PWM?")
    if action not in ['mode', 'pwm']:
        _help('Invalid value in mode/pwm')
    try:
        value = sys.argv[4]
    except IndexError:
        _help('Mode/PWM value not set')
    if action == 'mode':
        if value == 'auto':
            for fan in _fans:
                fan.mode = value
            show(True)
        if value in modes:
            value = modes[value]
        else:
            _help("Invalid mode value")
    for fan in _fans:
        fan.mode = 'man'
        fan.pwm = value
    show(True)


print("FanMode v0.1 - Control your FANS!")
try:
    action = sys.argv[1]
except IndexError:
    action = 'help'
match action:
    case 'info' | 'show':
        show()
    case 'set':
        _set()
    case 'default':
        sys.argv[2:] = ['all', 'mode', 'auto']
        _set()
    case 'help':
        _help()
    case 'fans':
        show(True)
    case _:
        _help(f"No action for {action}")

