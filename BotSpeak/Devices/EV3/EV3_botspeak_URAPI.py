#!/usr/bin/python
from BaseHTTPServer import BaseHTTPRequestHandler,HTTPServer
#from os import curdir, sep, listdir
import os,sys
import cgi
import thread
import threading
import time
import datetime

# variable dictionary
VARS = {'VER':'1.0', 'HI':'1', 'LO':0, 'END': 0}
# motor dictionary
MOTORS = {}
# sensor dictionary
SENSORS = {}
TIMER = []
SCRIPT = []
pwms = ["A","B","C","D"]
AIPins = ["1","2","3","4"]

## list of hardware variables
#setVar = ['DIO','PWM','AO','SERVO','TMR','COM']
#getVar = ['DIO','AI']

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

#This class will handle any incoming requests through http
class myHandler(BaseHTTPRequestHandler):
        
        #Handler for the POST requests
        def do_POST(self):
                length = self.headers.getheader('content-length')
                script = self.rfile.read(int(length))  
                runBotSpeak(script.rstrip('/r/n'))
                        
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

def runBotSpeak(command):
    botCode = command.split('&')
    totalSize = len(botCode)
    scripting = -1
    ptr = 0
    reply = ""
    def runScript(debug):
        j = int(botCode[i][botCode[i].index(' '):len(botCode[i])])
        VARS["END"] = len(SCRIPT) - 1
        while (j <= VARS["END"]):
            reply = ExecuteCommand(SCRIPT[j])
            print '{} -> {}'.format(SCRIPT[j],reply)
            goto = str(reply).split(' ')
            j = int(goto[1]) if (goto[0] == "GOTO") else (j + 1)            

    for i in range(0,totalSize):
        com = getCommand(botCode[i])
        if com == "SCRIPT":
            scripting = 0
            ptr = 0
            print "start script"
        elif com == "ENDSCRIPT":
            scripting = -1
            ptr = 0
            print "end script"
        elif com == "RUN":
            runScript(False)
        elif com == "DEBUG":
            runScript(True)
        else:
            if (scripting >= 0):
                SCRIPT.append(botCode[i])
                ptr += 1
            else: reply += ExecuteCommand(botCode[i])

#Execute BotSpeak Command
def ExecuteCommand(code):
        if code == '': return code
        if code.split(" ")[0].strip() == "//": return " "
        command = getCommand(code)
        args = code[code.index(" "):len(code)].split(',')
        dest = args[0].strip()
        value = args[1].strip() if len(args) > 1 else 0
        
        if command == "SET": return Assign(dest,Retrieve(value))
        elif command == "GET": 
            return Retrieve(dest)
        elif command == "WAIT": 
            waitTime = Retrieve(dest)/1000
            time.sleep(waitTime)
            return waitTime                          
        elif command == "ADD": 
            VARS[dest] = (float(VARS[dest]) + Retrieve(value))
            return VARS[dest]
        elif command == "SUB": 
            VARS[dest] = (float(VARS[dest]) - Retrieve(value))
            return VARS[dest]
        elif command == "MUL": 
            VARS[dest] = (float(VARS[dest]) * Retrieve(value))
            return VARS[dest]
        elif command == "DIV": 
            VARS[dest] = (float(VARS[dest]) / Retrieve(value))
            return VARS[dest]
        elif command == "AND": 
            VARS[dest] = (float(VARS[dest]) & Retrieve(value))
            return VARS[dest]
        elif command == "OR": 
            VARS[dest] = (float(VARS[dest]) | Retrieve(value)) 
            return VARS[dest]
        elif command == "NOT": 
            VARS[dest] = (float(VARS[dest]) != Retrieve(value))
            return VARS[dest]
        elif command == "BSL": 
            VARS[dest] = (float(VARS[dest]) << Retrieve(value))
            return VARS[dest]
        elif command == "BSR": 
            VARS[dest] = (float(VARS[dest]) >> Retrieve(value))
            return VARS[dest]
        elif command == "MOD": 
            VARS[dest] = (float(VARS[dest]) % Retrieve(value))
            return VARS[dest]
        elif command == "EQL": 
            VARS[dest] = (float(VARS[dest]) == Retrieve(value))
            return VARS[dest]
        elif command == "GRT": 
            VARS[dest] = (float(VARS[dest]) > Retrieve(value))
            return VARS[dest]
        elif command == "GRE": 
            VARS[dest] = (float(VARS[dest]) >= Retrieve(value))
            return VARS[dest]
        elif command == "LET": 
            VARS[dest] = (float(VARS[dest]) < Retrieve(value))
            return VARS[dest]
        elif command == "LEE": 
            VARS[dest] = (float(VARS[dest]) >= Retrieve(value))
            return VARS[dest]
        elif command == "GOTO": return "{} {}".format(command,dest)
        elif command == "LBL": return 0
        elif command == "IF":
            conditional = code[code.index('(')+1:code.index(')')]
            jump = code[code.index("GOTO"):len(code)]
            params = conditional.split(' ')
            if params[1] == ">": comparison = Retrieve(params[0].strip()) > Retrieve(params[2].strip())
            elif params[1] == "<": comparison = Retrieve(params[0].strip()) < Retrieve(params[2].strip())
            elif params[1] == "=": comparison = Retrieve(params[0].strip()) == Retrieve(params[2].strip())
            elif params[1] == "==": comparison = Retrieve(params[0].strip()) == Retrieve(params[2].strip())
            elif params[1] == "!=": comparison = Retrieve(params[0].strip()) != Retrieve(params[2].strip())
            elif params[1] == "<=": comparison = Retrieve(params[0].strip()) <= Retrieve(params[2].strip())
            elif params[1] == ">=": comparison = Retrieve(params[0].strip()) >= Retrieve(params[2].strip())
            else: return "unsupported conditional"
            if (code.find('~') != -1): comparison = not comparison
            if comparison: return jump
            else: return 1
        elif command == "SYSTEM": return SysmtemCall(args)
        elif command == "end": return "end"
        else: return "{} command not yet supported".format(command)
                
# assign value to certain source
def Assign(dest, value):
    param = dest.split('[')
    param1 = GetArrayIndex(param)
    if param[0] == "DIO": return DIO(param1,value)
    elif param[0] == "AO": return "0"
    elif param[0] == "PWM": return PWM(param1,value)
    elif param[0] == "TMR": return setTMR(param1,value)                                           
    elif param[0] == "VER": return VARS["VER"]
    elif param[0] == "AI": return AI(param1)
    elif param[0] == "SERVO": return PWM(param1,value)
    else:
        if len(param) == 1:
            VARS[dest] = value
            return VARS[dest]
                                           
def Retrieve(source):
    param = source.split('[') if source.find('[') else source
    length = len(param)
    param1 = GetArrayIndex(param)
    param = source.split('[')[0] if source.find('[') else source
    if param == "DIO": return readDIO(param1)
    elif param == "AI": return AI(param1)
    elif param == "TMR": return getTMR(param1)
    else:
        if length == 1:
            if source in VARS: return VARS[source]
            else: return int(float(source))
        else: # arrays not supported yet
            return 0

def GetArrayIndex(param):
    if len(param) <= 1: return -1
    TwoD = param[1].split(':') if param[1].find(":") else param[1]
#    print param[1].split(']')[0]
    if (len(TwoD) <= 1): return Retrieve((param[1].split(']')[0]).strip())
    else: return 0 # doesn't support arrays yet
                                           
        
def getCommand(code):
        return (code[0:code.index(' ')]).strip() if (code.find(' ') != -1) else code.strip()

# DIO write
# value: 0 = Right Red, 1 = Left Red, 2 = Right Green, 3 = Left Green
def DIO(channel,value):
        if channel == 0: LED = open(ledbright.format('right0','red'),"w",0)
        elif channel == 1: LED = open(ledbright.format('left0','red'),"w",0)
        elif channel == 2: LED = open(ledbright.format('right1','green'),"w",0)
        elif channel == 3: LED = open(ledbright.format('left1','green'),"w",0)                
        else: print 'no LED in this pin, choose from pins 0-3'
        if value: LED.write('255\n')
        else: LED.write('0\n')
        LED.close
        return value
                                           
# ports A,B,C,D
def PWM(channel,value):
        port=int(channel)
        speed = int(float(value))
        speed = str(speed) if speed <= 100 else str(100)
        # motor dictionary {'actual Ev3 port':'motor0'}
        existingMotors = os.listdir(motorAttached)
        MOTORS = {} # reset dictionary
        for i in range(0,len(existingMotors)):
            try:
                motorRead = open(checkMotorPort.format(existingMotors[i])) 
                mo = motorRead.read()
                motorRead.close
                MOTORS[mo[3]] = existingMotors[i] # add new motor to dictionary
            except IOError:
                print "no motor"           
        if port in range(0,3):
            port = pwms[port]
            motor = open(setMotorSpeed.format(MOTORS[port]),'w',0) 
            motor.write(speed + '\n')
            motor.close
            motorRun = open(runMotor.format(MOTORS[port]),'w',0)
            if speed == 0: #stop 
                    motorRun.write('stop')
            else:# run motor
                    motorRun.write('run-forever')
            motorRun.close
        else:
                print 'no motor attached to port'
        return value

# DIO read
def readDIO(chan):
        if chan == '0': LED = open(ledbright.format('right0','red'),'r+',0)
        elif chan == '1': LED = open(ledbright.format('left0','red'),'r+',0)
        elif chan == '2': LED = open(ledbright.format('right1','green'),'r+',0)
        elif chan == '3': LED = open(ledbright.format('left1','green'),'r+',0)
        theValue = LED.read()
        LED.close
        theValue = theValue.strip()
        theValue = int(theValue)
        if theValue == 255:
                return '1'
        elif theValue == 0:
                return '0'                                         

# ports 1,2,3,4
def AI(channel):
        # sensor dictionary {'actual Ev3 port':'sensor0'}
        existingSensors = os.listdir(sensorAttached)
        # reset dictionary
        SENSORS = {} 
        channel = AIPins[channel]
        for i in range(0,len(existingSensors)):
            try:
                senRead = open(checkSensorPort.format(existingSensors[i])) 
                mo = senRead.read()
                senRead.close
                SENSORS[mo[2]] = existingSensors[i] # add to dictionary
            except IOError:
                print "no sensor"
        if channel in SENSORS:
            # read value
            chan = str(channel)
            Sens = open(sensorValue.format(SENSORS[chan]))
            value = Sens.read()
            Sens.close
            # ask what sensor is plugged in - theSensor
#            sensor = open(drivername.format(SENSORS[chan]))
#            theSensor = sensor.read()
#            print theSensor # may want to do something with the sensor name later
#            sensor.close
            return value
        else: return 0

                                           
def setTMR(param,value):
    TMR[param] = value + datetime.datetime.now()
    return TMR[param]
                                           
def getTMR(param):
    reply = (datetime.datetime.now() - TMR[param]).total_seconds()
    reply = reply if reply >= 0 else 0
    return reply
    
      
while True:
    time.sleep(0.5)