# EXI is specified in w3.org/TR/exi
# For decoding and encoding, different decoders are availabe:
#  1.  https://github.com/FlUxIuS/V2Gdecoder
#      https://github.com/FlUxIuS/V2Gdecoder/releases
#      Install java from https://www.java.com/de/download/manual.jsp
#
#      C:\>java -version
#      java version "1.8.0_351"
#      Java(TM) SE Runtime Environment (build 1.8.0_351-b10)
#      Java HotSpot(TM) Client VM (build 25.351-b10, mixed mode, sharing)
#      C:\>
#
#      java -jar V2Gdecoder.jar -e -s 8000dbab9371d3234b71d1b981899189d191818991d26b9b3a232b30020000040040
#      ERROR:  'Premature EOS found while reading data.'
#      <?xml version="1.0" encoding="UTF-8"?><ns4:supportedAppProtocolReq xmlns:ns4="urn:iso:15118:2:2010:AppProtocol" 
#      xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ns3="http://www.w3.org/2001/XMLSchema">
#      <AppProtocol>
#      <ProtocolNamespace>urn:din:70121:2012:MsgDef</ProtocolNamespace>
#      <VersionNumberMajor>2</VersionNumberMajor>
#      <VersionNumberMinor>0</VersionNumberMinor>
#      <SchemaID>1</SchemaID>
#      <Priority>1</Priority>
#      </AppProtocol>
#      </ns4:supportedAppProtocolReq>
#
#  2. OpenV2G from https://github.com/Martin-P/OpenV2G
#      Pro: The schema-specific files are already included as generated C-code, this
#         makes it very fast.
#      Contra: Is only a demo, does not provide an interface which could be used for decoding/encoding.
#      Work in progress: Fork in https://github.com/uhi22/OpenV2Gx, to add a command line interface (and maybe a socket interface).

from helpers import twoCharHex
import subprocess
import time
import json

# Example data:
#   (1) From the Ioniq:
#     In wireshark: Copy as hex stream
#     01fe8001000000228000dbab9371d3234b71d1b981899189d191818991d26b9b3a232b30020000040040
#     remove the 8 bytes V2GTP header
#     8000dbab9371d3234b71d1b981899189d191818991d26b9b3a232b30020000040040
exiHexDemoSupportedApplicationProtocolRequestIoniq="8000dbab9371d3234b71d1b981899189d191818991d26b9b3a232b30020000040040"
#    Command line:
#    ./OpenV2G.exe DH8000dbab9371d3234b71d1b981899189d191818991d26b9b3a232b30020000040040

#    (1b) From the tesla. Source https://github.com/SmartEVSE/SmartEVSE-3/issues/25#issuecomment-1606259381)
exiHexDemoSupportedApplicationProtocolRequestTesla="8000DBAB9371D3234B71D1B981899189D191818991D26B9B3A232B30020000040401B75726E3A7465736C613A64696E3A323031383A4D736744656600001C0100080"
# The BMW iX3 handshake request (one schema, schemaID 0, from https://github.com/SmartEVSE/SmartEVSE-3/issues/25#issuecomment-1606271999)
exiHexDemoSupportedApplicationProtocolRequestBMWiX3="8000DBAB9371D3234B71D1B981899189D191818991D26B9B3A232B30020000000040"

#   (2) From OpenV2G main_example.appHandshake()
#   8000ebab9371d34b9b79d189a98989c1d191d191818981d26b9b3a232b30010000040001b75726e3a64696e3a37303132313a323031323a4d73674465660020000100880
exiHexDemoSupportedApplicationProtocolRequest2="8000ebab9371d34b9b79d189a98989c1d191d191818981d26b9b3a232b30010000040001b75726e3a64696e3a37303132313a323031323a4d73674465660020000100880"
#   Command line:
#   ./OpenV2G.exe DH8000ebab9371d34b9b79d189a98989c1d191d191818981d26b9b3a232b30010000040001b75726e3a64696e3a37303132313a323031323a4d73674465660020000100880

#   (3) SupportedApplicationProtocolResponse
#   80400040
#   Command line:
#   ./OpenV2G.exe DH80400040

#   (4) SessionSetupRequest DIN
#   809a0011d00000
#   Command line:
#   ./OpenV2G.exe DD809a0011d00000

#   (5) SessionSetupResponse DIN
# 809a02004080c1014181c211e0000080
#   ./OpenV2G.exe DD809a02004080c1014181c211e0000080

# (6) CableCheckReq
# "result": "809a001010400000"

# (7) PreChargeReq
# "result": "809a001150400000c80006400000"

# 809a0232417b661514a4cb91e0202d0691559529548c0841e0fc1af4507460c0 SessionSetupRes with NewSessionEstablished
# 809a0232417b661514a4cb91e0A02d0691559529548c0841e0fc1af4507460c0 SessionSetupRes with SequenceError
# 809a021a3b7c417774813311a00120024100c4 ServiceDiscoveryRes
# 809a021a3b7c417774813311a0A120024100c4 ServiceDiscoveryRes with SequenceError
# 809a021a3b7c417774813311c000 ServicePaymentSelectionRes
# 809a021a3b7c417774813311c0A0 ServicePaymentSelectionRes with SequenceError
# 809a021a3b7c417774813310c00200 ContractAuthenticationRes
# 809a021a3b7c417774813310c0A200 ContractAuthenticationRes with SequenceError
# 809a0125e6cecc50800001ec00200004051828758405500080000101844138101c2432c04081436c900c0c000041435ecc044606000200 ChargeParameterDiscovery
# 809a0125e6cecd50810001ec00201004051828758405500080000101844138101c2432c04081436c900c0c000041435ecc044606000200 ChargeParameterDiscovery with  ServiceSelectionInvalid
# 809a0125e6cecc5020004080000400  CableCheckRes
# 809a0125e6cecc5020804080000400  CableCheckRes with "FAILED"
# 809a0125e6cecc516000408000008284de880800  PreChargeRes
# 809a0125e6cecc516080408000008284de880800  PreChargeRes with "FAILED"
# 809a0125e6cecc51400420400000  PowerDeliveryRes
# 809a0125e6cecc51408420400000  PowerDeliveryRes with "FAILED"
# 809a0125e6cecc50e0004080000082867dc8081818000000040a1b64802030882702038486580800 CurrentDemandRes
# 809a0125e6cecc50e0804080000082867dc8081818000000040a1b64802030882702038486580800 CurrentDemandRes with "FAILED"

# Further examples are collected in the DemoExiLog.txt.

# Configuration of the exi converter tool
# Linux: Path to the EXI decoder/encoder
pathToOpenV2GExe = "../OpenV2Gx/Release/OpenV2G.exe";


# Functions
def exiprint(s):
    # todo: print to console or log or whatever
    pass

def exiHexToByteArray(hexString):
    # input: a string with the two-byte-hex representation
    # output: a byte array with the same data.
    # If the convertion fails, we return an empty byte array. 
    hexlen=len(hexString)
    if ((hexlen % 2)!=0):
        print("exiHexToByteArray: unplausible length of " + hexString)
        return bytearray(0)
    exiframe = bytearray(int(hexlen/2)) # two characters in the input string are one byte in the exiframe
    for i in range(0, int(hexlen/2)):
        x = hexString[2*i: 2*i+2]        
        #print("valuestring = " + x)
        try:
            v = int(x, 16)
            #print("value " + hex(v))
            exiframe[i] = v
        except:
            print("exiHexToByteArray: unplausible data " + x)
            return bytearray(0)
    return exiframe

def exiByteArrayToHex(b):
    # input: Byte array
    # output: a string with the two-byte-hex representation of the byte array
    s = ""
    for i in range(0, len(b)):
        s = s + twoCharHex(b[i])
    return s

def addV2GTPHeader(exidata):
    #print("type is " + str(type(exidata)))
    if (str(type(exidata)) == "<class 'str'>"):
        #print("changing type to bytearray")
        exidata = exiHexToByteArray(exidata)
    #print("type is " + str(type(exidata)))
    # takes the bytearray with exidata, and adds a header to it, according to the Vehicle-to-Grid-Transport-Protocol
    exiLen = len(exidata)
    header = bytearray(8) # V2GTP header has 8 bytes
                          # 1 byte protocol version
                          # 1 byte protocol version inverted
                          # 2 bytes payload type
                          # 4 byte payload length
    header[0] = 0x01 # version
    header[1] = 0xfe # version inverted
    header[2] = 0x80 # payload type. 0x8001 means "EXI data"
    header[3] = 0x01 # 
    header[4] = (exiLen >> 24) & 0xff # length 4 byte.
    header[5] = (exiLen >> 16) & 0xff
    header[6] = (exiLen >> 8) & 0xff
    header[7] = exiLen & 0xff
    return header + exidata

def removeV2GTPHeader(v2gtpData):
    #removeV2GTPHeader
    return v2gtpData[8:]

def exiDecode(exiHex, prefix="DH"):
    # input: exi data. Either hexstring, or bytearray or bytes
    #        prefix to select the schema
    # if the input is a byte array, we convert it into hex string. If it is already a hex string, we take it as it is.
    #print("type is " + str(type(exiHex)))
    if (str(type(exiHex)) == "<class 'bytearray'>"):
        exiHex = exiByteArrayToHex(exiHex)
    if (str(type(exiHex)) == "<class 'bytes'>"):
        exiHex = exiByteArrayToHex(exiHex)
    param1 = prefix + exiHex # DH for decode handshake
    result = subprocess.run(
        [pathToOpenV2GExe, param1], capture_output=True, text=True)
    if (len(result.stderr)>0):
        print("exiDecode ERROR. stderr:" + result.stderr)
    strConverterResult = result.stdout
    return strConverterResult
    
def exiEncode(strMessageName):
    # todo: handle the schema, the message name and the parameters
    # param1 = "Eh" # Eh for encode handshake, SupportedApplicationProtocolResponse
    # param1 = "EDa" # EDa for Encode, Din, SessionSetupResponse
    param1 = strMessageName
    exiprint("[EXICONNECTOR] exiEncode " + param1)
    result = subprocess.run([pathToOpenV2GExe, param1], capture_output=True, text=True)    
    if (len(result.stderr)>0):
        strConverterResult = "exiEncode ERROR. stderr:" + result.stderr
        print(strConverterResult)
    else:
        try:
            jsondict = json.loads(result.stdout)
            strConverterResult = jsondict["result"]
            strConverterError = jsondict["error"]
            if (len(strConverterError)>0):
                print("[EXICONNECTOR] exiEncode error " + strConverterError)
        except:
            strConverterResult = "exiEncode failed to convert json to dict."
            print(strConverterResult)
    return strConverterResult    
    

def testByteArrayConversion(s):
    print("Testing conversion of " + s)
    x = exiHexToByteArray(s)
    newHexString = exiByteArrayToHex(x)
    print("exi as hex=" + newHexString)
    exiWithHeader = addV2GTPHeader(x)
    exiWithHeaderString = exiByteArrayToHex(exiWithHeader)
    print("with V2GTP header=" + exiWithHeaderString)


def testDecoder(strHex, pre="DH", comment=""):
    global nFail
    strHex = strHex.replace(" ", "") # remove blanks
    print("Decoder test for " + comment + " with data " + strHex)
    decoded=exiDecode(strHex, pre)
    print(decoded)
    if (len(comment)>0):
        strExpected = comment
        if (decoded.find(strExpected)>0):
            print("---pass---")
        else:
            print("---***!!!FAIL!!!***---")
            nFail+=1

def testReadExiFromSnifferFile():
    file1 = open('results\\tmp.txt', 'r')
    Lines = file1.readlines()
    for myLine in Lines:
        if (myLine[0:9]=="[SNIFFER]"):
            posOfEqualsign = myLine.find("=")
            s = myLine[posOfEqualsign+1:] # The part after the "=" contains the EXI hex data.
            s = s.replace(" ", "")
            s = s.replace("\n", "")
            testDecoder(s, "DD", "")

def testReadExiFromExiLogFile(strLogFileName):
    print("Trying to read from ExiLogFile " + strLogFileName)
    try:
        file1 = open(strLogFileName, 'r')
        isFileOk = True
    except:
        print("Could not open " + strLogFileName)
        isFileOk = False
    if (isFileOk):
        fileOut = open(strLogFileName + '.decoded.txt', 'w')
        # example: "ED 809a02004080c1014181c210b8"
        # example with timestamp: "2022-12-20T08:17:15.055755=ED 809a02004080c1014181c21198"
        Lines = file1.readlines()
        for myLine in Lines:
            posOfEqual=myLine.find("=")
            if (posOfEqual>0):
                # we have an equal-sign. Take the string behind it.
                strToDecode=myLine[posOfEqual+1:]
            else:
                # no equal-sign. Take the complete line.
                strToDecode=myLine
            if (myLine[0]=="#"):
                # take-over comment lines into the output
                print(myLine.replace("\n", ""))
                print(myLine.replace("\n", ""), file=fileOut)
            strDecoderSelection = "" # default: unknown line
            if (strToDecode[1:3]=="D "):
                strDecoderSelection = "D" # it is a DIN message
            if (strToDecode[1:3]=="H ") or (strToDecode[1:3]=="h "):
                strDecoderSelection = "H" # it is a ProtocolHandshake message
                
            if (len(strDecoderSelection)>0): # if we have selected a valid decoder
                posOfSpace=2
                s = strToDecode[posOfSpace+1:] # The part after the " " contains the EXI hex data.
                s = s.replace(" ", "") # Remove blanks
                s = s.replace("\n", "") # Remove line feeds
                decoded=exiDecode(s, "D"+strDecoderSelection)
                print(myLine.replace("\n", "") + " means:")
                print(decoded)
                print(myLine.replace("\n", "") + " means:", file=fileOut)            
                print(decoded, file=fileOut)            
        fileOut.close()

def testTimeConsumption():
    strHex = "809a001150400000c80006400000"
    pre = "DD"
    tStart = time.time()
    nRuns = 100
    for i in range(0, nRuns):
        decoded=exiDecode(strHex, pre)
    tStop = time.time()
    elapsed_time = tStop - tStart
    print("Decoder: Execution time for " + str(nRuns) + " runs:", elapsed_time, "seconds")

    tStart = time.time()
    nRuns = 100
    for i in range(0, nRuns):
        s = exiEncode("EDC_1122334455667788")
    tStop = time.time()
    elapsed_time = tStop - tStart
    print("Encoder: Execution time for " + str(nRuns) + " runs:", elapsed_time, "seconds")
    

if __name__ == "__main__":
    nFail=0
    print("Testing exiConnector...")
    testReadExiFromExiLogFile('DemoExiLog.txt')
    testReadExiFromExiLogFile('PevExiLog.txt')
    exit()        
