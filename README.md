# <img src="/Img/icon.png" height="30"> SniffinHippo

Olfactometer control application for automated behavioural training on olfactory tasks

<p align="center">
  <img src="/Img/OlfactoryTask.gif" width="700">
</p>


## Description

This software is used for operating custom-built air dilution olfactometers (like the one in the schematic below). It can be run standalone for manual presentation of odours or interfaced with PyBehaviour (https://github.com/llerussell/PyBehaviour) for odour presentation in a trial structure for automated behavioural training. We use it for memory tasks with olfactory stimuli like delayed non-match-to-sample, delayed paired-associates or transitive inference tasks. Since 2019, this software has been used by >10 scientists in the Hausser lab.

<p align="center">
  <img src="/Img/Olfactometer.gif" width="500">
</p>


## Manual mode

In Manual mode, the olfactometer valves can either be addressed individually or the valves required for odour presentation from a single vial can be controlled collectively. For fast and precise odour delivery, air is funneled through the odour vial already before odour presentation (stabilisation) such that odourised air can build up in the tubing all the way to the shuttle valve placed right in front of the animal's nose. During the odour pulse, the shuttle valve then directs the odour stream to the animal.

<p align="center">
  <img src="/Img/SniffinHippo_Manual.png" width="500">
</p>


## PyBehaviour mode

PyBehaviour mode allows SniffinHippo to be operated in conjunction with the behavioural task control software PyBehaviour (https://github.com/llerussell/PyBehaviour). A pre-defined trial sequence specifying the trial type for each trial can be uploaded as a text file to both PyBehaviour and SniffinHippo. Odour identities and trial type contingencies can be definted in SniffinHippo. At the beginning of each trial, SniffinHippo receives a trigger from PyBehaviour, which then launches the odour presentations for the respective trial. 

<p align="center">
  <img src="/Img/SniffinHippo_PyBehaviour.png" width="500">
</p>


## Installation

* Prerequisites
  * Python (e.g. 3.6): `numpy`,`PyQt5`,`pyserial`,`colorama`,`termcolor`
  * Arduino (e.g. Mega 2560) and [Arduino IDE](https://www.arduino.cc/en/Main/Software)
* Download or clone SniffinHippo
* Upload `Sketch/sketch.ino` to the arduino
* Install [PyBehaviour](https://github.com/llerussell/PyBehaviour) (if you would like to use SniffinHippo for automated behavioural training)
* Run
  *  `python SniffinHippo.py` (or double-click on SniffinHippo.bat file)
