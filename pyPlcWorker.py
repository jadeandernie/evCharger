import pyPlcHomeplug
import fsmEvse
import addressManager
import subprocess
import hardwareInterface
import connMgr

class pyPlcWorker():
    def __init__(self, callbackAddToTrace=None, callbackShowStatus=None, callbackSoC=None):
        print("initializing pyPlcWorker")
        self.nMainFunctionCalls=0
        self.strUserAction = ""
        self.addressManager = addressManager.addressManager()
        self.callbackAddToTrace = callbackAddToTrace
        self.callbackShowStatus = callbackShowStatus
        self.callbackSoC = callbackSoC
        self.oldAvlnStatus = 0
        self.connMgr = connMgr.connMgr(self.workerAddToTrace, self.showStatus)
        self.hp = pyPlcHomeplug.pyPlcHomeplug(self.workerAddToTrace, self.showStatus, self.addressManager, self.connMgr)
        self.hardwareInterface = hardwareInterface.hardwareInterface(self.workerAddToTrace, self.showStatus)
        self.hp.printToUdp("pyPlcWorker init")
        # Find out the version number, using git.
        # see https://stackoverflow.com/questions/14989858/get-the-current-git-hash-in-a-python-script
        try:
            strLabel = str(subprocess.check_output(["git", "describe", "--tags"], text=True).strip())
        except:
            strLabel = "(unknown version. 'git describe --tags' failed.)"
        self.workerAddToTrace("[pyPlcWorker] Software version " + strLabel)
        self.evse = fsmEvse.fsmEvse(self.addressManager, self.workerAddToTrace, self.hardwareInterface, self.showStatus, self.callbackSoC)

    def workerAddToTrace(self, s):
        # The central logging function. All logging messages from the different parts of the project
        # shall come here.
        self.callbackAddToTrace(s) # give the message to the upper level, eg for console log.
        self.hp.printToUdp(s) # give the message to the udp for remote logging.

    def showStatus(self, s, selection = "", strAuxInfo1="", strAuxInfo2=""):
        self.callbackShowStatus(s, selection)
        if (selection == "pevState"):
            self.hardwareInterface.showOnDisplay(s, strAuxInfo1, strAuxInfo2)

    def handleTcpConnectionTrigger(self):
        if (self.connMgr.getConnectionLevel()<50):
            self.oldAvlnStatus = 0

    def mainfunction(self):
        self.nMainFunctionCalls+=1
        self.connMgr.mainfunction()
        self.handleTcpConnectionTrigger()
        self.hp.mainfunction() # call the lower-level workers
        self.hardwareInterface.mainfunction()
        if (self.nMainFunctionCalls>8*33): # ugly. Wait with EVSE high level handling, until the modem restarted.
            self.evse.mainfunction() # call the evse state machine

    def handleUserAction(self, strAction):
        self.strUserAction = strAction
        print("user action " + strAction)
        if (strAction == "space"):
            print("stopping the charge process")
            if (hasattr(self, 'pev')):
                self.pev.stopCharging()
        self.hp.sendTestFrame(strAction)