"""
# Domoticz Chacon 433 MHz Python Plugin

## Installation

```bash
cd ~
git clone https://github.com/gaelj/Chacon433Plugin.git domoticz/plugins/Chacon433Plugin
chmod +x domoticz/plugins/DAT/plugin.py
ln -Tsf DomoticzWrapper/DomoticzWrapperClass.py DomoticzWrapperClass.py
ln -Tsf DomoticzWrapper/DomoticzPluginHelper.py DomoticzPluginHelper.py
sudo systemctl restart domoticz.service
```

For more details, see [Using Python Plugins](https://www.domoticz.com/wiki/Using_Python_plugins)
"""

"""
<plugin
    key="Chacon433"
    name="Chacon433"
    author="gaelj"
    version="1.0.0"
    wikilink="https://github.com/gaelj/Chacon433Plugin//blob/master/README.md"
    externallink="https://github.com/gaelj/Chacon433Plugin">

    <description>
        <h2>Domoticz Chacon 433 interface</h2><br/>
    </description>

    <params>
        <param field="Address"  label="Domoticz IP Address"                                          width="200px" required="true"  default="localhost" />
        <param field="Port"     label="Port"                                                         width="40px"  required="true"  default="8080"      />
        <param field="Username" label="Username"                                                     width="200px" required="false" default=""          />
        <param field="Password" label="Password"                                                     width="200px" required="false" default=""          />
        <param field="Mode1" label="DIOShutterCode" width="200px" required="true" />
        <param field="Mode2" label="Shutter index" width="200px" required="true" default="0"/>
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

import Domoticz
from datetime import datetime, timedelta
import time
from enum import IntEnum
import subprocess

z = None
pluginDevices = None

class PluginConfig:
    """Plugin configuration (singleton)"""

    def __init__(self):
        self.fldChacon = r'/home/pi/433Utils/RPi_utils/'
        self.cmdChacon = 'codesend'
        self.ChaconCode = '0FF'
        self.DIOShutterCode = z.Parameters.Mode1 #'11111111'
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
        self.shutter = ShutterActuator(self.config.idx, self.config.DIOShutterCode)
        self.switches = dict([(du, VirtualSwitch(du)) for du in DeviceUnits])
        self.shutterControlSwitch = self.switches[DeviceUnits.DeviceSwitch]


class ShutterActuator:
    """Shutter actuator"""

    def __init__(self, idx, shutterNumber):
        global z
        global pluginDevices
        self.idx = idx
        self.state = None
        self.shutterNumber = z.Parameters.Mode2
        self.config = PluginConfig()

    def SetValue(self, state: bool):
        global z
        global pluginDevices
        if self.state != state:
            command = "On" if state else "Off"
            self.state = state
            z.DomoticzAPI(
                "type=command&param=switchlight&idx={}&switchcmd={}".format(self.idx, command))

        stateString = 'on' if state else 'off'        
        z.WriteLog(self.config.fldDio + self.config.cmdDio + ' 0 ' + self.config.DIOShutterCode + ' ' + str(self.shutterNumber) + ' ' + stateString)
        subprocess.call(self.config.fldDio + self.config.cmdDio + ' 0 ' + self.config.DIOShutterCode + ' ' + str(self.shutterNumber) + ' ' + stateString, shell = True)

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

    z.InitDevice('Shutter Control', DeviceUnits.DeviceSwitch,
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
    pluginDevices.shutter.SetValue(value)


def onHeartbeat():
    global z
    global pluginDevices
    z.onHeartbeat()
