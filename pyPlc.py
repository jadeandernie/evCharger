import tkinter as tk
import time
import pyPlcWorker
from mytestsuite import * 

def storekeyname(event):
    global nKeystrokes
    global lastKey
    nKeystrokes+=1
    lastKey = event.keysym
    worker.handleUserAction(lastKey)
    return 'break' # swallow the event

def cbAddToTrace(s):
    print("[" + str(time.time()) + "ms] " + s)

def cbShowStatus(s, selection=""):
    if (selection == "pevmac"):
        lblPevMac['text']="PEV MAC " + s
        s=""
    if (selection == "uInlet"):
        lblUInlet['text']= "UInlet " + s + "V"
        s=""
    if (selection == "EVSEPresentVoltage"):
        lblEVSEPresentVoltage['text']= "EVSEPresentVoltage " + s + "V"
        s=""
    if (selection == "soc"):
        lblSoc['text']= "SOC " + s + "%"
        s=""
    if (len(s)>0):
        lblStatus['text']=s

root = tk.Tk()
root.geometry("400x350")
lastKey = ''
lblHelp = tk.Label(root, justify= "left")
lblHelp['text']="x=exit \nS=GET_SW \ns=SET_KEY \nG=GET_KEY (try twice) \nt=SET_KEY modified \n space=stop charging"
lblHelp.pack()
lblStatus = tk.Label(root, text="(Status)")
lblStatus.pack()
lblPevMac = tk.Label(root, text="(pev mac)")
lblPevMac.pack()
lblState = tk.Label(root, text="(state)")
lblState.config(font=('Helvetica bold', 20))
lblState.pack()
lblSoc = tk.Label(root, text="(soc)")
lblSoc.pack()
lblUInlet = tk.Label(root, text="(U Inlet)")
lblUInlet.config(font=('Helvetica bold', 26))
lblUInlet.pack()
lblEVSEPresentVoltage = tk.Label(root, text="(EVSEPresentVoltage)")
lblEVSEPresentVoltage.config(font=('Helvetica bold', 16))
lblEVSEPresentVoltage.pack()
button = tk.Button(root,text="Exit",command=root.destroy)
button.pack(side="bottom")

root.mainloop()

# lblTestcase = tk.Label(root, text="(test case)")
# lblTestcase.pack()

lblUInlet['text']= ""

nKeystrokes=0
# Bind the keyboard handler to all relevant elements:
root.bind('<Key>', storekeyname)
cbShowStatus("initialized")
worker=pyPlcWorker.pyPlcWorker(cbAddToTrace, cbShowStatus)

while lastKey!="x":
    time.sleep(.03)
    worker.mainfunction()
    # print("Starting tests ...")
    # lblTestcase['text']= "Testcase " + str(testsuite_getTcNumber())

del(worker)