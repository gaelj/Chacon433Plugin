"""
# Domoticz Advanced Thermostat Python Plugin

This thermostat plugin allows precise temperature management and regulation per individual room

## Installation

```bash
cd ~
git clone https://github.com/gaelj/DomoticzAdvancedThermostatPlugin.git domoticz/plugins/DAT
chmod +x domoticz/plugins/DAT/plugin.py
sudo systemctl restart domoticz.service
```

For more details, see [Using Python Plugins](https://www.domoticz.com/wiki/Using_Python_plugins)
"""

"""
<plugin
    key="GaelJDomoticzAdvancedThermostat"
    name="GDAT"
    author="gaelj"
    version="1.0.0"
    wikilink="https://github.com/gaelj/DomoticzAdvancedThermostatPlugin/blob/master/README.md"
    externallink="https://github.com/gaelj/DomoticzAdvancedThermostatPlugin">

    <description>
        <h2>Domoticz Advanced Thermostat</h2><br/>
        This thermostat plugin allows precise temperature management and regulation per individual room

        <h3>Modes</h3>
        <ul style="list-style-type:square">
            <li>off</li>
            <li>away</li>
            <li>night</li>
            <li>eco</li>
            <li>Normal</li>
            <li>comfort</li>
        </ul>

        <h3>Features</h3>
        <ul style="list-style-type:square">
            <li>individual room temperature management</li>
            <li>global presence management</li>
            <li>room presence management</li>
            <li>control thermostat radiator valves temperature settings</li>
            <li>read thermostat radiator valves temperature measurements</li>
        </ul>

        <h3>Devices</h3>
        <ul style="list-style-type:square">
            <li>Thermostat Control: Off|Away|Night|Normal|Comfort</li>
            <li>Room 1 Presence: Absent|Present</li>
            <li>Room 2 Presence: Absent|Present</li>
        </ul>

        <h3>Configuration</h3>
        Configuration options...
    </description>

    <params>
        <param field="Address"  label="Domoticz IP Address"                                          width="200px" required="true"  default="localhost" />
        <param field="Port"     label="Port"                                                         width="40px"  required="true"  default="8080"      />
        <param field="Username" label="Username"                                                     width="200px" required="false" default=""          />
        <param field="Password" label="Password"                                                     width="200px" required="false" default=""          />
        <param field="Mode1" label="Apply minimum heating per cycle" width="200px">
            <options>
				<option label="ony when heating required" value="Normal"  default="true" />
                <option label="always" value="Forced"/>
            </options>
        </param>
        <param field="Mode2" label="Calculation cycle, Minimum Heating time per cycle, Pause On delay, Pause Off delay, Forced mode duration (all in minutes)" width="200px" required="true" default="30,0,2,1,60"/>
        <param field="Mode3" label="Logging Level" width="200px">
            <options>
                <option label="Normal" value="Normal" default="true"/>
                <option label="Verbose" value="Verbose"/>
                <option label="Debug - Python Only" value="2"/>
                <option label="Debug - Basic" value="62"/>
                <option label="Debug - Basic+Messages" value="126"/>
                <option label="Debug - Connections Only" value="16"/>
                <option label="Debug - Connections+Queue" value="144"/>
                <option label="Debug - All" value="-1"/>
            </options>
        </param>
    </params>
</plugin>
"""

# <param field="Mode1"    label="Inside Temperature Sensors, grouped by room (idx1, idx2...)"  width="300px" required="true"  default=""          />
# <param field="Mode2"    label="Outside Temperature Sensors (idx1, idx2...)"                  width="300px" required="true"  default=""          />
# <param field="Mode3"    label="Heating switch + Inside Radiator Setpoints, grouped by room (idx1, idx2...)"   width="300px" required="true"  default=""          />


import Domoticz
from datetime import datetime, timedelta
import time
from enum import IntEnum
z = None
pluginDevices = None

class PluginConfig:
    """Plugin configuration (singleton)"""

    def __init__(self):
        self.fldChacon = r'/home/pi/433Utils/RPi_utils/'
        self.cmdChacon = 'codesend'
        self.ChaconCode = '0FF'
        self.DIOShutterCode = '11111111'
        self.fldDio = r'/home/pi/hcc/'
        self.cmdDio = 'radioEmission'
        self.idx = 0

class DeviceUnits(IntEnum):
    """Unit numbers of each virtual switch"""
    DeviceSwitch = 1


class VirtualSwitch:
    """Virtual switch, On/Off or multi-position"""

    def __init__(self, pluginDeviceUnit: DeviceUnits):
        global z
        global pluginDevices
        self.pluginDeviceUnit = pluginDeviceUnit
        self.value = None

    def SetValue(self, value):
        global z
        global pluginDevices
        nValue = 1 if int(value) > 0 else 0
        if value in (0, 1):
            sValue = ""
        else:
            sValue = str(value)
        z.Devices[self.pluginDeviceUnit.value].Update(
            nValue=nValue, sValue=sValue)
        self.value = value

    def Read(self):
        global z
        global pluginDevices
        d = z.Devices[self.pluginDeviceUnit.value]
        self.value = int(d.sValue) if d.sValue is not None and d.sValue != "" else int(
            d.nValue) if d.nValue is not None else None
        return self.value


class PluginDevices:
    def __init__(self):
        self.config = PluginConfig()
        self.shutter = ShutterActuator(self.config.idx)
        self.switches = dict([(du, VirtualSwitch(du)) for du in DeviceUnits])
        self.shutterControlSwitch = self.switches[DeviceUnits.DeviceSwitch]


class ShutterActuator:
    """Shutter actuator"""

    def __init__(self, idx):
        global z
        global pluginDevices
        self.idx = idx
        self.state = None

    def SetValue(self, state: bool):
        global z
        global pluginDevices
        if self.state != state:
            command = "On" if state else "Off"
            self.state = state
            z.DomoticzAPI(
                "type=command&param=switchlight&idx={}&switchcmd={}".format(self.idx, command))

    def Read(self) -> bool:
        global z
        global pluginDevices
        devicesAPI = z.DomoticzAPI(
            "type=devices&filter=light&used=true&order=Name")
        if devicesAPI:
            for device in devicesAPI["result"]:
                idx = int(device["idx"])
                if idx != self.idx:
                    continue
                if "Status" in device:
                    self.state = device["Status"] == "On"
        return self.state



def onStart():
    global z
    global pluginDevices
    # prod
    # from DomoticzWrapperClass import \
    # dev
    # from DomoticzWrapper.DomoticzWrapperClass import \
    #     DomoticzTypeName, DomoticzDebugLevel, DomoticzPluginParameters, \
    #     DomoticzWrapper, DomoticzDevice, DomoticzConnection, DomoticzImage, \
    #     DomoticzDeviceType

    # dev
    # from DomoticzWrapper.DomoticzPluginHelper import \
    # prod
    from DomoticzPluginHelper import \
        DomoticzPluginHelper, DeviceParam, ParseCSV, DomoticzDeviceTypes

    z = DomoticzPluginHelper(
        Domoticz, Settings, Parameters, Devices, Images, {})
    z.onStart(3)

    LightSwitch_Switch_Blinds = DomoticzDeviceTypes.LightSwitch_Switch_Blinds()

    z.InitDevice('Thermostat Control', DeviceUnits.DeviceSwitch,
                 DeviceType=LightSwitch_Switch_Blinds,
                 Used=True,
                 defaultNValue=0,
                 defaultSValue="0")

    pluginDevices = PluginDevices()


def onStop():
    global z
    global pluginDevices
    z.onStop()


def onCommand(Unit, Command, Level, Color):
    global z
    global pluginDevices
    z.onCommand(Unit, Command, Level, Color)
    if Command == "On":
        value = 1
    elif Command == "Off":
        value = 0
    else:
        value = Level
    du = DeviceUnits(Unit)
    pluginDevices.switches[du].SetValue(value)


def onHeartbeat():
    global z
    global pluginDevices
    z.onHeartbeat()
