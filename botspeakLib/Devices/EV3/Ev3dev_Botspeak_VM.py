#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
#from os import curdir, sep, listdir
import os,sys
import cgi
import thread
import threading
# look at time import
import time

# do I need these? 
info = True
servo = False
IR = False
timer = False
com = False
pwm = False

# list of commands
COMMANDS = ['SET','GET','SCRIPT','ENDSCRIPT','WAIT','ADD','SUB','MUL','DIV','MOD','AND','OR','NOT','IF','BSR','BSL','GOTO','LBL','RUN']

# variable dictionary
VARS = {}

# motor dictionary
MOTORS = {}

# sensor dictionary
SENSORS = {}

# list of script commands
scriptArray = []

# list of hardware variables
setVar = ['DIO','PWM','AO','SERVO','TMR','COM']
getVar = ['DIO','AI']

PORT_NUMBER = 2012

####### linux path names on EV3DEV #######
#motor definitions
motorAttached = '/sys/class/tacho-motor/'
motorpath = '/sys/class/tacho-motor/{}/'
setMotorSpeed = motorpath + 'duty_cycle_sp'
runMotor = motorpath + 'run'
# check if this is true 
checkMotorPort = motorpath + 'port_name' 

#LED definitions

ledpath = '/sys/class/leds/ev3:{}:{}/'
ledbright = ledpath +'brightness'

#sensor definitions

sensorpath = '/sys/class/lego-sensor/{}/'
sensorAttached = '/sys/class/lego-sensor/'
checkSensorPort = sensorpath + 'port_name'
drivername = sensorpath + 'driver_name'

ultrasonicpath = 'ev3-uart-30'
ultrasonicmode = 'US-DIST-CM'
ultrasonicvalue = 'value0'

gyroname = 'ev3-uart-32' 
gyromode = 'GYRO-ANGLE'
gyrovalue = 'value0'

touchname = 'ev3-touch'
touchmode = 'TOUCH'
touchvalue = 'value0'

irname = 'ev3-uart-33'
irmode = 'IR-PROX'
irvalue = 'value0'

analogname = 'ev3-analog'
analogvalue = 'value0'

#This class will handle any incoming request from LabView
class myHandler(BaseHTTPRequestHandler):
        
        #Handler for the GET requests
        def do_GET(self):
                theScript = '' + self.rfile.read()
                print theScript
                scriptOrCommand(theScript)
                

        #Handler for the POST requests
        def do_POST(self):
                theScript = self.rfile.read()
                print theScript
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
        command,space,rest = script.partition(' ')

        if 'SCRIPT' in command:
                # save script as an array
                scriptArray = script.split('\n')

                # run command
                runCommand = scriptArray[scriptArray.len()-1]
                
                # get rid of endscript and run 
                scriptArray = scriptArray[0:scriptArray.len()-3]

                # execute RUN command
                ExecuteCommand(runCommand)

        # for single commands
        elif command in COMMANDS:
                theCom = script.split('\n')
                ExecuteCommand(theCom[0])

        else:
                print 'no command sent or unsupported command'

# Loop through commands
def runScript(start):
        # run commands from script array starting at line 'start'
        # think about assigning global variable to current line number in script
        for i in range(start, scriptArray.len()-1): 
                response = ExecuteCommand(scriptArray[i])
                print response
                
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
                        chan = chan.split(']')[0]
                        value = Read(place,chan)
                
        elif '[' in value:
                source,space,channel = value.partition('[')
                channel = channel.split(']')[0]
        
        # BotSpeak Commands
        if cmd == 'SET':
                if source in setVar:
                        print 'Setting '+source+' [' + channel + '] to ' + value
                        Assign(source,channel,value)
                elif value in VARS:
                        VARS[int(source)] = VARS[int(value)]
                # value is a number
                else:
                        VARS[source] = int(value)
                        
        elif cmd == 'GET':
                if source in getVar:
                        print 'Reading '+source+' [' + channel + ']'
                        return Read(source,channel)
                elif value in VARS:
                        VARS[value]
                elif value == 'IP':
                        return "192.168.2.3"
                elif value == 'VER':
                        return "version 1"
                else:
                        print 'variable not SET or incorrect source name'
                
        elif cmd == 'WAIT':
                waitTime = float(value) / 1000
                time.sleep(waitTime)
                return value
        
        elif cmd == 'ADD':
                if value in VARS:
                        value = VARS[value]
                VARS[source] += int(value)
                return VARS[source]

        elif cmd == 'SUB':
                if value in VARS:
                        value = VARS[value]
                VARS[source] -= int(value)
                return VARS[source]

        elif cmd == 'MUL':
                if value in VARS:
                        value = VARS[value]
                VARS[source] *= int(value)
                return VARS[source]

        elif cmd == 'DIV':
                if value in VARS:
                        value = VARS[value]
                VARS[source] /= int(value)
                return VARS[source]

        elif cmd == 'MOD':
                if source in VARS:
                        if value in VARS:
                                value = VARS[value]
                        VARS[source] %= int(value)
                        return VARS[source]
                else:
                        return int(source) % int(value)

        elif cmd == 'AND':
                if value in VARS:
                        value = VARS[value]
                VARS[source] &= value
                return VARS[source]

        elif cmd == 'OR':
                if value in VARS:
                        value = VARS[value]
                VARS[source] |= int(value)
                return VARS[source]
        
        elif cmd == 'NOT':
                if value in VARS:
                        value = VARS[value]
                VARS[source] != int(value)
                return VARS[source]
        
        elif cmd == 'BSL':
                if value in VARS:
                        value = VARS[value]
                VARS[source] <<= int(value)
                return VARS[source]

        elif cmd == 'BSR':
                if value in VARS:
                        value = VARS[value]
                VARS[source] >>= int(value)
                return VARS[source]

        elif cmd == 'GOTO':
                runScript(int(value))
                
        elif cmd == 'LBL':
                return 0
                # is this needed?
        
        elif cmd == 'IF':
                #parse IF statement
                #cond = 
                #gotoLine =
                

                if cond == '==':
                        comp = cond

                elif cond == '=':
                        comp = cond

                elif cond == '<':
                        comp = cond

                elif cond == '=<':
                        comp = cond

                elif cond == '>':
                        comp = cond

                elif cond == '=>':
                        comp = cond

                elif cond == '!=':
                        comp = cond

                else:
                        comp = 'comparison is not supported'
                        
                if comp == True:
                        return comp
                        # runScript from line below IF statement line 
                        

        elif cmd == 'RUN':
                runScript(int(value))

        elif cmd == 'SCRIPT':
                print 'begin script'
                # shouldn't be sent through

        elif cmd == 'ENDSCRIPT':
                print 'end script'
                # shouldn't be sent through
        elif cmd == '':
                return 1 
                
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

        for i in range(0,len(existingMotors)-1):
                try:
                        motorRead = open(checkMotorPort.format(existingMotors[i])) 
                        mo = motorRead.read()
                        motorRead.close
                        print mo
                        print mo[3]
                        
                        MOTORS[mo[3]] = existingMotors[i]
                except IOError:
                        print "no motor"
                        
                
        if port in range(0,3):
                port = changePort(port)
                motor = open(setMotorSpeed.format(MOTORS[port]),'r+') 
                motor.write(value + '\n')
                motor.close
                motorRun = open(runMotor.format(MOTORS[port]),'r+')
                motorRun.write('1\n')
                motorRun.close

        else:
                print 'no motor attached to port'
        
# ports A,B,C,D
def AO(channel,value):
        return 1024

# ports 1,2,3,4
def AI(channel):

        existingSensors = os.listdir(sensorAttached)

        for i in range(0,len(existingMotors)-1):
                try:
                        sRead = open(checkSensorPort.format(existingSensors[i])) 
                        sen = sRead.read()
                        sRead.close
                        print sen
                        print sen[2]
                        
                        SENSORS[sen[2]] = existingSensors[i]
                except IOError:
                        print "no sensor"
                        
                
        if channel in range(0,3):
                channel = changeInPort(channel)
        
        # ask what sensor is plugged in - theSensor
        sensor = open(drivername.format(channel),'r+')
        theSensor = sensor.read()
        sensor.close 

        # read value from sensor 
        # ultrasonic sensor
        if theSensor == 'ev3-uart-30':
                print 'ultrasonic sensor'
                ultra = open(ultrasonicvalue.format(channel),'r+')
                value = ultra.read()
                ultra.close

        # gyro sensor   
        elif theSensor == 'ev3-uart-32':
                print 'gyro sensor'
                gyro = open(gyrovalue.format(channel),'r+')
                value = gyro.read()
                gyro.close

        # touch sensor 
        elif theSensor == 'ev3-touch':
                print 'touch sensor'
                touch = open(touchvalue.format(channel),'r+')
                value = touch.read()
                touch.close

        # ir sensor 
        elif theSensor == 'ev3-uart-33':
                print 'IR sensor'
                ir = open(irvalue.format(channel),'r+')
                value = ir.read()
                ir.close
                
        # angle sensor
        elif theSensor == 'ev3-analog':
                print 'angle sensor'
                angle = open(analogvalue.format(channel),'r+')
                value = angle.read()
                angle.close

        return value

# DIO write
# value: 0 = Right Green, 1 = Right Red, 2 = Left Green, 3 = Left Red
def DIO(channel,value):
                
        if channel == '0':
                LED = open(ledbright.format('green','right'),'r+')
        elif channel == '1':
                LED = open(ledbright.format('red','right'),'r+')
        elif channel == '2': 
                LED = open(ledbright.format('green','left'),'r+')
        elif channel == '3':
                LED = open(ledbright.format('red','left'),'r+')
        else:
                print 'no LED in this pin, choose from pins 0-3'

        value = value.strip()
        value = int(value)
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
                LED = open(ledbright.format('green','right'),'r+')
        elif chan == '1':
                LED = open(ledbright.format('red','right'),'r+')
        elif chan == '2':
                LED = open(ledbright.format('green','left'),'r+')
        elif chan == '3':
                LED = open(ledbright.format('red','left'),'r+')
       
        theValue = LED.read()
        print theValue
        LED.close

        theValue = theValue.strip()
        theValue = int(theValue)
        if theValue == 255:
                print '1'
        elif theValue == 0:
                print '0'

def TMR(channel,value):
        timer = True
def SERVO(channel,value):
        servo = True
def COM(channel,value):
        com = False

# port A,B,C,D to 0,1,2,3

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


while True:
        time.sleep(0.5)
        

