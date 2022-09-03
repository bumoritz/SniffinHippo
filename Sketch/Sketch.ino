//---------------------------------------------------------
// SNIFFINHIPPO 2.0
//---------------------------------------------------------


//---------------------------------------------------------
// DECLARE AND INITIALISE VARIABLES
//---------------------------------------------------------

// pin numbers
const int pin_led = 13;
const int pin_finalValve = 22;
const int pin_mixingValve = 23;
const int pin_vial1_in = 24;
const int pin_vial1_out = 25;
const int pin_vial2_in = 26;
const int pin_vial2_out = 27;
const int pin_vial3_in = 28;
const int pin_vial3_out = 29;
const int pin_vial4_in = 30;
const int pin_vial4_out = 31;
//const int pin_mfc1_digi = 50;
//const int pin_mfc2_digi = 51;
//const int pin_mfc3_digi = 52;
const int pin_trigger = 53;
//const int pin_mfc1_anal = A0;
//const int pin_mfc2_anal = A1;
//const int pin_mfc3_anal = A2;
//const int pin_flowmeter = A3;
//const int pin_pid = A4;

// serial communication
char incomingByte;
char varBuffer[1000]; // maximum length of serial input objects, i.e. trials
int varIndex = 0;
int varBufferIndex = 0;
char INCOMING_COMMAND = '@';
char ABORT_COMMAND = '&';
char TEST_PIN = '!';
char TEST_READY = '?';
char test_command;
int testChanNum;
int testChanDur;
String ConfigString;

// config parameters
String mode;
String valves = "0000000000";
String source;
String delivery;
int stabilisation;
int pulse;
int tOdour1;
int tGap;
int tOdour2;
String typeConts;
String vialConts;
int numTrials;
String trialOrder;
String trialVariations;

// states
bool configReceived = false;
bool configStringStarted = false;
bool configStringEnded = false;
bool abortReceived = false;
bool triggerReceived = false;
//bool trialCompleted = false;
bool executionCompleted = false;
int currentState = 0;

// timing
unsigned long t_startExecution;
unsigned long t_current;
unsigned long t_thisTrigger;
unsigned long t_currentState;

// other variables
int trigger;
int thisTrial = -1;
String thisType;
String thisVariation;
int thisVial;
int vial;
String odour1;
String odour2;
String vials1;
String vials2;
String vials;
String valvesDefault = "0000000000";
int ledState = LOW;     

//---------------------------------------------------------
// PREPARE ARDUINO
//---------------------------------------------------------

void setup() {
  
  // set up serial communication
  Serial.begin(19200);
  Serial.println("{READY}");
  delay(10);

  // define digital output pins
  for ( int i = 0; i < 40; ++i ) {
    pinMode(i, OUTPUT);
    digitalWrite(i, LOW);
  }

  // define digital input pins
  for ( int i = 40; i < 54; ++i ) {
    pinMode(i, INPUT);
  }
}

//---------------------------------------------------------
// MAIN LOOP
//---------------------------------------------------------

void loop() {

  // receive instructions loop 
  while (!configReceived) {
    //sensors2serial();
    updateValves(valves);    
    rxConfig();
  }

  // execute instructions loop 
  t_startExecution = millis();
  while (configReceived) {
    t_current = millis();
    //sensors2serial();

    getCurrentValvesString();

    updateValves(valves);

    handleAbortSignal();

    // prepare to go back into receive instructions loop
    if (executionCompleted) {
      if (abortReceived) {
        Serial.println("{ABORTED}");
      }
      else {
        Serial.println("{COMPLETED}");
      }
      resetStates();
    }
  }
}

//---------------------------------------------------------
// STATE UPDATE FUNCTIONS / PREPARE VALVES STRING
//---------------------------------------------------------

void getCurrentValvesString() {
  
  if (mode == "Manual_Valves") {
    executionCompleted = true;
  }
  
  else if (mode == "Manual_Vials") {
    if (t_current - t_startExecution < stabilisation) {
      vial = source[source.length()-1]-'0';
      getStabilisationString();
      if (currentState == 0) {
        t_currentState = millis();
        Serial.println("$_ST_"+String(t_currentState));
        currentState += 1;
      } 
    }
    else if (t_current - t_startExecution < stabilisation+pulse) {
      valves.setCharAt(0,'1'); // set pulse string
      if (currentState == 1) {
        t_currentState = millis();
        Serial.println("$_OD_"+String(t_currentState));
        currentState += 1;
      } 
    }   
    else if (t_current - t_startExecution >= stabilisation+pulse) {
      valves = valvesDefault;
      executionCompleted = true;
      if (currentState == 2) {
        t_currentState = millis();
        Serial.println("$_EX_"+String(t_currentState));
        currentState = 0;
      } 
    }   
  }
  
  else if (mode == "PyBehaviour") {

    if (triggerReceived) {
      if (t_current - t_thisTrigger < tOdour1) {
        valves.setCharAt(0,'1'); // set pulse string
        if (currentState == 1) {
          t_currentState = millis();
          Serial.println("$_"+String(thisTrial+1)+"_O1_"+String(t_currentState));
          currentState += 1;
        } 
      }
      else if (t_current - t_thisTrigger < tOdour1+tGap) {     
        getVials(thisTrial);
        vial = vials[1]-'0';
        getStabilisationString();
        if (currentState == 2) {
          t_currentState = millis();
          Serial.println("$_"+String(thisTrial+1)+"_S2_"+String(t_currentState));
          currentState += 1;
        } 
      }
      else if (t_current - t_thisTrigger < tOdour1+tGap+tOdour2) {
        valves.setCharAt(0,'1'); // set pulse string
        if (currentState == 3) {
          t_currentState = millis();
          Serial.println("$_"+String(thisTrial+1)+"_O2_"+String(t_currentState));
          currentState += 1;
        } 
      }
      else if (t_current - t_thisTrigger >= tOdour1+tGap+tOdour2) {
        triggerReceived = false;
        currentState = 0;
      }    
    }
    
    else {   
      if (thisTrial < numTrials-1) {

        // stabilise first odour of next trial
        getVials(thisTrial+1);
        vial = vials[0]-'0';
        getStabilisationString();
        if (currentState == 0) {
          t_currentState = millis();
          Serial.println("$_"+String(thisTrial+2)+"_S1_"+String(t_currentState));
          currentState += 1;
        } 

        // check if trigger arrived
        trigger = digitalRead(pin_trigger);
        if (trigger == HIGH) {
          thisTrial += 1;
          triggerReceived = true;
          t_thisTrigger = millis();
          Serial.println("$_"+String(thisTrial+1)+"_TR_"+String(t_thisTrigger));
        }
      }
      else {
        valves = valvesDefault;
        executionCompleted = true;
        t_currentState = millis();
        Serial.println("$_"+String(thisTrial+1)+"_EX_"+String(t_currentState));
      }
    }
  }
}

void getStabilisationString() {
  if (vial == 1) {
    valves = "0111000000";
  }
  else if (vial == 2) {
    valves = "0100110000";
  }
  else if (vial == 3) {
    valves = "0100001100";
  }
  else if (vial == 4) {
    valves = "0100000011";
  }
  else {
    valves = "0000000000";
  }
}

void getVials(int trialToConsider) {
  thisType = trialOrder[trialToConsider];
  thisVariation = trialVariations[trialToConsider];
  odour1 = typeConts[typeConts.indexOf(thisType+thisVariation)+2];
  odour2 = typeConts[typeConts.indexOf(thisType+thisVariation)+3];
  vials1 = vialConts[vialConts.indexOf(odour1)-1];
  vials2 = vialConts[vialConts.indexOf(odour2)-1];
  vials = vials1+vials2;
}

void handleAbortSignal() {
  incomingByte = Serial.read();
  if (incomingByte == ABORT_COMMAND) {
    abortReceived = true;
    valves = valvesDefault;
    updateValves(valves);
    executionCompleted = true;
  }
}

void resetStates() {
  // change such that it really includes all states
  abortReceived = false;
  configReceived = false;
  configStringStarted = false;
  configStringEnded = false;
  executionCompleted = false;
  triggerReceived = false;
  thisTrial = -1;
  currentState = 0;
}

//---------------------------------------------------------
// EXECUTION FUNCTIONS
//---------------------------------------------------------

void updateValves(String valvesCommandString) {
  digitalWrite(pin_finalValve,valvesCommandString[0] == '1');
  digitalWrite(pin_mixingValve,valvesCommandString[1] == '1');
  digitalWrite(pin_vial1_in,valvesCommandString[2] == '1');
  digitalWrite(pin_vial1_out,valvesCommandString[3] == '1');
  digitalWrite(pin_vial2_in,valvesCommandString[4] == '1');
  digitalWrite(pin_vial2_out,valvesCommandString[5] == '1');
  digitalWrite(pin_vial3_in,valvesCommandString[6] == '1');
  digitalWrite(pin_vial3_out,valvesCommandString[7] == '1');
  digitalWrite(pin_vial4_in,valvesCommandString[8] == '1');
  digitalWrite(pin_vial4_out,valvesCommandString[9] == '1');
}

//---------------------------------------------------------
// SENSOR FUNCTIONS
//---------------------------------------------------------

void sensors2serial() {
  //Serial.println("TEST");
}

//---------------------------------------------------------
// SERIAL COMMUNICATION FUNCTIONS
//---------------------------------------------------------

void rxConfig() {
  while (Serial.available()) {
    incomingByte = Serial.read();

    // TEST PIN
    if (incomingByte == INCOMING_COMMAND) {
      delay(1);
      test_command = Serial.read();
      delay(1);
      if (test_command == TEST_PIN) {
        varBufferIndex = 0;
        varBuffer[varBufferIndex] = '\0';
        varIndex = 0;
        while (Serial.available()) {
          delay(1);
          incomingByte = Serial.read();
          if (incomingByte == ';') {
            // when reach seperator ; save the variable
            varIndex++;
            switch (varIndex) {
              case 1:
              testChanNum = atoi(varBuffer);
              break;
              case 2:
              testChanDur = atoi(varBuffer);
              break;
            }
            varBufferIndex = 0;
            varBuffer[varBufferIndex] = '\0';
          }
          else {
            // store in the buffer
            varBuffer[varBufferIndex] = incomingByte;
            varBufferIndex++;
            varBuffer[varBufferIndex] = '\0';
          }
        }
        testPin(testChanNum, testChanDur);
      }

      else if (test_command == TEST_READY) {
        Serial.println("{!}");
      }
    }
    
    // TRIAL CONFIGURATION
    else if (incomingByte == '<') {
      configStringStarted = true;
      varBufferIndex = 0;
      varBuffer[varBufferIndex] = '\0';
      varIndex = 0;
    }
    else if (incomingByte == '>') {
      // when reach > stop and clear buffer (variables already saved)
      configStringEnded = true;
      varBufferIndex = 0;
      varBuffer[varBufferIndex] = '\0';
      varIndex = 0;
      break;
    }
    else if (incomingByte == ':') {
      // : signals start of variable, the preceding identfier string is discarded
      varBufferIndex = 0;
      varBuffer[varBufferIndex] = '\0';
      
    }
    else if (incomingByte == ';') {
      // when reach seperator ; save the variable
      varIndex++;

      switch (varIndex) {
        
        case 1:
        mode = varBuffer;
        break;
        
        case 2:
        if (mode == "Manual_Valves") {
          valves = varBuffer;
        }
        else if (mode == "Manual_Vials") {
          source = varBuffer;
        }
        else if (mode == "PyBehaviour") {
          tOdour1 = atoi(varBuffer);
        }
        break;
        
        case 3:
        if (mode == "Manual_Vials") {
          delivery = varBuffer;
        }
        else if (mode == "PyBehaviour") {
          tGap = atoi(varBuffer);
        }
        break;

        case 4:
        if (mode == "Manual_Vials") {
          stabilisation = atoi(varBuffer);
        }
        else if (mode == "PyBehaviour") {
          tOdour2 = atoi(varBuffer);    
        }
        break;

        case 5:
        if (mode == "Manual_Vials") {
          pulse = atoi(varBuffer);
        }
        else if (mode == "PyBehaviour") {
          typeConts = varBuffer;
        }
        break;
        
        case 6:
        if (mode == "PyBehaviour") {
          vialConts = varBuffer;
        }
        break;

        case 7:
        if (mode == "PyBehaviour") {
          numTrials = atoi(varBuffer);  
        }
        break;

        case 8:
        if (mode == "PyBehaviour") {
          trialOrder = varBuffer;
          trialOrder = trialOrder.substring(1,trialOrder.length());
        }
        break;

        case 9:
        if (mode == "PyBehaviour") {
          trialVariations = varBuffer;
          trialVariations = trialVariations.substring(1,trialVariations.length());
        }
        break;
      }
      varBufferIndex = 0;
      varBuffer[varBufferIndex] = '\0';
    }
    else {
      // save the read character to the incoming variable buffer
      varBuffer[varBufferIndex] = incomingByte;
      varBufferIndex++;
      varBuffer[varBufferIndex] = '\0';
    }
  }
  if (configStringStarted && configStringEnded) {
    // received a whole < > packet
    configReceived = true;
    Serial.println("{CONFIGURED}");
  }
}

void testPin(int pinNumber, int pinDuration) {
  Serial.print("Pin: ");
  Serial.print(pinNumber);
  Serial.print(", duration: ");
  Serial.println(pinDuration);
  digitalWrite(pinNumber, HIGH);
  delay(pinDuration);
  digitalWrite(pinNumber, LOW);
}

//---------------------------------------------------------
// DEBUGGING HELPERS
//---------------------------------------------------------

void types(String a){Serial.println("it's a String");}
void types(int a)   {Serial.println("it's an int");}
void types(char* a) {Serial.println("it's a char*");}
void types(float a) {Serial.println("it's a float");} 
