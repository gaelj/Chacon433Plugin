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
        <param field="Mode2" label="Shutter indexes (csv)" width="200px" required="true" default="0"/>
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


class PluginDevices:
    def __init__(self, shutterIds):
        self.config = PluginConfig()
        self.shutters = dict([(i, ShutterActuator(x)) for x, i in enumerate(shutterIds)])


class ShutterActuator:
    """Shutter actuator"""

    def __init__(self, shutterNumber):
        global z
        global pluginDevices
        self.state = None
        self.shutterNumber = shutterNumber
        self.config = PluginConfig()

    def SetValue(self, state: bool):
        global z
        global pluginDevices
        self.state = not state
        stateString = 'on' if self.state else 'off'        
        z.WriteLog(self.config.fldDio + self.config.cmdDio + ' 0 ' + self.config.DIOShutterCode + ' ' + str(self.shutterNumber) + ' ' + stateString)
        subprocess.call(self.config.fldDio + self.config.cmdDio + ' 0 ' + self.config.DIOShutterCode + ' ' + str(self.shutterNumber) + ' ' + stateString, shell = True)

    # def Read(self) -> bool:
    #     global z
    #     global pluginDevices
    #     devicesAPI = z.DomoticzAPI(
    #         "type=devices&filter=light&used=true&order=Name")
    #     if devicesAPI:
    #         for device in devicesAPI["result"]:
    #             idx = int(device["idx"])
    #             if idx != self.idx:
    #                 continue
    #             if "Status" in device:
    #                 self.state = device["Status"] == "On"
    #     return self.state



def onStart():
    global z
    global pluginDevices
    from DomoticzPluginHelper import \
        DomoticzPluginHelper, DeviceParam, ParseCSV, DomoticzDeviceTypes

    z = DomoticzPluginHelper(
        Domoticz, Settings, Parameters, Devices, Images, {})
    z.onStart(3)

    LightSwitch_Switch_Blinds = DomoticzDeviceTypes.LightSwitch_Switch_Blinds()

    shutterIds = [x.strip() for x in z.Parameters.Mode2.split(',') if len(x.strip()) > 0]
    deviceUnit = 1

    for shutterId in shutterIds:
        z.InitDevice('Shutter Control ' + str(deviceUnit), deviceUnit,
                    DeviceType=LightSwitch_Switch_Blinds,
                    Used=True,
                    defaultNValue=0,
                    defaultSValue="0")
        deviceUnit = deviceUnit + 1

    pluginDevices = PluginDevices(shutterIds)


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
    pluginDevices.shutters[(int(Unit))].SetValue(value)


def onHeartbeat():
    global z
    global pluginDevices
    z.onHeartbeat()
