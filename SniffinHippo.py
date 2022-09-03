# -*- coding: utf-8 -*-
"""

Application for automated mouse behavioural training on olfactory tasks

@author: Moritz Buchholz
"""

import time

import sys
import os
import ctypes
import serial
import logging
from datetime import datetime
import numpy as np
import colorama
from termcolor import colored
colorama.init()

from PyQt5 import QtGui
from PyQt5.QtCore import QCoreApplication, QTimer, QObject, QThread, pyqtSignal
from PyQt5.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QComboBox, QDateTimeEdit,
        QDial, QDialog, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
        QProgressBar, QPushButton, QRadioButton, QScrollArea, QSizePolicy,
        QSlider, QSpinBox, QDoubleSpinBox, QStyleFactory, QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
        QVBoxLayout, QWidget, QStyleFactory)

from Functions import serial_ports

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler('C:\\Setup\\SniffinHippo\\errors.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.info('Started application')

class Sensor(QObject):

    def __init__(self):
        super(Sensor, self).__init__()
        self.saveData = False
        
    def startSensing(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.readSerial)
        self.timer.start(600) # TIMEOUT BETWEEN ITERATIONS (500 works definitely, 200 does not work)
        
    def readSerial(self):
        
        if self.saveData == True:
            GUI.executer.saveInfo()
            self.saveData = False
        
        else:            
            temp_cont_read = arduino['device'].readline().strip().decode('utf-8')
       
            if temp_cont_read == "{COMPLETED}":
                GUI.executer.comm_feed_signal.emit(temp_cont_read, 'arduino')
                if (p['mode'] == "PyBehaviour") or (p['mode'] == "Manual_Vials"):
                    self.saveData = True
                arduino['executing'] = False
                GUI.notExecuting()
                
            elif len(temp_cont_read) > 0:
                if temp_cont_read[0] == "$":
                    thisTimestamp = temp_cont_read[1:len(temp_cont_read)-1]
                    GUI.executer.comm_feed_signal.emit(thisTimestamp, 'arduino')
        

class Executer(QObject):

    # --- SETTING UP EXECUTION ---
    def __init__(self):
        super(Executer, self).__init__()
        self._session_running = False
        self._exiting = False
        self.trial_num = 0
    response_signal = pyqtSignal(int, float, int, str, bool, name='responseSignal')
    state_signal = pyqtSignal(str, name='stateSignal')
    results_signal = pyqtSignal(int, name='resultsSignal')
    trial_start_signal = pyqtSignal(int, name='trialStartSignal')
    trial_end_signal = pyqtSignal(int, name='trialEndSignal')
    session_end_signal = pyqtSignal(name='sessionEndGUISignal')
    arduino_connected_signal = pyqtSignal(name='arduinoConnectedSignal')
    arduino_disconnected_signal = pyqtSignal(name='arduinoDisconnectedSignal')
    comm_feed_signal = pyqtSignal(str, str, name='commFeedSignal')
    def collectSettings(self):
        if GUI.tabs.tabText(GUI.tabs.currentIndex()) == "Manual mode":
            if ((GUI.manual.valvesBox.isChecked() == True) & (GUI.manual.vialsBox.isChecked() == False)):
                p['mode'] = "Manual_Valves" 
                p['valves'] =   str(int(GUI.manual.valves_finalValve_on.isChecked())) + \
                                str(int(GUI.manual.valves_mixingValve_on.isChecked())) + \
                                str(int(GUI.manual.valves_vial1_in_on.isChecked())) + \
                                str(int(GUI.manual.valves_vial1_out_on.isChecked())) + \
                                str(int(GUI.manual.valves_vial2_in_on.isChecked())) + \
                                str(int(GUI.manual.valves_vial2_out_on.isChecked())) + \
                                str(int(GUI.manual.valves_vial3_in_on.isChecked())) + \
                                str(int(GUI.manual.valves_vial3_out_on.isChecked())) + \
                                str(int(GUI.manual.valves_vial4_in_on.isChecked())) + \
                                str(int(GUI.manual.valves_vial4_out_on.isChecked()))
            elif ((GUI.manual.valvesBox.isChecked() == False) & (GUI.manual.vialsBox.isChecked() == True)):
                p['mode'] = "Manual_Vials" 
                p['source'] = GUI.manual.vials_source.currentText()
                p['delivery'] = GUI.manual.vials_delivery.currentText()
                p['stabilisation'] = str(int(GUI.manual.vials_stabilisation.value()*1000))
                p['pulse'] = str(int(GUI.manual.vials_pulse.value()*1000))
                p['date'] = time.strftime('%Y%m%d')
                p['datetime'] = time.strftime('%Y%m%d_%H%M%S')
                p['sessionID'] = "Manual" + '_' + p['datetime'] + '_' + 'SNH'
            else:
                self.comm_feed_signal.emit('Something went wrong in the selection of mode', '')
        elif GUI.tabs.tabText(GUI.tabs.currentIndex()) == "PyBehaviour mode":
            # already collected: trialOrder, trialVariations, numTrials
            p['mode'] = "PyBehaviour" 
            p['animal'] = GUI.pyBehaviour.general_name.text()
            p['date'] = time.strftime('%Y%m%d')
            p['datetime'] = time.strftime('%Y%m%d_%H%M%S')
            p['sessionID'] = p['animal'] + '_' + p['datetime'] + '_' + 'SNH'
            p['tOdour1'] = str(int(GUI.pyBehaviour.struct_odour1.value()*1000))
            p['tGap'] = str(int(GUI.pyBehaviour.struct_gap.value()*1000))
            p['tOdour2'] = str(int(GUI.pyBehaviour.struct_odour2.value()*1000))
            tmp = ""
            for r in range(GUI.pyBehaviour.conts_types.rowCount()):
                for c in range(GUI.pyBehaviour.conts_types.columnCount()):
                    tmp = tmp+GUI.pyBehaviour.conts_types.item(r,c).text()
                tmp = tmp+","
            p['typeConts'] = tmp[0:len(tmp)-1]
            tmp = ""
            for r in range(GUI.pyBehaviour.conts_vials.rowCount()):
                for c in range(GUI.pyBehaviour.conts_vials.columnCount()):
                    tmp = tmp+GUI.pyBehaviour.conts_vials.item(r,c).text()
                tmp = tmp+","
            p['vialConts'] = tmp[0:len(tmp)-1]
        # self.comm_feed_signal.emit('Collected settings for ' + p['mode'] + ' mode', '')

    # --- ARDUINO COMMUNICATION ---
    def connectArduino(self):
        self.comm_feed_signal.emit('Connecting Arduino on port ' + GUI.device_port.currentText(), '')
        try:
            arduino['device'] = serial.Serial(GUI.device_port.currentText(), 19200)
            arduino['device'].timeout = 1
            connect_attempts = 1
            current_attempt = 1
            while arduino['connected'] is False and current_attempt <= connect_attempts:
                temp_read = arduino['device'].readline().strip().decode('utf-8')
                self.comm_feed_signal.emit(temp_read, 'arduino')
                if temp_read == '{READY}':
                    arduino['connected'] = True
                    self.arduino_connected_signal.emit()
                    arduino['device'].timeout = 0.05
                else:
                    current_attempt += 1
                if current_attempt > connect_attempts:
                    self.comm_feed_signal.emit('Failed to connect', 'pc')
                    arduino['device'].close()
        except serial.SerialException as e:
            logger.exception(e)
            self.comm_feed_signal.emit('Serial error', 'pc')       
    def disconnectArduino(self):
        if arduino['connected']:
            arduino['connected'] = False
            self.comm_feed_signal.emit('Disconnecting Arduino...', '')
            arduino['device'].close()
            self.arduino_disconnected_signal.emit()
    def createConfig(self):       # AND DISPLAY DEFAULTS IN MANUAL VALVES MODE BOX. I know does not really belong here
        if p['mode'] == "Manual_Valves":
            self.config_string = '<' + \
                'MODE:' + \
                p['mode'] + ';' \
                'VALVES:' + \
                p['valves'] + ';' \
                '>'
        elif p['mode'] == "Manual_Vials":
            GUI.manual.setValvesBoxDefaults()
            self.config_string = '<' + \
                'MODE:' + \
                p['mode'] + ';' \
                'SOURCE:' + \
                p['source'] + ';' \
                'DELIVERY:' + \
                p['delivery'] + ';' \
                'STABILISATION:' + \
                p['stabilisation'] + ';' \
                'PULSE:' + \
                p['pulse'] + ';' \
                '>'
        elif p['mode'] == "PyBehaviour":
            GUI.manual.setValvesBoxDefaults()
            self.config_string = '<' + \
                'MODE:' + \
                p['mode'] + ';' \
                'T_ODOUR1:' + \
                p['tOdour1'] + ';' \
                'T_GAP:' + \
                p['tGap'] + ';' \
                'T_ODOUR2:' + \
                p['tOdour2'] + ';' \
                'TYPE_CONTS:' + \
                p['typeConts'] + ';' \
                'VIAL_CONTS:' + \
                p['vialConts'] + ';' \
                'NUM_TRIALS:' + \
                p['numTrials'] + ';' \
                'TRIAL_ORDER:' + \
                p['trialOrder'] + ';' \
                'TRIAL_VARIATIONS:' + \
                p['trialVariations'] + ';' \
                '>'
    def transmitConfig(self):
        GUI.trial_log = []
        self.collectSettings()
        self.createConfig()
        arduino_ready = 0
        while not arduino_ready:
            try:
                write_string = '@?'
                self.comm_feed_signal.emit(write_string, 'pc')
                arduino['device'].write(write_string.encode('utf-8'))
                temp_read = arduino['device'].readline().strip().decode('utf-8')
                self.comm_feed_signal.emit(temp_read, 'arduino')                
                if temp_read == '{!}':
                    arduino_ready = 1
                    write_string = self.config_string
                    self.comm_feed_signal.emit(write_string, 'pc')
                    arduino['device'].write(write_string.encode('utf-8'))
                    temp_read = arduino['device'].readline().strip().decode('utf-8')
                    self.comm_feed_signal.emit(temp_read, 'arduino')
            except Exception as e:
                logger.exception(e)
                self.comm_feed_signal.emit('Something went wrong', 'pc')
                self.comm_feed_signal.emit(str(e), 'pc')
                self.disconnectArduino()
                self.connectArduino()
    def transmitAbort(self):
        arduino_aborted = 0
        while not arduino_aborted:
            try:
                write_string = '&'
                self.comm_feed_signal.emit(write_string, 'pc')
                arduino['device'].write(write_string.encode('utf-8'))
                temp_read = arduino['device'].readline().strip().decode('utf-8')
                self.comm_feed_signal.emit(temp_read, 'arduino')                
                if temp_read == '{ABORTED}':
                    arduino_aborted = 1
                    if (p['mode'] == "PyBehaviour") or (p['mode'] == "Manual_Vials"):
                        GUI.executer.saveInfo()
            except Exception as e:
                logger.exception(e)
                self.comm_feed_signal.emit('Something went wrong', 'pc')
                self.comm_feed_signal.emit(str(e), 'pc')
                self.disconnectArduino()
                self.connectArduino()

    def saveInfo(self):

        # get directory
        tempdate = p['date']
        tempsavedir = os.path.join(dir_exp, tempdate[0:4])
        tempsavedir2 = os.path.join(tempsavedir, tempdate[0:4]+'-'+tempdate[4:6])
        tempsavedir3 = os.path.join(tempsavedir2, tempdate[0:4]+'-'+tempdate[4:6]+'-'+tempdate[6:8])        
        if p['mode'] == "PyBehaviour":
            save_directory = os.path.join(tempsavedir3, p['animal'])
        elif p['mode'] == "Manual_Vials":
            save_directory = os.path.join(tempsavedir3, "Manual")
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        save_name = os.path.join(save_directory, p['sessionID'])
        
        log = open(save_name + '.txt', 'w')
        log.write(p['sessionID'])
        log.write('\n')
        if p['mode'] == "PyBehaviour":
            p['notes'] = GUI.pyBehaviour.general_notes.toPlainText()
            log.write(p['notes'])
            log.write('\n')
        log.write('\n')
        log.write('---')
        log.write('\n')
        log.write('\n')
        log.write('\n'.join(GUI.trial_log))
        log.close()

class Manual(QWidget):
    
    def __init__(self):
        super().__init__()
        
        self.createValvesBox()
        self.createVialsBox()
        self.setValvesBoxDefaults()
        self.setVialsBoxDefaults()
        self.setConnects()

        manualLayout = QVBoxLayout()
        manualLayout.addWidget(self.valvesBox)
        manualLayout.addWidget(self.vialsBox)
        self.setLayout(manualLayout)
        
    def setValvesBoxDefaults(self):
        self.valves_finalValve_off.setChecked(True)
        self.valves_mixingValve_off.setChecked(True)
        self.valves_vial1_in_off.setChecked(True)
        self.valves_vial1_out_off.setChecked(True)
        self.valves_vial2_in_off.setChecked(True)
        self.valves_vial2_out_off.setChecked(True)
        self.valves_vial3_in_off.setChecked(True)
        self.valves_vial3_out_off.setChecked(True)
        self.valves_vial4_in_off.setChecked(True)
        self.valves_vial4_out_off.setChecked(True)     
        
    def setVialsBoxDefaults(self):
        self.vials_source.setCurrentIndex(0)
        self.vials_delivery.setCurrentIndex(0)
        self.vials_stabilisation.setValue(5)
        self.vials_pulse.setValue(1)

    def setConnects(self):
        self.valvesBox.toggled.connect(self.valvesBoxChanged)
        self.vialsBox.toggled.connect(self.vialsBoxChanged)
    
    def valvesBoxChanged(self):
        if self.valvesBox.isChecked() == False:
            self.vialsBox.setChecked(True)
        elif self.valvesBox.isChecked() == True:
            self.vialsBox.setChecked(False)
    def vialsBoxChanged(self):
        if self.vialsBox.isChecked() == False:
            self.valvesBox.setChecked(True)
        elif self.vialsBox.isChecked() == True:
            self.valvesBox.setChecked(False)
        
        
    def createValvesBox(self):
        self.valvesBox = QGroupBox("Valves")
        self.valvesBox.setCheckable(True)
        self.valvesBox.setChecked(False)
        
        self.valves_finalValve_label = QLabel("Final valve")
        self.valves_finalValve_off = QRadioButton("Off (odour to exhaust)")
        self.valves_finalValve_on = QRadioButton("On (odour to animal)")
        self.valves_mixingValve_label = QLabel("Mixing valve")
        self.valves_mixingValve_off = QRadioButton("Off (open)")
        self.valves_mixingValve_on = QRadioButton("On (closed)")  
        self.valves_vial1_in_label = QLabel("Vial 1 - inlet")
        self.valves_vial1_in_off = QRadioButton("Off (closed)")
        self.valves_vial1_in_on = QRadioButton("On (opened)")
        self.valves_vial1_out_label = QLabel("Vial 1 - outlet")
        self.valves_vial1_out_off = QRadioButton("Off (closed)")
        self.valves_vial1_out_on = QRadioButton("On (opened)")
        self.valves_vial2_in_label = QLabel("Vial 2 - inlet")
        self.valves_vial2_in_off = QRadioButton("Off (closed)")
        self.valves_vial2_in_on = QRadioButton("On (opened)")
        self.valves_vial2_out_label = QLabel("Vial 2 - outlet")
        self.valves_vial2_out_off = QRadioButton("Off (closed)")
        self.valves_vial2_out_on = QRadioButton("On (opened)")
        self.valves_vial3_in_label = QLabel("Vial 3 - inlet")
        self.valves_vial3_in_off = QRadioButton("Off (closed)")
        self.valves_vial3_in_on = QRadioButton("On (opened)")
        self.valves_vial3_out_label = QLabel("Vial 3 - outlet")
        self.valves_vial3_out_off = QRadioButton("Off (closed)")
        self.valves_vial3_out_on = QRadioButton("On (opened)")
        self.valves_vial4_in_label = QLabel("Vial 4 - inlet")
        self.valves_vial4_in_off = QRadioButton("Off (closed)")
        self.valves_vial4_in_on = QRadioButton("On (opened)")
        self.valves_vial4_out_label = QLabel("Vial 4 - outlet")
        self.valves_vial4_out_off = QRadioButton("Off (closed)")
        self.valves_vial4_out_on = QRadioButton("On (opened)")

        self.valves_finalValve_group = QButtonGroup()
        self.valves_finalValve_group.addButton(self.valves_finalValve_off)
        self.valves_finalValve_group.addButton(self.valves_finalValve_on)        
        self.valves_mixingValve_group = QButtonGroup()
        self.valves_mixingValve_group.addButton(self.valves_mixingValve_off)
        self.valves_mixingValve_group.addButton(self.valves_mixingValve_on)
        self.valves_vial1_in_group = QButtonGroup()
        self.valves_vial1_in_group.addButton(self.valves_vial1_in_off)
        self.valves_vial1_in_group.addButton(self.valves_vial1_in_on)
        self.valves_vial1_out_group = QButtonGroup()
        self.valves_vial1_out_group.addButton(self.valves_vial1_out_off)
        self.valves_vial1_out_group.addButton(self.valves_vial1_out_on)
        self.valves_vial2_in_group = QButtonGroup()
        self.valves_vial2_in_group.addButton(self.valves_vial2_in_off)
        self.valves_vial2_in_group.addButton(self.valves_vial2_in_on)
        self.valves_vial2_out_group = QButtonGroup()
        self.valves_vial2_out_group.addButton(self.valves_vial2_out_off)
        self.valves_vial2_out_group.addButton(self.valves_vial2_out_on)
        self.valves_vial3_in_group = QButtonGroup()
        self.valves_vial3_in_group.addButton(self.valves_vial3_in_off)
        self.valves_vial3_in_group.addButton(self.valves_vial3_in_on)
        self.valves_vial3_out_group = QButtonGroup()
        self.valves_vial3_out_group.addButton(self.valves_vial3_out_off)
        self.valves_vial3_out_group.addButton(self.valves_vial3_out_on)
        self.valves_vial4_in_group = QButtonGroup()
        self.valves_vial4_in_group.addButton(self.valves_vial4_in_off)
        self.valves_vial4_in_group.addButton(self.valves_vial4_in_on)
        self.valves_vial4_out_group = QButtonGroup()
        self.valves_vial4_out_group.addButton(self.valves_vial4_out_off)
        self.valves_vial4_out_group.addButton(self.valves_vial4_out_on)
        
        layout = QGridLayout()
        layout.addWidget(self.valves_finalValve_label, 0, 0)
        layout.addWidget(self.valves_mixingValve_label, 1, 0)
        layout.addWidget(self.valves_vial1_in_label, 2, 0)
        layout.addWidget(self.valves_vial1_out_label, 3, 0)
        layout.addWidget(self.valves_vial2_in_label, 4, 0)
        layout.addWidget(self.valves_vial2_out_label, 5, 0)
        layout.addWidget(self.valves_vial3_in_label, 6, 0)
        layout.addWidget(self.valves_vial3_out_label, 7, 0)
        layout.addWidget(self.valves_vial4_in_label, 8, 0)
        layout.addWidget(self.valves_vial4_out_label, 9, 0)
        layout.addWidget(self.valves_finalValve_off, 0, 1)
        layout.addWidget(self.valves_mixingValve_off, 1, 1)
        layout.addWidget(self.valves_vial1_in_off, 2, 1)
        layout.addWidget(self.valves_vial1_out_off, 3, 1)
        layout.addWidget(self.valves_vial2_in_off, 4, 1)
        layout.addWidget(self.valves_vial2_out_off, 5, 1)
        layout.addWidget(self.valves_vial3_in_off, 6, 1)
        layout.addWidget(self.valves_vial3_out_off, 7, 1)
        layout.addWidget(self.valves_vial4_in_off, 8, 1)
        layout.addWidget(self.valves_vial4_out_off, 9, 1)
        layout.addWidget(self.valves_finalValve_on, 0, 2)
        layout.addWidget(self.valves_mixingValve_on, 1, 2)
        layout.addWidget(self.valves_vial1_in_on, 2, 2)
        layout.addWidget(self.valves_vial1_out_on, 3, 2)
        layout.addWidget(self.valves_vial2_in_on, 4, 2)
        layout.addWidget(self.valves_vial2_out_on, 5, 2)
        layout.addWidget(self.valves_vial3_in_on, 6, 2)
        layout.addWidget(self.valves_vial3_out_on, 7, 2)
        layout.addWidget(self.valves_vial4_in_on, 8, 2)
        layout.addWidget(self.valves_vial4_out_on, 9, 2)
        self.valvesBox.setLayout(layout)     
        
        
    def createVialsBox(self):
        self.vialsBox = QGroupBox("Vials")
        self.vialsBox.setCheckable(True)
        self.vialsBox.setChecked(True)
        
        self.vials_source = QComboBox()
        self.vials_source.addItem("Clean air")
        self.vials_source.addItem("Vial 1")
        self.vials_source.addItem("Vial 2")
        self.vials_source.addItem("Vial 3")
        self.vials_source.addItem("Vial 4")
        vials_source_label = QLabel("Source")
        self.vials_delivery = QComboBox()
        vials_delivery_label = QLabel("Delivery")
        self.vials_delivery.addItem("to animal")
        self.vials_delivery.addItem("to exhaust")
        self.vials_stabilisation = QDoubleSpinBox()
        self.vials_stabilisation.setRange(0, 10000)
        self.vials_stabilisation.setSingleStep(1)
        vials_stabilisation_label = QLabel("Stabilisation [s]")
        self.vials_pulse = QDoubleSpinBox()
        self.vials_pulse.setRange(0, 10000)
        self.vials_pulse.setSingleStep(0.1)
        vials_pulse_label = QLabel("Pulse [s]")
        
        layout = QGridLayout()
        layout.addWidget(vials_source_label, 0, 0)
        layout.addWidget(self.vials_source, 1, 0)
        layout.addWidget(vials_delivery_label, 0, 1)
        layout.addWidget(self.vials_delivery, 1, 1)
        layout.addWidget(vials_stabilisation_label, 0, 2)
        layout.addWidget(self.vials_stabilisation, 1, 2)    
        layout.addWidget(vials_pulse_label, 0, 3)
        layout.addWidget(self.vials_pulse, 1, 3)   
        self.vialsBox.setLayout(layout)     
        
        

class PyBehaviour(QWidget):
    
    def __init__(self):
        super().__init__()
        
        self.createSessionInformation()
        self.setDefaults()
        
        # make a callbacks/connects folder
        self.struct_seq.clicked.connect(self.loadTrialSequence)
        
        pybehaviourLayout = QVBoxLayout()
        pybehaviourLayout.addWidget(self.sessionInformation_scroll)
        self.setLayout(pybehaviourLayout)
        
    
    def setDefaults(self):
        
        self.general_name.setText("Fridolin")        
        self.struct_odour1.setValue(0.3)
        self.struct_gap.setValue(5)
        self.struct_odour2.setValue(0.3)

        self.conts_vials.setItem(0, 0, QTableWidgetItem("1"))
        self.conts_vials.setItem(1, 0, QTableWidgetItem("2"))
        self.conts_vials.setItem(2, 0, QTableWidgetItem("3"))
        self.conts_vials.setItem(3, 0, QTableWidgetItem("4"))        
        self.conts_vials.setItem(0, 1, QTableWidgetItem("A"))
        self.conts_vials.setItem(1, 1, QTableWidgetItem("X"))
        self.conts_vials.setItem(2, 1, QTableWidgetItem("B"))
        self.conts_vials.setItem(3, 1, QTableWidgetItem("Y"))
        self.conts_vials.setItem(0, 2, QTableWidgetItem("methylbutyrate"))
        self.conts_vials.setItem(1, 2, QTableWidgetItem("ethylpropionate"))
        self.conts_vials.setItem(2, 2, QTableWidgetItem("pinene"))
        self.conts_vials.setItem(3, 2, QTableWidgetItem("benzaldehyde"))
        
        self.conts_types.setItem(0, 0, QTableWidgetItem("1"))
        self.conts_types.setItem(1, 0, QTableWidgetItem("2"))
        self.conts_types.setItem(2, 0, QTableWidgetItem("3"))
        self.conts_types.setItem(3, 0, QTableWidgetItem("4"))
        self.conts_types.setItem(0, 1, QTableWidgetItem("0"))
        self.conts_types.setItem(1, 1, QTableWidgetItem("0"))
        self.conts_types.setItem(2, 1, QTableWidgetItem("0"))
        self.conts_types.setItem(3, 1, QTableWidgetItem("0"))
        self.conts_types.setItem(0, 2, QTableWidgetItem("A"))
        self.conts_types.setItem(1, 2, QTableWidgetItem("X"))
        self.conts_types.setItem(2, 2, QTableWidgetItem("A"))
        self.conts_types.setItem(3, 2, QTableWidgetItem("X"))
        self.conts_types.setItem(0, 3, QTableWidgetItem("B"))
        self.conts_types.setItem(1, 3, QTableWidgetItem("Y"))
        self.conts_types.setItem(2, 3, QTableWidgetItem("Y"))
        self.conts_types.setItem(3, 3, QTableWidgetItem("B"))


    def createSessionInformation(self):
        self.sessionInformation = QGroupBox("Session information")
        self.sessionInformation.setMinimumWidth(450)
    
        # 1: general
        self.general_name = QLineEdit()
        general_name_label = QLabel("Animal ID")
        self.general_notes = QTextEdit()
        general_notes_label = QLabel("Notes")
        
        sessionInformation_general = QGroupBox("General")
        layout = QGridLayout()
        layout.addWidget(general_name_label, 0, 0)
        layout.addWidget(self.general_name, 0, 1)
        layout.addWidget(general_notes_label, 1, 0)
        layout.addWidget(self.general_notes, 1, 1)
        sessionInformation_general.setLayout(layout)
            
        # 2: trial structure
        self.struct_odour1 = QDoubleSpinBox()
        self.struct_odour1.setRange(0, 100)
        self.struct_odour1.setSingleStep(0.1)   
        self.struct_gap = QDoubleSpinBox()
        self.struct_gap.setRange(0, 100)
        self.struct_gap.setSingleStep(1) 
        self.struct_odour2 = QDoubleSpinBox()
        self.struct_odour2.setRange(0, 100)
        self.struct_odour2.setSingleStep(0.1)  
        struct_odour1_label = QLabel("1st Odour [s]")
        struct_gap_label = QLabel("Gap [s]")
        struct_odour2_label = QLabel("2nd Odour [s]")      
        self.struct_seq = QPushButton("Load trial sequence")
        self.struct_seq_name = QLabel()
        self.struct_trials_label = QLabel()
        sessionInformation_struct = QGroupBox("Trial structure")
        
        layout = QGridLayout()
        layout.addWidget(struct_odour1_label, 0, 0)
        layout.addWidget(struct_gap_label, 0, 1)
        layout.addWidget(struct_odour2_label, 0, 2)
        layout.addWidget(self.struct_odour1, 1, 0)
        layout.addWidget(self.struct_gap, 1, 1)
        layout.addWidget(self.struct_odour2, 1, 2)
        layout.addWidget(self.struct_seq, 3, 0)
        layout.addWidget(self.struct_seq_name, 3, 1)
        layout.addWidget(self.struct_trials_label, 3, 2)
        sessionInformation_struct.setLayout(layout)
        
        # 3: vials
        self.conts_vials = QTableWidget(4, 3)
        self.conts_vials.verticalHeader().hide()
        self.conts_vials.horizontalHeader().setStretchLastSection(True)
        self.conts_vials.setHorizontalHeaderItem(0, QTableWidgetItem("Vial"))
        self.conts_vials.setHorizontalHeaderItem(1, QTableWidgetItem("Odour"))
        self.conts_vials.setHorizontalHeaderItem(2, QTableWidgetItem("Odorant"))
        
        contingencyTables_vials = QGroupBox("Vials")
        layout = QHBoxLayout()
        layout.addWidget(self.conts_vials)
        contingencyTables_vials.setLayout(layout)
        
        # 4: trial types
        self.conts_types = QTableWidget(4, 4)
        self.conts_types.verticalHeader().hide()
        self.conts_types.horizontalHeader().setStretchLastSection(True)
        self.conts_types.setHorizontalHeaderItem(0, QTableWidgetItem("Stim"))
        self.conts_types.setHorizontalHeaderItem(1, QTableWidgetItem("Variation"))
        self.conts_types.setHorizontalHeaderItem(2, QTableWidgetItem("1st Odour"))
        self.conts_types.setHorizontalHeaderItem(3, QTableWidgetItem("2nd Odour"))
        
        contingencyTables_types = QGroupBox("Trial types")
        layout = QHBoxLayout()
        layout.addWidget(self.conts_types)
        contingencyTables_types.setLayout(layout)
        
        layout = QVBoxLayout()
        layout.addWidget(sessionInformation_general)
        layout.addWidget(sessionInformation_struct)
        layout.addWidget(contingencyTables_vials)
        layout.addWidget(contingencyTables_types)
        self.sessionInformation.setLayout(layout)
        
        self.sessionInformation_scroll = QScrollArea()
        self.sessionInformation_scroll.setWidget(self.sessionInformation)
        
        
    def loadTrialSequence(self):
        filepath = str(QFileDialog.getOpenFileName(self, 'Load trial sequence', dir_seq, '*.txt')[0])
        if filepath:
            arr = np.genfromtxt(filepath, delimiter=',')
            trialOrder = arr[0]
            p['trialOrder'] = ((("".join(np.array2string(trialOrder))).replace(" ", "")).replace(".", "")).replace("\n", "")
            trialVariations = arr[1]
            p['trialVariations'] = ((("".join(np.array2string(trialVariations))).replace(" ", "")).replace(".", "")).replace("\n", "")
            filename = os.path.splitext(os.path.basename(filepath))[0]
            self.struct_seq_name.setText('File: ' + filename)
            self.struct_trials = len(p['trialOrder'])-2
            p['numTrials'] = str(self.struct_trials)
            self.struct_trials_label.setText('Number of trials: ' + str(self.struct_trials)) 

class Window(QDialog):
    
    def __init__(self):
        super().__init__()
        
        self.trial_log = []
        
        # create the worker thread (run trials in the background)
        self.executerThread = QThread()
        self.executer = Executer()
        self.executer.moveToThread(self.executerThread)
        self.executerThread.start()
        
        # create the sensor thread
        self.sensorThread = QThread()
        self.sensor = Sensor()
        self.sensor.moveToThread(self.sensorThread)
        self.sensorThread.start()
        
        self.tabs = QTabWidget()
        self.manual = Manual()
        self.tabs.addTab(self.manual, "Manual mode")
        self.pyBehaviour = PyBehaviour()
        self.tabs.addTab(self.pyBehaviour, "PyBehaviour mode")
        
        self.createDeviceBox()
        self.createControlBox()
        self.setConnects()
        self.initWindow()
        
        
    def initWindow(self):
        
        self.title = "SniffinHippo"     
        self.setWindowIcon(QtGui.QIcon('C:\\Setup\\SniffinHippo\\icon.png'))
        self.top = 100#100
        self.left = 100#100
        self.width = 530#680
        self.height = 100#500    
        
        self.setWindowTitle(self.title)
        self.setGeometry(self.top, self.left, self.width, self.height)
        
        mainLayout = QVBoxLayout()
        mainLayout.addWidget(self.deviceBox)
        mainLayout.addWidget(self.tabs)
        mainLayout.addWidget(self.controlBox)
        self.setLayout(mainLayout)
        
    def createDeviceBox(self):
        self.deviceBox = QGroupBox("Arduino")
        
        device_port_label = QLabel("Device")
        self.device_port = QComboBox()
        self.device_port.addItems(available_devices)
        self.device_connect = QPushButton()
        self.device_connect.setCheckable(True)

        # set defaults
        self.device_connect.setText("Connect")
        self.deviceBox.setStyleSheet('QGroupBox {\n    border: 1px solid rgb(225, 225, 225);\n    margin-top: 1.1em;\n   background-color: rgb(255, 234, 238);\n}\n\nQGroupBox::title {\n    subcontrol-origin: margin;\n}')

        
        layout = QHBoxLayout()
        layout.addWidget(device_port_label)
        layout.addWidget(self.device_port)
        layout.addWidget(self.device_connect)
        self.deviceBox.setLayout(layout)
        
    def createControlBox(self):
        self.controlBox = QGroupBox("Control")
        
        self.execute = QPushButton()
        self.execute.setCheckable(True)
        
        # set defaults
        self.execute.setText("Execute")
        self.controlBox.setStyleSheet('QGroupBox {\n    border: 1px solid rgb(225, 225, 225);\n    margin-top: 1.1em;\n   background-color: rgb(255, 234, 238);\n}\n\nQGroupBox::title {\n    subcontrol-origin: margin;\n}')

        layout = QHBoxLayout()
        layout.addWidget(self.execute)
        self.controlBox.setLayout(layout)
        
    def setConnects(self):
        
        self.executer.comm_feed_signal.connect(self.updateCommFeed)
        
        self.device_connect.clicked.connect(self.connectDisconnect)
        self.executer.arduino_connected_signal.connect(self.arduinoConnected)
        self.executer.arduino_disconnected_signal.connect(self.arduinoDisconnected)
        
        self.execute.clicked.connect(self.executeAbort)


    def updateCommFeed(self, input_string, device=None):
        
        # write to text file
        if device == 'pc':
            input_string = 'PC:      ' + input_string
        elif device == 'arduino':
            input_string = 'ARDUINO: ' + input_string
        elif device == 'trial':
            input_string = input_string
        self.trial_log.append(input_string)
        
        # print to terminal/command window
        if device == 'pc':
            input_string = colored(input_string, 'cyan')
        elif device == 'arduino':
            input_string = colored(input_string, 'yellow')
        elif device == 'trial':
            input_string = colored(input_string, 'grey', 'on_white')
        elif device == 'session':
            input_string = colored(input_string, 'white', 'on_red')    
        print(input_string)

    # --- CONNECT VS DISCONNECT ---
    def connectDisconnect(self):
        if arduino['connected'] is False:
            self.executer.connectArduino()
            self.sensor.startSensing()
        elif arduino['connected'] is True:
            self.executer.disconnectArduino()
            self.sensor.timer.stop()
    def arduinoConnected(self):
        self.device_connect.setText("Disconnect")
        self.deviceBox.setStyleSheet('QGroupBox {\n    border: 1px solid rgb(225, 225, 225);\n    margin-top: 1.1em;\n   background-color: rgb(226, 255, 242);\n}\n\nQGroupBox::title {\n    subcontrol-origin: margin;\n}')
    def arduinoDisconnected(self):
        self.device_connect.setText("Connect")      
        self.deviceBox.setStyleSheet('QGroupBox {\n    border: 1px solid rgb(225, 225, 225);\n    margin-top: 1.1em;\n   background-color: rgb(255, 234, 238);\n}\n\nQGroupBox::title {\n    subcontrol-origin: margin;\n}')

    # --- EXECUTE VS ABORT ---
    def executeAbort(self):
        if arduino['executing'] is False:
            self.executer.transmitConfig()
            arduino['executing'] = True
            self.executing()
        elif arduino['executing'] is True:
            self.executer.transmitAbort()
            arduino['executing'] = False
            self.notExecuting()
    def executing(self):
        self.execute.setText("Abort!")
        self.controlBox.setStyleSheet('QGroupBox {\n    border: 1px solid rgb(225, 225, 225);\n    margin-top: 1.1em;\n   background-color: rgb(226, 255, 242);\n}\n\nQGroupBox::title {\n    subcontrol-origin: margin;\n}')
    def notExecuting(self):
        self.execute.setText("Execute!")
        self.controlBox.setStyleSheet('QGroupBox {\n    border: 1px solid rgb(225, 225, 225);\n    margin-top: 1.1em;\n   background-color: rgb(255, 234, 238);\n}\n\nQGroupBox::title {\n    subcontrol-origin: margin;\n}')


if __name__ == '__main__':
    
    # set directories
    dir_exp = 'C:\\Data\\SniffinHippo' #'C:\\Users\\Virtual Hippo\\Desktop\\Moritz\\Data'
    if not os.path.exists(dir_exp):
        os.makedirs(dir_exp)

    dir_seq = 'C:\\Data\\SniffinHippo' #'Trial sequences'
    if not os.path.exists(dir_seq):
        os.makedirs(dir_seq)
    
    available_devices = serial_ports.list_ports()    
            
    # initialise global variables
    global arduino
    global p

    arduino = {}
    arduino['connected'] = False
    arduino['executing'] = False
    p = {}
    
    # create application
    time.sleep(0.1)
    app = QCoreApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    if os.name == 'nt':
        myappid = 'SniffinHippo'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    
    # launch GUI
    GUI = Window()
    GUI.show()
    GUI.raise_()
    ret = app.exec_()
    GUI.sensor.timer.stop()
    sys.exit(ret) 
    
    
    
    
    