
# This module handles the IPv6 related functionality of the communication between charging station and car.
#
# It has the following sub-functionalities:
# - IP.UDP.SDP: listen to requests from the car, and responding to them.
#   Eth --> IPv6 --> UDP --> V2GTP --> SDP
#                                       |
#                                       v
#   Eth <-- IPv6 <-- UDP <-- V2GTP <-- SDP
#
#
# Abbreviations:
# SECC: Supply Equipment Communication Controller. The "computer" of the charging station.
# EVCC: Electric Vehicle Communication Controller. The "computer" of the vehicle.
# SDP: SECC Discovery Protocol. The UDP based protocol to find out the IP address of the charging station.
# SLAAC: Stateless auto address configuration (not SLAC!). A method to automatically set IPv6 address, based
#        on the 6 byte MAC address.

from helpers import showAsHex
import udpChecksum


class ipv6handler():
    def fillMac(self, macbytearray, position=6): # position 6 is the source MAC
        for i in range(0, 6):
            self.EthResponse[6+i] = macbytearray[i]
            
    def packResponseIntoEthernet(self, buffer):
        # packs the IP packet into an ethernet packet
        self.EthResponse = bytearray(len(buffer) + 6 + 6 + 2) # Ethernet header needs 14 bytes:
                                                      #  6 bytes destination MAC
                                                      #  6 bytes source MAC
                                                      #  2 bytes EtherType
        for i in range(0, 6): # fill the destination MAC with the source MAC of the received package
            self.EthResponse[i] = self.myreceivebuffer[6+i]
        self.fillMac(self.ownMac) # bytes 6 to 11 are the source MAC
        self.EthResponse[12] = 0x86 # 86dd is IPv6
        self.EthResponse[13] = 0xdd
        for i in range(0, len(buffer)):
            self.EthResponse[14+i] = buffer[i]
        self.transmit(self.EthResponse)
        
                                                      
    def packResponseIntoIp(self, buffer):
        # embeds the (SDP) response into the lower-layer-protocol: IP, Ethernet
        self.IpResponse = bytearray(len(buffer) + 8 + 16 + 16) # IP6 needs 40 bytes:
                                                      #   4 bytes traffic class, flow
                                                      #   2 bytes destination port
                                                      #   2 bytes length (incl checksum)
                                                      #   2 bytes checksum
        self.IpResponse[0] = 0x60 # traffic class, flow
        self.IpResponse[1] = 0
        self.IpResponse[2] = 0
        self.IpResponse[3] = 0
        plen = len(buffer) # length of the payload. Without headers.
        self.IpResponse[4] = plen >> 8
        self.IpResponse[5] = plen & 0xFF
        self.IpResponse[6] = 0x11 # next level protocol, 0x11 = UDP in this case
        self.IpResponse[7] = 0x0A # hop limit
        for i in range(0, 16):
            self.IpResponse[8+i] = self.SeccIp[i] # source IP address
        for i in range(0, 16):
            self.IpResponse[24+i] = self.EvccIp[i] # destination IP address
        for i in range(0, len(buffer)):
            self.IpResponse[40+i] = buffer[i]
        showAsHex(self.IpResponse, "IP response ")
        self.packResponseIntoEthernet(self.IpResponse)


    def packResponseIntoUdp(self, buffer):
        # embeds the (SDP) response into the lower-layer-protocol: UDP
        self.UdpResponse = bytearray(len(buffer) + 8) # UDP needs 8 bytes:
                                                      #   2 bytes source port
                                                      #   2 bytes destination port
                                                      #   2 bytes length (incl checksum)
                                                      #   2 bytes checksum
        self.UdpResponse[0] = 15118 >> 8
        self.UdpResponse[1] = 15118 & 0xFF
        self.UdpResponse[2] = self.evccPort >> 8
        self.UdpResponse[3] = self.evccPort  & 0xFF
        lenInclChecksum = len(buffer) + 8
        self.UdpResponse[4] = lenInclChecksum >> 8
        self.UdpResponse[5] = lenInclChecksum & 0xFF
        # checksum will be calculated afterwards
        self.UdpResponse[6] = 0
        self.UdpResponse[7] = 0
        for i in range(0, len(buffer)):
            self.UdpResponse[8+i] = buffer[i]
        showAsHex(self.UdpResponse, "UDP response ")
        # The content of buffer is ready. We can calculate the checksum. see https://en.wikipedia.org/wiki/User_Datagram_Protocol
        checksum = udpChecksum.calculateUdpChecksumForIPv6(self.UdpResponse, self.SeccIp, self.EvccIp)   
        self.UdpResponse[6] = checksum >> 8
        self.UdpResponse[7] = checksum & 0xFF        
        self.packResponseIntoIp(self.UdpResponse)
        
    def sendSdpResponse(self):
        # SECC Discovery Response.
        # The response from the charger to the EV, which transfers the IPv6 address of the charger to the car.
        self.SdpPayload = bytearray(20) # SDP response has 20 bytes
        for i in range(0, 16):
            self.SdpPayload[i] = self.SeccIp[i] # 16 bytes IP address of the charger
        self.SdpPayload[16] = 15118 >> 8 # SECC port high byte. Port is always 15118.
        self.SdpPayload[17] = 15118 & 0xFF # SECC port low byte. Port is always 15118.
        self.SdpPayload[18] = 0x10 # security. We only support "no transport layer security, 0x10".
        self.SdpPayload[19] = 0x00 # transport protocol. We only support "TCP, 0x00".
        showAsHex(self.SdpPayload, "SDP payload ")
        # add the SDP header
        lenSdp = len(self.SdpPayload)
        self.V2Gframe = bytearray(lenSdp + 8) # V2GTP header needs 8 bytes:
                                                    # 1 byte protocol version
                                                    # 1 byte protocol version inverted
                                                    # 2 bytes payload type
                                                    # 4 byte payload length
        self.V2Gframe[0] = 0x01 # version
        self.V2Gframe[1] = 0xfe # version inverted
        self.V2Gframe[2] = 0x90 # payload type. 0x9001 is the SDP response message
        self.V2Gframe[3] = 0x01 # 
        self.V2Gframe[4] = (lenSdp >> 24) & 0xff # length 4 byte.
        self.V2Gframe[5] = (lenSdp >> 16) & 0xff
        self.V2Gframe[6] = (lenSdp >> 8) & 0xff
        self.V2Gframe[7] = lenSdp & 0xff
        for i in range(0, lenSdp):
            self.V2Gframe[8+i] = self.SdpPayload[i]
        showAsHex(self.V2Gframe, "V2Gframe ")
        self.packResponseIntoUdp(self.V2Gframe)
        
    def evaluateUdpPayload(self):
        if (self.destinationport == 15118): # port for the SECC
            if ((self.udpPayload[0]==0x01) and (self.udpPayload[1]==0xFE)): # protocol version 1 and inverted
                # it is a V2GTP message
                showAsHex(self.udpPayload, "V2GTP ")
                self.evccPort = self.sourceport
                v2gptPayloadType = self.udpPayload[2] * 256 + self.udpPayload[3]
                # 0x8001 EXI encoded V2G message
                # 0x9000 SDP request message (SECC Discovery)
                # 0x9001 SDP response message (SECC response to the EVCC)
                if (v2gptPayloadType == 0x9000):
                    v2gptPayloadLen = self.udpPayload[4] * 256 ** 3 + self.udpPayload[5] * 256 ** 2 + self.udpPayload[6] * 256 + self.udpPayload[7]
                    if (v2gptPayloadLen == 2):
                        # 2 is the only valid length for a SDP request.
                        seccDiscoveryReqSecurity = self.udpPayload[8] # normally 0x10 for "no transport layer security". Or 0x00 for "TLS".
                        seccDiscoveryReqTransportProtocol = self.udpPayload[9] # normally 0x00 for TCP
                        if (seccDiscoveryReqSecurity!=0x10):
                            print("seccDiscoveryReqSecurity " + str(seccDiscoveryReqSecurity) + " is not supported")
                        else:    
                            if (seccDiscoveryReqTransportProtocol!=0x00):
                                print("seccDiscoveryReqTransportProtocol " + str(seccDiscoveryReqTransportProtocol) + " is not supported")
                            else:
                                # This was a valid SDP request. Let's respond, if we are the charger.
                                print("ok, this was a valid SDP request")
                                if (self.iAmEvse==1):
                                    print("We are the SECC. Sending SDP response.")
                                    self.sendSdpResponse()
                    else:
                        print("v2gptPayloadLen on SDP request is " + str(v2gptPayloadLen) + " not supported")
                else:        
                    print("v2gptPayloadType " + hex(v2gptPayloadType) + " not supported")
                    
    def enterPevMode(self):
        self.iAmEvse = 0 # not emulating a charging station
        self.iAmPev = 1 # emulating a vehicle
    def enterEvseMode(self):
        self.iAmEvse = 1 # emulating a charging station
        self.iAmPev = 0 # not emulating a vehicle
    def enterListenMode(self):
        self.iAmEvse = 0 # not emulating a charging station
        self.iAmPev = 0 # not emulating a vehicle

    def evaluateReceivedPacket(self, pkt):
        if (len(pkt)>60):
            self.myreceivebuffer = pkt
            self.nextheader = self.myreceivebuffer[20]
            if (self.nextheader == 0x11): # it is an UDP frame
                self.sourceport = self.myreceivebuffer[54] * 256 + self.myreceivebuffer[55]
                self.destinationport = self.myreceivebuffer[56] * 256 + self.myreceivebuffer[57]
                self.udplen = self.myreceivebuffer[58] * 256 + self.myreceivebuffer[59]
                self.udpsum = self.myreceivebuffer[60] * 256 + self.myreceivebuffer[61]
                # udplen is including 8 bytes header at the begin
                if (self.udplen>8):
                    self.udpPayload = bytearray(self.udplen-8)
                    # print("self.udplen=" + str(self.udplen))
                    # print("self.myreceivebuffer len=" + str(len(self.myreceivebuffer)))
                    for i in range(0, self.udplen-8):
                        #print("index " + str(i) + " " + hex(self.myreceivebuffer[62+i]))
                        self.udpPayload[i] = self.myreceivebuffer[62+i]
                    self.evaluateUdpPayload()
                        
    def __init__(self, transmitCallback):
        self.enterEvseMode()
        self.transmit = transmitCallback
        self.SeccIp = [ 0xfe, 0x80, 0, 0, 0, 0, 0, 0, 0x06, 0xaa, 0xaa, 0xff, 0xfe, 0, 0xaa, 0xaa ] # 16 bytes, a default IPv6 address for the charging station
        self.EvccIp = [ 0xfe, 0x80, 0, 0, 0, 0, 0, 0, 0x06, 0x65, 0x65, 0xff, 0xfe, 0, 0x64, 0xC3 ] # 16 bytes, a default IPv6 address for the vehicle
        self.ownMac = [ 0x01, 0x02, 0x03, 0x04, 0x05, 0x06 ] # 6 bytes own MAC default. Should be overwritten before use.
    