
# Relais einschalten: Channel 1, BCM-Pin 26

import time, sys

import mariadb
import base64

import socket
import subprocess

from gmbasis import CBaseApp

import RPi.GPIO as GPIO 

class COpenDtuOnOff (CBaseApp):

   ###### __init__(self) ##############################################################################
   def __init__(self):
       super().__init__()
       self.vInit('opendtu')

     
   ###### vInit(self, sAppName) ##############################################################################
   def vInit(self, sAppName):
      super().vInit(sAppName)


def main(argv):
   ooo = COpenDtuOnOff()           # u.a. die Konfigdatei lesen 

   ooo.VerbindeMitMariaDb()            # Verbindung zur DB herstellen, zweite Verbindung fürs Log

   if ooo.sHostName != 'solarraspi':
      ooo.vEndeNormal(f'Script kann nur auf dem Raspi ausgeführt werden.')
      
   pin = 26

   if len(argv) < 2:
      ooo.vScriptAbbruch(f'Aufruf: opendtu_switch_on_off.py on ... Pin26/Relais1 einschalten, opendtu_switch_on_off.pyoff ... Pin26/Relais1 ausschalten')
   sStat = argv[1].lower()
   if sStat == 'on':
        stat = GPIO.HIGH
   elif sStat == 'off':
        stat = GPIO.LOW
   else:
        ooo.vScriptAbbruch(f'Aufruf: opendtu_switch_on_off.py on ... Pin26/Relais1 einschalten, opendtu_switch_on_off.pyoff ... Pin26/Relais1 ausschalten')

   try:
        GPIO.setmode(GPIO.BCM)

        for v in range (1,4,1):
           if v == 1:
              GPIO.setup( pin, GPIO.OUT) #schaltet das Relais bereits ein (anders als das China-8-Kanal-Board)
           else:
              GPIO.output( pin, stat)

        GPIO.cleanup()   
              
   except Exception as e:
           sErr = f'Ausnahme in opendtu_switch_on(): {e}'
           ooo.vScriptAbbruch(sErr)

   ooo.vEndeNormal(f'GPIO Pin {pin} {stat}.')




if __name__ == "__main__":
    main(sys.argv)

