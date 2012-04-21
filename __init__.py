# -*- coding: utf-8 -*-
#
# plugins/Pioneer_AV_NET/__init__.py
# 
# This file is a plugin for EventGhost.
# Copyright (C) 2005-2009 Lars-Peter Voss <bitmonster@eventghost.org>
#
# EventGhost is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by the
# Free Software Foundation;
#
# EventGhost is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

import eg
import socket
import select
import re
from time import sleep
from threading import Event, Thread

eg.RegisterPlugin(
    name = "Pioneer_AV_NET",
    author = "Sem;colon (based on OnkyoISCP plugin by Alexander Hartmaier)",
    version = "0.2",
    kind = "external",
    description = "Control Pioneer A/V Receivers via Ethernet (Tested with VSX-921-K)"
)

class Text:
    tcpBox = "TCP/IP Settings"
    ip = "IP:"
    port = "Port:"
    timeout = "Timeout:"
    class SendCommand:
        commandBox = "Command Settings"
        command = "Code to send:"

class Pioneer_AV_NET(eg.PluginBase):
    text = Text

    def __init__(self):
        self.AddAction(SendCommand)

    def __start__(self, ip, port, timeout):
        self.ip = ip
        self.port = int(port)
        self.timeout = float(timeout)
        self.Connect()
        self.stopThreadEvent = Event()
        thread = Thread(
            target=self.Receive,
            args=(self.stopThreadEvent, )
        )
        thread.start()

    def __stop__(self):
        self.stopThreadEvent.set()
    	self.socket.close()

    def Receive(self, stopThreadEvent):
        while not stopThreadEvent.isSet():
            try:
                ready = select.select([self.socket], [], [])
                # the first element of the returned list is a list of readable sockets
                if ready[0]:
                    # 1024 bytes should be enough for every received event
                    response = self.socket.recv(1024)
                    # splits the received string in substrings for every event
                    splitter="\r\n"
                    responseArray=response.split(splitter)
                    responseArrayLen=len(responseArray)-1
                    for i in range(0, responseArrayLen, 1):
                        response=responseArray[i]
                        if response!="":
                            if response[:3]=="VOL":
                                response1=response[:3]
                                response2=response[3:]
                                self.TriggerEvent(response1, payload=response2)
                            elif response[:3]=="FRF":
                                response1=response[:3]
                                response2=response[3:]
                                self.TriggerEvent(response1, payload=response2)
                            elif response[:2]=="FL":
                                # data displayed on the receiver
                                response1=response[:2]
                                response2=response[2:]
                                response3=""
                                while response2!="":
                                    # converts hex to ascii
                                    character=int(response2[:2], 16)
                                    if character==5:
                                        character="|)"
                                    elif character==6:
                                        character="(|"
                                    elif character==8:
                                        character="II"
                                    else:
                                        character=chr(character)
                                    response3=response3+character
                                    response2=response2[2:len(response2)]
                                response4=unicode(re.sub(" ", "&nbsp;", response3[1:]), 'latin-1', 'replace')
                                #displays the data as an event with payload:
                                #self.TriggerEvent(response1, payload=response4)
                                #saves the data to the variale "AVDisplay": 
                                eg.globals.AVDisplay=response4
                            elif len(response)<=10:
                                self.TriggerEvent(response)
                            else:
                                print response
                            sleep(0.01)        
            except Exception as e:
                print "Pioneer_AV_NET ERROR:",e
                if "10054" in e:
                    print "trying to reconnect"
                    self.plugin.Connect()
                stopThreadEvent.wait(3.0)
        self.TriggerEvent("ThreadStopped!")

    def Connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(self.timeout)
        self.socket = s

        ip = self.ip
        port = self.port
        try:
            s.connect((ip, port))
        except Exception as e:
            print "Failed to connect to " + ip + ":" + str(port), e
        else:
            print "Connected to " + ip + ":" + str(port)

    def Configure(self, ip="", port="8102", timeout="1"):
        text = self.text
        panel = eg.ConfigPanel()
        wx_ip = panel.TextCtrl(ip)
        wx_port = panel.SpinIntCtrl(port, max=65535)
        wx_timeout = panel.TextCtrl(timeout)

        st_ip = panel.StaticText(text.ip)
        st_port = panel.StaticText(text.port)
        st_timeout = panel.StaticText(text.timeout)
        eg.EqualizeWidths((st_ip, st_port, st_timeout))

        tcpBox = panel.BoxedGroup(
            text.tcpBox,
            (st_ip, wx_ip),
            (st_port, wx_port),
            (st_timeout, wx_timeout),
        )

        panel.sizer.Add(tcpBox, 0, wx.EXPAND)

        while panel.Affirmed():
            panel.SetResult(
                wx_ip.GetValue(),
                wx_port.GetValue(),
                wx_timeout.GetValue(),
            )

class SendCommand(eg.ActionBase):

    def __call__(self, Command):
        line = Command + "\x0D"
        try:
            self.plugin.socket.sendall(line)
            sleep(0.1)
        except socket.error, msg:
            print "Error sending command, retrying", msg
            # try to reopen the socket on error
            # happens if no commands are sent for a long time
            # and the tcp connection got closed because
            # e.g. the receiver was switched off and on again
            self.plugin.Connect()
            try:
                self.plugin.socket.sendall(line)
            except socket.error, msg:
                print "Error sending command", msg

    def Configure(self, Command=""):
        panel = eg.ConfigPanel()
        text = self.text
        st_command = panel.StaticText(text.command)
        wx_command = panel.TextCtrl(Command)

        commandBox = panel.BoxedGroup(
            text.commandBox,
            (st_command, wx_command)
        )

        panel.sizer.Add(commandBox, 0, wx.EXPAND)

        while panel.Affirmed():
            panel.SetResult(wx_command.GetValue())
