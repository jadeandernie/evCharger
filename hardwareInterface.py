# For serial (including USB-to-serial) interfaces:
# https://pyserial.readthedocs.io/en/latest/pyserial.html
# Install pyserial library:
#   python -m pip install pyserial
# List ports:
#   python -m serial.tools.list_ports

import serial # the pyserial
from serial.tools.list_ports import comports
from time import sleep
from configmodule import getConfigValue, getConfigValueBool
import sys # For exit_on_session_end hack

PinCp = "P8_18"
PinPowerRelay = "P8_16"

class hardwareInterface():        
    def findSerialPort(self):
        baud = int(getConfigValue("serial_baud"))
        if (getConfigValue("serial_port")!="auto"):
            port = getConfigValue("serial_port")
            try:
                self.addToTrace("Using serial port " + port)
                self.ser = serial.Serial(port, baud, timeout=0)
                self.isSerialInterfaceOk = True
            except:
                self.addToTrace("ERROR: Could not open serial port.")
                self.ser = None
                self.isSerialInterfaceOk = False
            return

        ports = []
        self.addToTrace('Auto detection of serial ports. Available serial ports:')
        for n, (port, desc, hwid) in enumerate(sorted(comports()), 1):
            if (port=="/dev/ttyAMA0"):
                self.addToTrace("ignoring /dev/ttyAMA0, because this is not an USB serial port")
            else:
                self.addToTrace('{:2}: {:20} {!r}'.format(n, port, desc))
                ports.append(port)
        if (len(ports)<1):
            self.addToTrace("ERROR: No serial ports found. No hardware interaction possible.")
            self.ser = None
            self.isSerialInterfaceOk = False
        else:
            self.addToTrace("ok, we take the first port, " + ports[0])
            try:
                self.ser = serial.Serial(ports[0], baud, timeout=0)
                self.isSerialInterfaceOk = True
            except:
                self.addToTrace("ERROR: Could not open serial port.")
                self.ser = None
                self.isSerialInterfaceOk = False

    def addToTrace(self, s):
        self.callbackAddToTrace("[HARDWAREINTERFACE] " + s)            

    def setStateB(self):
        self.addToTrace("Setting CP line into state B.")
        self.outvalue &= ~1
        
    def setStateC(self):
        self.addToTrace("Setting CP line into state C.")
        self.outvalue |= 1
        
    def setPowerRelayOn(self):
        self.addToTrace("Switching PowerRelay ON.")
        self.outvalue |= 2

    def setPowerRelayOff(self):
        self.addToTrace("Switching PowerRelay OFF.")
        self.outvalue &= ~2

    def setRelay2On(self):
        self.addToTrace("Switching Relay2 ON.")
        self.outvalue |= 4

    def setRelay2Off(self):
        self.addToTrace("Switching Relay2 OFF.")
        self.outvalue &= ~4
        
    def getPowerRelayConfirmation(self):
        return 1 # todo: self.contactor_confirmed
        
    def triggerConnectorLocking(self):
        self.addToTrace("Locking the connector")
        # todo control the lock motor into lock direction until the end (time based or current based stopping?)

    def triggerConnectorUnlocking(self):
        self.addToTrace("Unocking the connector")
        # todo control the lock motor into unlock direction until the end (time based or current based stopping?)

    def isConnectorLocked(self):
        # TODO: Read the lock= value from the hardware so that this works
        return 1 # todo: use the real connector lock feedback
        
    def setChargerParameters(self, maxVoltage, maxCurrent):
        self.maxChargerVoltage = int(maxVoltage)
        self.maxChargerCurrent = int(maxCurrent)
        
    def setChargerVoltageAndCurrent(self, voltageNow, currentNow):
        self.chargerVoltage = int(voltageNow)
        self.chargerCurrent = int(currentNow)

    def getInletVoltage(self):
        return self.inletVoltage
        
    def getAccuVoltage(self):
        return self.accuVoltage

    def getAccuMaxCurrent(self):
        #todo: get max charging current from the BMS
        self.accuMaxCurrent = 10
        return self.accuMaxCurrent

    def getAccuMaxVoltage(self):
        if getConfigValue("charge_target_voltage"):
            self.accuMaxVoltage = getConfigValue("charge_target_voltage")            
        else:
            #todo: get max charging voltage from the BMS
            self.accuMaxVoltage = 230
        return self.accuMaxVoltage

    def getIsAccuFull(self):
        return self.IsAccuFull
        
    def __init__(self, callbackAddToTrace=None, callbackShowStatus=None):
        self.callbackAddToTrace = callbackAddToTrace
        self.callbackShowStatus = callbackShowStatus

        self.loopcounter = 0
        self.outvalue = 0
        self.inletVoltage = 0.0 # volts
        self.accuVoltage = 0.0
        self.lock_confirmed = False  # Confirmation from hardware
        self.cp_pwm = 0.0
        self.soc_percent = 0.0
        self.capacity = 0.0
        self.accuMaxVoltage = 0.0
        self.accuMaxCurrent = 0.0
        self.contactor_confirmed = False  # Confirmation from hardware
        self.plugged_in = None  # None means "not known yet"
        self.lastReceptionTime = 0

        self.maxChargerVoltage = 0
        self.maxChargerCurrent = 10
        self.chargerVoltage = 0
        self.chargerCurrent = 0

        self.logged_inlet_voltage = None
        self.logged_dc_link_voltage = None
        self.logged_cp_pwm = None
        self.logged_max_charge_a = None
        self.logged_soc_percent = None
        self.logged_contactor_confirmed = None
        self.logged_plugged_in = None

        self.rxbuffer = ""

        self.findSerialPort()

    def close(self):
        if (self.isSerialInterfaceOk):        
            self.ser.close()

    def evaluateReceivedData_dieter(self, s):
        self.rxbuffer += s
        x=self.rxbuffer.find("A0=")
        if (x>=0):
            s = self.rxbuffer[x+3:x+7]
            if (len(s)==4):
                try:
                    self.inletVoltage = int(s) / 1024.0 * 1.08 * (6250) / (4.7+4.7)
                except:
                    # keep last known value, if nothing new valid was received.
                    pass
                self.rxbuffer = self.rxbuffer[x+3:] # consume the receive buffer entry

    def evaluateReceivedData_celeron55device(self, s):
        self.rxbuffer += s
        while True:
            x = self.rxbuffer.find("\n")
            if x < 0:
                break
            line = self.rxbuffer[0:x].strip()
            self.rxbuffer = self.rxbuffer[x+1:]
            if line.startswith("inlet_v="):
                self.inletVoltage = int(line[8:])
                if self.logged_inlet_voltage != self.inletVoltage:
                    self.logged_inlet_voltage = self.inletVoltage
                    self.addToTrace("<< inlet_voltage="+str(self.inletVoltage))
                if self.callbackShowStatus:
                    self.callbackShowStatus(format(self.inletVoltage,".1f"), "uInlet")
            elif line.startswith("dc_link_v="):
                self.accuVoltage = int(line[10:])
                if self.logged_dc_link_voltage != self.accuVoltage:
                    self.logged_dc_link_voltage = self.accuVoltage
                    self.addToTrace("<< dc_link_voltage="+str(self.accuVoltage))
            elif line.startswith("cp_pwm="):
                self.cp_pwm = int(line[7:])
                if self.logged_cp_pwm != self.cp_pwm:
                    self.logged_cp_pwm = self.cp_pwm
                    self.addToTrace("<< cp_pwm="+str(self.cp_pwm))
            elif line.startswith("cp_output_state="):
                state = int(line[len("cp_output_state="):])
                if bool(state) == ((self.outvalue & 1)!=0):
                    self.addToTrace("<< CP state confirmed")
                else:
                    self.addToTrace("<< CP state MISMATCH")
            elif line.startswith("ccs_contactor_wanted_closed="):
                state = int(line[len("ccs_contactor_wanted_closed="):])
                if bool(state) == ((self.outvalue & 2)!=0):
                    self.addToTrace("<< Contactor request confirmed")
                else:
                    self.addToTrace("<< Contactor request MISMATCH")
            elif line.startswith("max_charge_a="):
                self.accuMaxCurrent = int(line[13:])
                if self.logged_max_charge_a != self.accuMaxCurrent:
                    self.logged_max_charge_a = self.accuMaxCurrent
                    self.addToTrace("<< max_charge_a="+str(self.accuMaxCurrent))
            elif line.startswith("soc_percent="):
                self.soc_percent = int(line[12:])
                if self.logged_soc_percent != self.soc_percent:
                    self.logged_soc_percent = self.soc_percent
                    self.addToTrace("<< soc_percent="+str(self.soc_percent))
            elif line.startswith("contactor_confirmed="):
                self.contactor_confirmed = bool(int(line[20:]))
                if self.logged_contactor_confirmed != self.contactor_confirmed:
                    self.logged_contactor_confirmed = self.contactor_confirmed
                    self.addToTrace("<< contactor_confirmed="+str(self.contactor_confirmed))
            elif line.startswith("plugged_in="):
                self.plugged_in = bool(int(line[11:]))
                if self.logged_plugged_in != self.plugged_in:
                    self.logged_plugged_in = self.plugged_in
                    self.addToTrace("<< plugged_in="+str(self.plugged_in))
            else:
                self.addToTrace("Received unknown line: \""+line+"\"")

    def showOnDisplay(self, s1, s2, s3):
        # show the given string s on the display which is connected to the serial port
        if (getConfigValueBool("display_via_serial") and self.isSerialInterfaceOk):
            s = "lc" + s1 + "\n" + "lc" + s2 + "\n" + "lc" + s3 + "\n"
            self.ser.write(bytes(s, "utf-8"))
        
    def mainfunction(self):        
        self.mainfunction()
        if getConfigValueBool("exit_on_session_end"):
            # TODO: This is a hack. Do this in fsmPev instead and publish some
            # of these values into there if needed.
            if (self.plugged_in is not None and self.plugged_in == False and
                    self.inletVoltage < 50):
                sys.exit(0)

    def mainfunction(self):
        self.loopcounter+=1
        if (self.isSerialInterfaceOk):
            if (self.loopcounter>15):
                self.loopcounter=0
                # self.ser.write(b'hello world\n')
                s = "000" + str(self.outvalue)
                self.ser.write(bytes("do"+s+"\n", "utf-8")) # set outputs of dieter, see https://github.com/uhi22/dieter
            s = self.ser.read(100)
            if (len(s)>0):
                try:
                    s = str(s, 'utf-8').strip()
                except:
                    s = "" # for the case we received corrupted data (not convertable as utf-8)
                self.addToTrace(str(len(s)) + " bytes received: " + s)
                self.evaluateReceivedData_dieter(s)

if __name__ == "__main__":
    print("Testing hardwareInterface...")
    hw = hardwareInterface()
    for i in range(0, 350):
        hw.mainfunction()
        if (i==20):
            hw.showOnDisplay("Hello", "A DEMO", "321.0V")
        if (i==50):
            hw.setStateC()
        if (i==100):
            hw.setStateB()
        if (i==150):
            hw.setStateC()
            hw.setPowerRelayOn()
            hw.showOnDisplay("", "..middle..", "")
        if (i==200):
            hw.setStateB()
            hw.setPowerRelayOff()
        if (i==250):
            hw.setRelay2On()
        if (i==300):
            hw.setRelay2Off()
        if (i==320):
            hw.showOnDisplay("This", "...is...", "DONE :-)")
        sleep(0.03)
    hw.close()    
    print("finished.")
