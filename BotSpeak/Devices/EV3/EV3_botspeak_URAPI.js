var net = require('net');
var fs = require('fs');

var ledpath = '/sys/class/leds/ev3-';
var motorPath = '/sys/class/tacho-motor/'; 
var sensorPath = '/sys/class/lego-sensor/';
var soundPath = '/sys/devices/platform/snd-legoev3/';

var PWMPins = ["A","B","C","D"]; //PWM capable pins
var DIOPins = ["1","2","3","4"];

var PWM_SIZE = PWMPins.length;

var SCRIPT = []; //initialize script space; javascript autosizes arrays
var TIMER = []; //initialize timer space
var VARS = {VER:'4', HI:'1', LO:'0', END: '0'}; //initialize variable space, first 4 are reserved for system info

var server = net.createServer(socketOpen); //start the server

function socketOpen(socket) {
    socket.on('end', tcpClose);
    function tcpClose() {
    }
    socket.on('data', tcpData);
    var my_input = "";
    function tcpData(data) {
        my_input = my_input + data;
	console.log('input received:\n' + my_input);
	var n = my_input.indexOf("\r\n");        
        if(n != -1) {
            var command = my_input.split("\r\n");
            var reply = RunBotSpeak(command[0],socket); // don't want \r\n and whatever is after it - assume only one \r\n
            if (reply !== '') socket.write(reply + "\r\n");
            if ((reply !== "close") && (command[0] !== '')) console.log("Got: " + command[0].replace(/\n/g,",") + " Replied: " + reply.replace(/\n/g,","));
            my_input = "";
        }
    }
}

console.log("starting");
server.listen(2012);

function RunBotSpeak (command,socket) {
    var BotCode = command.split('\n');
       //    console.log(BotCode);
    var TotalSize = BotCode.length;
    var reply = "";
    var scripting = -1, ptr = 0,i,j;
    
    function RunScript (debug){
	j = Number(Retrieve(BotCode[i].slice(BotCode[i].indexOf(' '))));
	VARS["END"] = SCRIPT.length - 1;
    	if(j <= VARS["END"]) setTimeout(runExecuteCommand, 0);
		function runExecuteCommand() {
			var reply1 = ExecuteCommand(SCRIPT[j]);
//			if (debug && (command !== 'RUN')) {
//			    socket.emit('message',(SCRIPT[j] + ' -> '+ reply1 + '\n'));
			    console.log(SCRIPT[j] + ' -> '+ reply1 + '\n');
//			}
			var goto = String(reply1).split(' ');
            var timeDelay = (goto[0] == "WAIT") ? Number(goto[1]): 0;
			j = (goto[0] == "GOTO") ? Number(goto[1]): j + 1;
			
    			if(j <= VARS["END"]) {
    				setTimeout(runExecuteCommand, timeDelay);
    			} else {
        			if (debug) reply += "ran " + (Number(VARS["END"]) + 1) + " lines of script\nDone";
        			if (debug) { if (command == 'RUN') reply = '';}
        	    		socket.emit('message',reply);
    			}
		}
	}

    for (i = 0;i < TotalSize; i++) {
        //        console.log(GetCommand(BotCode[i]));
        switch (GetCommand(BotCode[i])) {
            case "":console.log("blank"); break;
                
            case "SCRIPT":		//start recording the script to memory
                scripting = 0;
                ptr = 0;
                reply += "start script\n";
                break;
                
            case "ENDSCRIPT":		//finish recording the script to memory
                scripting = -1;
                ptr = 0;
                reply += "end script\n";
                // console.log(SCRIPT);
                break;
                
            case "RUN": // run the script without debugging
//                socket.write('\r\n');
                RunScript(false);
				break;

            case "RUN&WAIT":
            case "DEBUG":		//Run script in debug mode: echo each command as it executes and also print the value returned by the command
                RunScript(true);
                break;
                
            case "Done": break;
            default: {
                if (scripting >= 0) {
                    SCRIPT[ptr] = BotCode[i];
                    reply += SCRIPT[ptr] + '\n';
                    ptr ++;
                }
                else reply += ExecuteCommand(BotCode[i]) + '\n';
			}
        }
    }
    return reply;
}

function ExecuteCommand(Code) {
    if (trim(Code.slice(0,2)) == '//') return " ";  // "//" means it's just a comment
    if (trim(Code) =='') return '';   // a space is a blank line
    var command = GetCommand(Code);   // everything before the space
    var args = trim(Code.slice(Code.indexOf(' '))).split(',');  // everything after the space, split by ','
    var dest = trim(args[0]); //trim the space off first operand, which is the destination
    var value = (args.length > 1) ? trim(args[1]):0; //if there is more than one operand, set the second one as the value; otherwise value = 0 because we only have one operand
    var waittime = 0;
    
    switch (command) {
        case "SET": return Assign(dest,Retrieve(value));		//set value
        case "GET": return Retrieve(dest);		//get value
        case "WAIT": waittime = Retrieve(dest); return "WAIT " + waittime;		//wait in milliseconds; BotSpeak sends wait in seconds
        case "WAITµs": waittime = Retrieve(dest)/1000; return "WAIT " + waittime;		//wait in microseconds
        case "ADD": return VARS[dest] += Retrieve(value); 
        case "SUB": return VARS[dest] -= Retrieve(value);
        case "MUL": return VARS[dest] *= Retrieve(value);
        case "DIV": return VARS[dest] /= Retrieve(value);
        case "AND": return VARS[dest] &= Retrieve(value);
        case "OR":  return VARS[dest] |= Retrieve(value);
        case "NOT": return VARS[dest] = (VARS[dest] != Retrieve(value));
        case "BSL": return VARS[dest] <<= Retrieve(value);
        case "BSR": return VARS[dest] >>= Retrieve(value);
        case "MOD": return VARS[dest] %= Retrieve(value);
        case "EQL": return VARS[dest] = (VARS[dest] == Retrieve(value));
        case "GRT": return VARS[dest] = (VARS[dest] > Retrieve(value));
        case "GRE": return VARS[dest] = (VARS[dest] >= Retrieve(value));
        case "LET": return VARS[dest] = (VARS[dest] < Retrieve(value));
        case "LEE": return VARS[dest] = (VARS[dest] >= Retrieve(value));
        case "GOTO":return Jump = command + ' ' + dest;		//used in loops for the most part
        case "LBL": return 0;		//not sure what this is supposed to do; website says it "Stores the current script line into the variable Jump (so you can use IF 1 GOTO Jump)"
        case "IF": {
        	var comparison;
            var conditional = trim(Code.slice(Code.indexOf('(')+1,Code.indexOf(')'))); // get conditional
            var Jump = trim(Code.slice(Code.indexOf('GOTO'))); // get 'GOTO #'
            var params = conditional.split(' ');
            switch (trim(params[1])) {
                case '>':   comparison = (Retrieve(trim(params[0])) > Retrieve(trim(params[2]))); break;
                case '<':   comparison = (Retrieve(trim(params[0])) < Retrieve(trim(params[2])));  break;
                case '=':  comparison = (Retrieve(trim(params[0])) == Retrieve(trim(params[2]))); break;
                case '==':  comparison = (Retrieve(trim(params[0])) == Retrieve(trim(params[2]))); break;
                case '!=':  comparison = (Retrieve(trim(params[0])) != Retrieve(trim(params[2]))); break;
                case '<=':  comparison = (Retrieve(trim(params[0])) <= Retrieve(trim(params[2]))); break;
                case '>=':  comparison = (Retrieve(trim(params[0])) >= Retrieve(trim(params[2]))); break;
                default: return "unsupported conditional";
            }
            if (Code.match('~') != null) comparison = !comparison;
            if (comparison) return Jump; else return 1;
        }    
        case "SYSTEM": return SystemCall(args); //used to enable  user-programmed commands
        case "": return 1; //blank line
        case "end": return "end";
        default: return (command + " not yet supported");
    }
}

function Assign(dest,value)  {		//function that writes values to the various registers - DIO, AO, PWM, etc
    var i;
    var param = dest.split('[');
    var param1 = GetArrayIndex(param);
    switch (param[0]) {
        case "DIO":			//first set pin as output, then write the value
            param1 = (param1 < 3)?param1:0;
            DIO(param1, value);
            return value;
        case "AO":	return 0;	//BB has no analog out
        case "PWM":		//first set up PWM pin, then write value
            param1 = (param1 < 3)?param1:0;
            PWM(PWMPins[param1], value);
            return value;
        case "TMR":		
            TIMER[param1] = value + new Date().getTime();
            return value;
            // Read Only Variables
        case "VER": return VARS["VER"];
        case "AI":		//read analog pin
            param1 = (param1 < 3)?param1:0;
            return AI(param1);
        case "SERVO":
            param1 = (param1 < 3)?param1:0;
            PWM(PWMPins[param1], value);
            return value;
        default:
            if (param.length == 1) {
                var arrayName=dest.split('_SIZE');  // see if they are defining an array
                if (arrayName.length > 1) {
                    VARS[arrayName[0]] =[];
                    for (i=0;i<value;i++) VARS[arrayName[0]][i]=0;
                    VARS[arrayName[0]+'_COLS']=1;  // assume a 1D array initially
                }
                return VARS[dest] = value;
            }
            //            console.log("Assigning "+param[0]+"__"+param1+" of "+VARS[param[0]+'_SIZE']);
            param1 = (param1 < VARS[param[0]+'_SIZE'])?param1:VARS[param[0]+'_SIZE'] - 1;
            
            return VARS[param[0]][param1] = value;
    }
}

function Retrieve(source)  {
    var param = source.split('[');
    var param1 = GetArrayIndex(param);
    var reply = '';
    
    switch (param[0]) {
        case "DIO":
            reply = readDIO(); break;
        case "AI":  reply = AI(param1); break;
        case "TMR": reply = new Date().getTime() - TIMER[param1]; break;
        default: {
            switch(param.length) {
                case 1: {
                    if (VARS[source] === undefined) reply = Number(source);
                    else reply = VARS[source];  // if not declared then probably a number
                    break;
                }
                default:  {
                    //                    console.log("Retrieving "+param[0]+"__"+param1+" of "+VARS[param[0]+'_SIZE']);
                    var ArrayPtr = (param1 < VARS[param[0]+'_SIZE'])? param1 : VARS[param[0]+'_SIZE']-1;
                    reply = VARS[param[0]][ArrayPtr];
                    break;
                }    
            }
        }
    }
    return reply;
}

function GetArrayIndex(param)  {
    if (param.length <= 1) return -1;
    var TwoD=param[1].split(':');
    //    console.log(param[1]+' : '+TwoD);  //2D does not work because the comma is used elsewhere
    if (TwoD.length <= 1) return Retrieve(trim(param[1].split(']')[0]));  // recursive to allow variables in the brackets]
    console.log(Retrieve(TwoD[0]*VARS[param[0]+'_COLS'])+Retrieve(trim(TwoD[1].split(']')[0])));
    return Retrieve(TwoD[0]*VARS[param[0]+'_COLS'])+Retrieve(trim(TwoD[1].split(']')[0]));
}

function trim(AnyString) { // get rid of spaces before and after
    return AnyString.replace(/^\s+|\s+$/g,"");
}

function delay (msec) {
    var start = new Date().getTime();
    for (var i = 0; i < 1e7; i++) {
        if ((new Date().getTime() - start) > msec) break;
    }
    return msec;
}
function microdelay (msec) {
    var start = new Date().getTime();
    for (var i = 0; i < 1e7; i++) {
        if ((new Date().getTime() - start) > msec/1000) break;
    }
}

function GetCommand(Code) {
    return (Code.indexOf(' ') >= 0) ? trim(Code.slice(0,Code.indexOf(' '))) : Code;
}

function SystemCall(args) { //this is just an example of something a user might program
    
}

function DIO(port, value){
    value = (Number(value) == 1) ? 255:0;
    switch(Number(port)){
        case 0: writeLED('right0','red',value); break;
        case 1: writeLED('left0','red',value); break;
        case 2: writeLED('right1','green',value); break;
        case 3: writeLED('left1','green',value); break;
        default:
             console.log('no LED in this pin, choose from pins 0-3'); break;
    }
    return;
}

// changes on board LEDs ex. writeLED('right1','green',20)
function writeLED(location,color,rgb){
    rgb = rgb.toString();
    var path = ledpath + location + ':' + color + ':ev3dev/brightness';
    fs.writeFileSync(path, rgb);
    return;
}

// writes to motor ex. runMotor('A',100)
function PWM(port,speed){
    port = port.toUpperCase();
    var num = port;
    speed = (speed > 100) ? 100: speed;
    if (num === "") return;
    if ((typeof speed) != 'string') speed = Math.round(speed).toString();
    var MOTORS = getMotors();
    if (port in MOTORS){
        if (Number(speed) <= 0) {stopMotor(port);}
        else {
            motorSpeedPath = motorPath + MOTORS[port] + '/duty_cycle_sp';
            motorRunPath = motorPath + MOTORS[port] + '/command';
            fs.writeFileSync(motorSpeedPath, speed + '\n');
            fs.writeFileSync(motorRunPath, 'run-forever');
        }
    }
    else{
        console.log("Run Motor -> no motor connected to port " + port)   
    }
    return;
}

// stops motor ex. stopMotor('A')
function stopMotor(port){
    port = port.toUpperCase();
    var num = port;
        if (num === "") return;
    var MOTORS = getMotors();
    if (port in MOTORS){
        motorRunPath = motorPath + MOTORS[port] + '/command';
        fs.writeFileSync(motorRunPath, 'stop');
    }
    else {
        console.log("Stop Motor -> No motor connected to port " + port);   
    }
    return;
}

// get sensor values ex. getSensor(1)
// returns array of [value, sensor type, units]
function AI(port){
    SENSORS = getAllSensors();
    port = DIOPins[port];
    if (port in SENSORS){
        var sensorValuePath = sensorPath + SENSORS[port] + '/value0';
        try{
            value = Number(fs.readFileSync(sensorValuePath,'utf8').trim());
            return value;
           }
        catch(e){console.log('failed to read sensor');}
    }
    else {
        console.log("No sensor in port" + port); 
        return 0;
    }
    return 0;
}

// creates motor object
function getMotors(){
    var existingMotors = fs.readdirSync(motorPath);
    var MOTORS = new Object();
    for (var i = 0; i < existingMotors.length; i++){
        var motorPort = motorPath + existingMotors[i] + "/port_name";
        try{
            var motorRead = fs.readFileSync(motorPort, "utf8");
            MOTORS[motorRead[3]] = existingMotors[i];
        }
        catch(e){}
    }
    return MOTORS;
}

// creates sensor object
function getAllSensors(){
    var SENSORS = new Object();
    // need an error check here if dir doesnt exist! ***********************************
    try {
        var existingSensors = fs.readdirSync(sensorPath);
        for (var i = 0; i < existingSensors.length; i++){
            var sensorPort = sensorPath + existingSensors[i] + '/port_name';
            try{
                var sensorRead = fs.readFileSync(sensorPort,'utf8')
                SENSORS[sensorRead[2]] = existingSensors[i];
            }
            catch(e){console.log("found no sensors")}
        }
    }
    catch(e){
    }
    return SENSORS;
}


process.on('uncaughtException', function(err) {
	console.log('Exception: ' + err);

	// Trigger autorun to restart us
	var stat = fs.statSync(__filename);
	fs.utimesSync(__filename, stat.atime, new Date());
	process.exit(1);
});
