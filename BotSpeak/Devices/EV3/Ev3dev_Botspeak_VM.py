#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
#from os import curdir, sep, listdir
import os,sys
import cgi
import thread
import threading
import time

# do I need these? 
info = True
servo = False
IR = False
timer = False
com = False
pwm = False

# list of commands
COMMANDS = ['SET','GET','SCRIPT','ENDSCRIPT','WAIT','ADD','SUB','MUL','DIV','MOD','AND','OR','NOT','IF','BSR','BSL','GOTO','LBL','RUN','EQL','GRT','GRE','LEE','LET']

# variable dictionary
VARS = {}

# motor dictionary
MOTORS = {}

# sensor dictionary
SENSORS = {}


# list of hardware variables
setVar = ['DIO','PWM','AO','SERVO','TMR','COM']
getVar = ['DIO','AI']

PORT_NUMBER = 2012

####### linux path names on EV3DEV #######
#motor definitions
motorAttached = '/sys/class/tacho-motor/'
motorpath = '/sys/class/tacho-motor/{}/'
setMotorSpeed = motorpath + 'duty_cycle_sp'
runMotor = motorpath + 'command'

# check if this is true 
checkMotorPort = motorpath + 'port_name' 

#LED definitions

ledpath = '/sys/class/leds/ev3-{}:{}:ev3dev/'
ledbright = ledpath +'brightness'

#sensor definitions

sensorpath = '/sys/class/lego-sensor/{}/'
sensorValue = sensorpath + 'value0'
sensorAttached = '/sys/class/lego-sensor/'
checkSensorPort = sensorpath + 'port_name'
drivername = sensorpath + 'driver_name'

#This class will handle any incoming request from LabView
class myHandler(BaseHTTPRequestHandler):
        
        #Handler for the POST requests
        def do_POST(self):
                length = self.headers.getheader('content-length')
                theScript = self.rfile.read(int(length)).rstrip('/r/n')
                scriptOrCommand(theScript)
                        
#This is a thread that runs the web server 
def WebServerThread():                  
        try:
                #Create a web server and define the handler to manage the incoming request
                server = HTTPServer(('', PORT_NUMBER), myHandler)
                print 'Started httpserver on port ' , PORT_NUMBER
                
                #Wait forever for incoming http requests
                server.serve_forever()

        except (KeyboardInterrupt,SystemExit):
                print '^C received, shutting down the web server'
                server.socket.close()
                

# Runs the web server thread 
thread.start_new_thread(WebServerThread,())             

# deals with script or single commands accordingly
def scriptOrCommand(script):
        # reset variable dictionary 
        VARS = {}
        
        command,space,rest = script.partition(' ')
        
        if 'SCRIPT' in command:
                # save script as an array
                global scriptArray
                scriptArray = []
                scriptArray = script.split('&')
                scriptSize = len(scriptArray)

                # get run command line number
                runCommand = scriptArray[scriptSize-1]

                # delete SCRIPT and ENDSCRIPT
                scriptArray = scriptArray[1:scriptSize-2]
                print scriptArray

                # execute RUN command
                ExecuteCommand(runCommand)

        # for single commands
        elif command in COMMANDS:
                ExecuteCommand(script)

        else:
                print 'no command sent or unsupported command'

# Loop through commands
def runScript(start):
        # run commands from script array starting at line 'start'

        # set lineNum as line number in VARS
        VARS['lineNum'] = 0
        arraySize = len(scriptArray)
        
        while (VARS['lineNum']<arraySize):
##                print 'line number is ' + str(VARS['lineNum'])
                ExecuteCommand(scriptArray[VARS['lineNum']])
                VARS['lineNum'] += 1
                
#Execute BotSpeak Command
def ExecuteCommand(command):
        if command == '':
                return command
        
        cmd,space,value = command.partition(' ')
        channel = '0'
        source = ''
        
        if ',' in value:
                source,space,value = value.partition(',')
                if '[' in source:
                        source,space,channel = source.partition('[')
                        channel = channel.split(']')[0]
                elif '[' in value:
                        place,space,chan = value.partition('[')
                        channel = chan.split(']')[0]
                        value = Read(place,channel)
                
        elif '[' in value:
                source,space,channel = value.partition('[')
                channel = channel.split(']')[0]
        
        try:        
                value = float(value)
                channel = int(channel)
        except(ValueError):
                print 'value or channel is not a number'
        
        print cmd
        print value
        print source
        
        # BotSpeak Commands
        if cmd == 'SET':
                if source in setVar:
                        Assign(source,channel,value)
                elif value in VARS:
                        VARS[source] = VARS[value]
                # value is a number
                else:
                        VARS[source] = value
                print 'setting command'
                print source
                print value
                
        elif cmd == 'GET':
                if source in getVar:
                        print 'Reading '+source+' [' + channel + ']'
                        return Read(source,channel)
                elif value in VARS:
                        return VARS[value]
                elif value == 'IP':
                        return "192.168.2.3"
                elif value == 'VER':
                        return "version 2"
                else:
                        print 'variable not SET or incorrect source name'
                
        elif cmd == 'WAIT':
                if value in VARS:
                        value = VARS[value]
                waitTime = value / 1000
                time.sleep(waitTime)
                return value
        
        elif cmd == 'ADD':
                if value in VARS:
                        value = VARS[value]
                VARS[source] += value
                return VARS[source]

        elif cmd == 'SUB':
                if value in VARS:
                        value = VARS[value]
                VARS[source] -= value
                return VARS[source]

        elif cmd == 'MUL':
                if value in VARS:
                        value = VARS[value]
                VARS[source] *= value
                return VARS[source]

        elif cmd == 'DIV':
                if value in VARS:
                        value = VARS[value]
                VARS[source] /= value
                return VARS[source]

        elif cmd == 'MOD':
                if source in VARS:
                        if value in VARS:
                                value = VARS[value]
                        VARS[source] %= value
                        return VARS[source]
                else:
                        return source % value

        elif cmd == 'AND':
                if value in VARS:
                        value = VARS[value]
                VARS[source] &= value
                return VARS[source]

        elif cmd == 'OR':
                if value in VARS:
                        value = VARS[value]
                VARS[source] |= value
                return VARS[source]
        
        elif cmd == 'BSL':
                if value in VARS:
                        value = VARS[value]
                VARS[source] <<= value
                return VARS[source]

        elif cmd == 'BSR':
                if value in VARS:
                        value = VARS[value]
                VARS[source] >>= value
                return VARS[source]

        elif cmd == 'GOTO':
                value = int(value) - 1
                VARS['lineNum'] = value
                
        elif cmd == 'IF':
                #parse IF statement
                var,space,rest = value.partition(' ')
                # theSource
                theSource = var[1:]
                # cond
                cond,space,rest = rest.partition(' ')
                # theValue
                theValue,parenth,rest = rest.partition(') ')
                #gotoLine
                goto,space,gotoLine = rest.partition(' ')

##                print theSource
##                print theValue
##                print cond
        
                if cond == '=':
                        ExecuteCommand('EQL '+ theSource + ',' + theValue)
                        comp = VARS[theSource]

                elif cond == '<':
                        ExecuteCommand('LET '+ theSource + ',' + theValue)
                        comp = VARS[theSource]

                elif cond == '<=':
                        ExecuteCommand('LEE '+ theSource + ',' + theValue)
                        comp = VARS[theSource]

                elif cond == '>':
                        ExecuteCommand('GRT '+ theSource + ',' + theValue)
                        comp = VARS[theSource]

                elif cond == '>=':
                        ExecuteCommand('GRE '+ theSource + ',' + theValue)
                        comp = VARS[theSource]

                elif cond == '!=':
                        ExecuteCommand('NOT '+ theSource + ',' + theValue)
                        comp = VARS[theSource]

                else:
                        comp = 'comparison is not supported'

                    
                if comp:
                        print 'TRUE'
                        ExecuteCommand('GOTO '+ gotoLine)
                else:
                        print 'FALSE'
                        
                        
        elif cmd == 'EQL':
                #saving variable to update VARS dictionary later
                test = source
                [source,value] = compCheck(source,value,channel)
                try:
                        print 'Equals'
                        print source
                        print value
##                        source = float(source)
##                        value = float(value)
                        
                        if (source == value):
                                print 'True'
                                VARS[test] = True        
                        else:
                                print 'False'
                                VARS[test] = False
                except ValueError:
                        print 'a variable has not yet been defined'
                        # return error message
                        

        elif cmd == 'GRT':
                #saving variable to update VARS dictionary later
                test = source
                [source,value] = compCheck(source,value,channel)
                try:      
                        source = float(source)
                        value = float(value)
                        
                        if (source > value):
                                print 'True'
                                VARS[test] = True        
                        else:
                                print 'False'
                                VARS[test] = False
                except ValueError:
                        print 'a variable has not yet been defined'
                        # return error message

        elif cmd == 'GRE':
                #saving variable to update VARS dictionary later
                test = source
                [source,value] = compCheck(source,value,channel)
                print source
                print value
                try:      
                        source = float(source)
                        value = float(value)
                        
                        if (source >= value):
                                print 'True'
                                VARS[test] = True        
                        else:
                                print 'False'
                                VARS[test] = False
                except ValueError:
                        print 'a variable has not yet been defined'
                        # return error message

        elif cmd == 'LET':
                #saving variable to update VARS dictionary later
                test = source
                [source,value] = compCheck(source,value,channel)
                try:      
                        source = int(source)
                        value = int(value)
                        
                        if (source < value):
                                print 'True'
                                VARS[test] = True        
                        else:
                                print 'False'
                                VARS[test] = False
                except ValueError:
                        print 'a variable has not yet been defined'
                        # return error message

        elif cmd == 'LEE':
                #saving variable to update VARS dictionary later
                test = source
                [source,value] = compCheck(source,value,channel)
                try:      
                        source = float(source)
                        value = float(value)
                        
                        if (source <= value):
                                print 'True'
                                VARS[test] = True        
                        else:
                                print 'False'
                                VARS[test] = False
                except ValueError:
                        print 'a variable has not yet been defined'
                        # return error message
                        
        elif cmd == 'NOT':
                #saving variable to update VARS dictionary later
                test = source
                [source,value] = compCheck(source,value,channel)
                try:      
                        source = float(source)
                        value = float(value)
                        
                        if (source != value):
                                print 'True'
                                VARS[test] = True        
                        else:
                                print 'False'
                                VARS[test] = False
                except ValueError:
                        print 'a variable has not yet been defined'
                        # return error message
        elif cmd == 'RUN':
                runScript(int(value))

        elif cmd == 'SCRIPT':
                print 'begin script'
                # shouldn't be sent through

        elif cmd == 'ENDSCRIPT':
                print 'end script'
                # shouldn't be sent through
                
        elif '//' in cmd:
               print 'comment' 
                
        else:
                return (cmd + " not yet supported or you have not initially SET your variable")
        

# assign value to certain source
def Assign(source,chan,val):
        if source == 'DIO':
                DIO(chan,val)

        elif source == 'PWM':
                PWM(chan,val)
                
        elif source == 'AO':
                AO(chan,val)

        elif source == 'TMR':
                TMR(val)

        elif source == 'SERVO':
                PWM(chan,val)
                #SERVO(chan,val)
                
        elif source == 'COM':
                COM(chan,val)                               

# read value from a source
def Read(source,chan):
        if source == 'DIO':
                return readDIO(chan)
        elif source == 'AI':
                return AI(chan)


# ports A,B,C,D
def PWM(channel,value):
        port=int(channel)
        speed = int(float(value))
        
        # motor dictionary {'actual Ev3 port':'motor0'}
        existingMotors = os.listdir(motorAttached)
        MOTORS = {} # reset dictionary

        for i in range(0,len(existingMotors)):
                try:
                        motorRead = open(checkMotorPort.format(existingMotors[i])) 
                        mo = motorRead.read()
                        motorRead.close
                        print mo
                        print mo[3]
                        
                        MOTORS[mo[3]] = existingMotors[i] # add new motor to dictionary
                except IOError:
                        print "no motor"
                        
                
        if port in range(0,3):
                port = changePort(port)
                motor = open(setMotorSpeed.format(MOTORS[port]),'w',0) 
                motor.write(speed + '\n')
                motor.close
                motorRun = open(runMotor.format(MOTORS[port]),'w',0)
                if speed == 0: #stop 
                        motor.write('stop')
                else:# run motor
                        motor.write('run-forever')
                motor.close
        else:
                print 'no motor attached to port'
        
# ports A,B,C,D
def AO(channel,value):
        return 1024

# ports 1,2,3,4
def AI(channel):
        # sensor dictionary {'actual Ev3 port':'sensor0'}
        existingSensors = os.listdir(sensorAttached)

        # reset dictionary
        SENSORS = {} 

        for i in range(0,len(existingSensors)):
                try:
                        senRead = open(checkSensorPort.format(existingSensors[i])) 
                        print senRead
                        mo = senRead.read()
                        print mo
                        senRead.close
                        SENSORS[mo[2]] = existingSensors[i] # add to dictionary
                except IOError:
                        print "no sensor"
        print SENSORS
                
        if channel in SENSORS:
                # read value
                chan = str(channel)
                Sens = open(sensorValue.format(SENSORS[chan]))
                theValue = Sens.read()
                Sens.close

                # ask what sensor is plugged in - theSensor
                sensor = open(drivername.format(SENSORS[chan]))
                theSensor = sensor.read()
                print theSensor # may want to do something with the sensor name later
                sensor.close
                
        return theValue
        

# DIO write
# value: 0 = Right Red, 1 = Left Red, 2 = Right Green, 3 = Left Green
def DIO(channel,value):
                
        if channel == 0:
                LED = open(ledbright.format('right0','red'),"w",0)
        elif channel == 1:
                LED = open(ledbright.format('left0','red'),"w",0)
        elif channel == 2: 
                LED = open(ledbright.format('right1','green'),"w",0)
        elif channel == 3:
                LED = open(ledbright.format('left1','green'),"w",0)                
        else:
                print 'no LED in this pin, choose from pins 0-3'

        
        if value:
                LED.write('255\n')
                print value
        else:
                LED.write('0\n')
                print value
        LED.close
                
# DIO read
def readDIO(chan):
        if chan == '0':
                LED = open(ledbright.format('right0','red'),'r+',0)
        elif chan == '1':
                LED = open(ledbright.format('left0','red'),'r+',0)
        elif chan == '2':
                LED = open(ledbright.format('right1','green'),'r+',0)
        elif chan == '3':
                LED = open(ledbright.format('left1','green'),'r+',0)
       
        theValue = LED.read()
        print theValue
        LED.close

        theValue = theValue.strip()
        theValue = int(theValue)
        if theValue == 255:
                return '1'
        elif theValue == 0:
                return '0'

def TMR(channel,value):
        timer = True
def SERVO(channel,value):
        servo = True
def COM(channel,value):
        com = False


# port 0,1,2,3 to A,B,C,D
def changePort(portNum):
        if portNum in range(0,3):
                if portNum == 0:
                        value = 'A'
                elif portNum == 1:
                        value = 'B'
                elif portNum == 2:
                        value = 'C'
                elif portNum == 3:
                        value = 'D'
                else:
                        value = ''
                return value
        
# check if a variable is in the variable dictionary
def checkVARS(value):
        if value in VARS:
                return VARS[value]
        else:
                return "variable does not exist"

# command check for comparisons
def compCheck(source,value,channel):
        if source in COMMANDS:
                source = Read(source,channel)
        if value in VARS:
                value = VARS[value]
        if source in VARS:
                source = VARS[source]
        return [source,value]

while True:
        time.sleep(0.5)
        

