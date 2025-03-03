# Script für die Abfrage des Ertrags und für das Einstellen des Limits, des Abfrageintervalls und der Sendeleistung
# im Zusammenspiel zwischen OpenDTU-Sende/Empfangseinheit und Hoymiles-Wechselrichter

# Hier gefunden: https://github.com/Selbstbau-PV/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-Shelly3EM
# Testergebnis gepostet: https://github.com/Selbstbau-PV/Selbstbau-PV-Hoymiles-nulleinspeisung-mit-OpenDTU-und-Shelly3EM/issues/29
# API siehe https://www.opendtu.solar/firmware/web_api/
#           https://www.opendtu.solar/firmware/configuration/dtu_settings/

# Die Ertragswerte werden einmal täglich eine Stunde vor dem Sonnenuntergang abgefragt, um den Tagesertrag zu ermitteln.
# Zusätzlich werden die Ertragswerte um 12 Uhr (bei Winterzeit um 13 Uhr) abgefragt, um den Maximalwert der Module (etwa Südausrichtung) zu ermitteln.

# Dieses Script wird über crontab aufgerufen, Bearbeitung mit crontab -e:
# Taeglich um 12:02 und um 13:02 die maximalen Ertragswerte abholen. Das Script prueft die Sommerzeit und fuehrt seine Funktionen nur um 12 Uhr Sonnenzeit aus
# Aktualisiert die beiden Crontab-Einträge unten
# 2 12 * * * sh /mnt/wd2tb/script/opendtu/opendtu.sh
# 2 13 * * * sh /mnt/wd2tb/script/opendtu/opendtu.sh

# Minute und Stunde wird mittags von opendtu-py mit Hilfe von python-crontab auf eine Stunde vor Sonenuntergang aktualisiert
# 5VDC einschalten
# 38 16 * * * sh /mnt/wd2tb/script/opendtu/opendtu_switch_on.sh

# Abfragen und danach 5VDC ausschalten
# 48 16 * * * sh /mnt/wd2tb/script/opendtu/opendtu_sunset.sh



#!/usr/bin/env python3

import logging
import requests, time, sys
from requests.auth import HTTPBasicAuth

import datetime
import json

import mariadb
import base64

import socket
import subprocess

from gmbasis import CBaseApp

from crontab import CronTab

# Einstellungen: 
sn_hoy20241gh = "116491111111" # Seriennummer des Hoymiles Wechselrichters 

dtu_nutzer = '********' # OpenDTU Nutzername
dtu_passwort = '********' # OpenDTU Passwort


###### CInverterDaten ##############################################################################
###### Container für die Daten eines Wechselrichters ###############################################
class CInverterDaten:
   def __init__(self, sInvSn):
      self.sName = '?'
      self.sSn = sInvSn
      
      self.reachable = False
      self.producing = False

      self.nSendeDbm = 0
      self.altes_limit = 0

      self.dPowerAc1   = 0.0
      self.d_temperature1 = 0.0

      self.sNameModule11  = '?'
      self.sNameModule12  = '?'
      self.sNameModule13  = '?'
      self.sNameModule14  = '?'

      self.d_yieldModule11Now  = 0.0
      self.d_yieldModule12Now  = 0.0
      self.d_yieldModule13Now  = 0.0
      self.d_yieldModule14Now  = 0.0
      
      self.d_yieldModule11  = 0.0
      self.d_yieldModule12  = 0.0
      self.d_yieldModule13  = 0.0
      self.d_yieldModule14  = 0.0

      self.d_yieldModule11Day  = 0.0
      self.d_yieldModule12Day  = 0.0
      self.d_yieldModule13Day  = 0.0
      self.d_yieldModule14Day  = 0.0


      # es würde reichen, diese Daten nur bei einem Inverter mit abzufragen:
      self.yieldTotal       = '?'
      self.d_yieldTotal     = 0,0
      self.yieldToday       = '?'
      self.d_yieldToday     = 0.0


###### COpenDtuSteuerung ##############################################################################
class COpenDtuSteuerung (CBaseApp):

   ###### __init__(self) ##############################################################################
   def __init__(self):
       super().__init__()
       self.vInit('opendtu')

      
   ###### vInit(self, sAppName) ##############################################################################
   def vInit(self, sAppName):
      
      super().vInit(sAppName)

      try:
         self.sDtuIp =  self.Settings['DTU']['Ip'] 
         self.nSendeIntervall =  self.Settings['DTU']['SendeIntervall'] 
         self.nSendeDbm = 0  #Schleife läuft von 5 bis 20

         if self.sHostName == 'solarraspi':
            self.sDateipfad = self.Settings['Datei']['Pfad_raspi'] 
         elif self.sHostName == 'leno2018':
            self.sDateipfad = self.Settings['Datei']['Pfad_leno'] 

         self.nLimit = int(self.Settings['Inverter']['Limit'])
         self.aInv = [CInverterDaten(sn_hoy20241gh)]

      except Exception as e:
         sErr = f'Ausnahme in COpenDtuSteuerung.vInit: {e}'
         self.vScriptAbbruch(sErr)


   ###### def bIstOpenDtuErreichbar(self) ##############################################################################
   def bIstOpenDtuErreichbar(self):
      if self.sHostName == 'solarraspi':
         command = ['ping', '-c', '1', self.sDtuIp]  # Für Raspbian
     
      elif self.sHostName == 'leno2018':
         command = ['ping', '-n', '1', self.sDtuIp]  # Für Windows

      try:
         output = subprocess.check_output(command, stderr=subprocess.STDOUT) #fktnicht: universal_newlines=True)
         sOutput = output.decode('utf-8', errors='replace') # ohne errors='replace' gibt es eine Ausnahme

         sLower = sOutput.lower()
         if "zielhost nicht erreichbar" in sLower or "destination host unreachable" in sLower:
            return False  # Gerät ist nicht erreichbar
         else:
            return True  # Gerät ist erreichbar

      except subprocess.CalledProcessError as e:
         self.Error2Log(f'subprocess.CalledProcessError-Ausnahme in bIstOpenDtuErreichbar: ret: {e.returncode}: output: {e.output}'  )
         return False  # Gerät ist nicht erreichbar


   ###### SetzeSendeleistung(self, nDbm) ##############################################################################
   def SetzeSendeleistung(self, nDbm):
      try:
         print(f'Versuch mit {nDbm} dBm')

         # In den Parametern ist viel Dynamik drin. Deshalb immer erst alle Paramter holen
         # und ggf unten ergänzen. post(api/dtu/config) ist nicht sehr tolerant, was fehlende Parameter angeht!
         ret = requests.get(
                  url = f'http://{self.sDtuIp}/api/dtu/config',
                  auth = HTTPBasicAuth(dtu_nutzer, dtu_passwort),
                  headers = {'Content-Type': 'application/x-www-form-urlencoded'}
         )
         jData = ret.json()
         #sPretty = json.dumps( jData, sort_keys=True, indent=2)
         #logging.info(sPretty)

         sendeleistung = int(jData["cmt_palevel"])
         if sendeleistung == int(nDbm):
            return True
         
         sendeleistung = f'{jData["cmt_palevel"]} dBm'
         sendefrequenz = f'{round(jData["cmt_frequency"] /1000)} Mhz'
         d_sendefrequenz = round(jData["cmt_frequency"] /1000)
         
         serialOpenDtu = jData["serial"] # Achtung! Das ist die Seriennummer der OpenDTU-Unit, diese muss bei post(api/dtu/config) angegeben werden!
         #  '199980120484'

         # Abfrageintervall und Sendeleistung setzen
         ret = requests.post(
                  url = f'http://{self.sDtuIp}/api/dtu/config',
                  data = f'data={{"serial":"{serialOpenDtu}", "pollinterval":{self.nSendeIntervall},\
                  "nrf_enabled": "true", "nrf_palevel":0,\
                  "cmt_country": 0, "cmt_chan_width": 250000,\
                  "cmt_enabled": "true", "cmt_palevel":{nDbm},"cmt_frequency": 865000000}}',
                  auth = HTTPBasicAuth(dtu_nutzer, dtu_passwort),
                  headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            ).json()
         if ret["type"] == 'success':
            self.Info2Log( f'Sendeleistung {nDbm}  gesetzt')         
            return True
         else:
            return False
         
      except Exception as e:
         self.Error2Log(f'Fehler beim Setzen der Sendeleistung ({nDbm} dBm): {e}')
         return False

            
   ###### HoleErtragswerte(self) ##############################################################################
   def HoleErtragswerte(self):
      try:
         # Nimmt Daten von der openDTU Rest-API und übersetzt sie in ein json-Format
         # liefert seit März 2024 leider nur noch rudimentäre Daten:
         # r = requests.get(url = f'http://{self.sDtuIp}/api/livedata/status/inverters' ).json()
         # Seit März 2024 muss man jeden Wechselrichter einzeln abfragen, wenn man an die Temperatur und die Moduldaten heran will

         for inv in self.aInv:
      
            r1 = requests.get(url = f'http://{self.sDtuIp}/api/livedata/status?inv={inv.sSn}' ).json()
            # sPretty1 = json.dumps( r1, sort_keys=True, indent=2)
            # logging.info(sPretty1)

            if len(r1['inverters']) == 0:
               return 'notreachable'
                      
            # zuerst die Inverter-spezifischen Daten vom ersten Inverter:
            inv.reachable   = r1['inverters'][0]['reachable'] # Ist erreichbar?
            if inv.reachable == False:
               return 'notreachable'

            inv.sName = r1['inverters'][0]['name'] 

            inv.producing   = int(r1['inverters'][0]['producing']) # Produziert der Wechselrichter etwas?
            inv.altes_limit = int(r1['inverters'][0]['limit_absolute']) # Altes Limit

            inv.dPowerAc1   = round(r1['inverters'][0]['AC']['0']['Power']['v'],1) # Gesamtleistung AC in Watt

            # MUP: Nach dem Einschalten der DTU liefert sie in den ersten 5(?) Minuten leider keine Ertragswerte
            if inv.dPowerAc1 <= 0.0:
               return 'notreachable'
            
            inv.d_temperature1 = round(r1['inverters'][0]['INV']['0']['Temperature']['v'],1)
            
            inv.d_yieldTotal       = round(r1['inverters'][0]['INV']['0']['YieldTotal']['v'] ,1)
            inv.d_yieldToday       = round(r1['inverters'][0]['INV']['0']['YieldDay']['v'] / 1000 ,3)
            
            inv.sNameModule11  = r1['inverters'][0]['DC']['0']['name']['u']
            inv.sNameModule12  = r1['inverters'][0]['DC']['1']['name']['u']
            inv.sNameModule13  = r1['inverters'][0]['DC']['2']['name']['u']
            inv.sNameModule14  = r1['inverters'][0]['DC']['3']['name']['u']

            inv.d_yieldModule11Now  = round(r1['inverters'][0]['DC']['0']['Power']['v'],1)
            inv.d_yieldModule12Now  = round(r1['inverters'][0]['DC']['1']['Power']['v'],1)
            inv.d_yieldModule13Now  = round(r1['inverters'][0]['DC']['2']['Power']['v'],1)
            inv.d_yieldModule14Now  = round(r1['inverters'][0]['DC']['3']['Power']['v'],1)

            inv.d_yieldModule11  = round(r1['inverters'][0]['DC']['0']['YieldTotal']['v'],1)
            inv.d_yieldModule12  = round(r1['inverters'][0]['DC']['1']['YieldTotal']['v'],1)
            inv.d_yieldModule13  = round(r1['inverters'][0]['DC']['2']['YieldTotal']['v'],1)
            inv.d_yieldModule14  = round(r1['inverters'][0]['DC']['3']['YieldTotal']['v'],1)

            yieldModule11DayUnit  = r1['inverters'][0]['DC']['0']['YieldDay']['u']
            yieldModule12DayUnit  = r1['inverters'][0]['DC']['1']['YieldDay']['u']
            yieldModule13DayUnit  = r1['inverters'][0]['DC']['2']['YieldDay']['u']
            yieldModule14DayUnit  = r1['inverters'][0]['DC']['3']['YieldDay']['u']

            d_yieldModule11DayMulti  = 1000.0 if yieldModule11DayUnit.lower() == 'wh' else 1
            d_yieldModule12DayMulti  = 1000.0 if yieldModule12DayUnit.lower() == 'wh' else 1
            d_yieldModule13DayMulti  = 1000.0 if yieldModule13DayUnit.lower() == 'wh' else 1
            d_yieldModule14DayMulti  = 1000.0 if yieldModule14DayUnit.lower() == 'wh' else 1

            inv.d_yieldModule11Day  = round(r1['inverters'][0]['DC']['0']['YieldDay']['v'] / d_yieldModule11DayMulti ,3)
            inv.d_yieldModule12Day  = round(r1['inverters'][0]['DC']['1']['YieldDay']['v'] / d_yieldModule12DayMulti ,3)
            inv.d_yieldModule13Day  = round(r1['inverters'][0]['DC']['2']['YieldDay']['v'] / d_yieldModule13DayMulti ,3)
            inv.d_yieldModule14Day  = round(r1['inverters'][0]['DC']['3']['YieldDay']['v'] / d_yieldModule14DayMulti ,3)

            # dann beim ersten Inverter auch die Gesamtwerte aller Wechselrichter abfragen:
            inv.yieldTotalAll       = f"{round(r1['total']['YieldTotal']['v'] ,1)} kWh" # Ertrag gesamt
            inv.d_yieldTotalAll       = round(r1['total']['YieldTotal']['v'] ,1)
            inv.yieldTodayAll       = f"{round(r1['total']['YieldDay']['v'] / 1000,1)} kWh" # Ertrag heute
            inv.d_yieldTodayAll       = round(r1['total']['YieldDay']['v'] / 1000,1)

            # Ergebnisse in die Tabelle t_hoy2000 eintragen:
            stmt = f"INSERT INTO solar2023.t_hoy2000 (\
               Seriennummer, Zeitpunkt, GesamtAlle, HeuteAlle, Gesamt,Heute,\
               Modul1Gesamt,Modul2Gesamt, Modul3Gesamt, Modul4Gesamt,\
               Modul1Heute,Modul2Heute, Modul3Heute, Modul4Heute,\
               Modul1Jetzt,Modul2Jetzt, Modul3Jetzt, Modul4Jetzt,\
               Sendeleistung,Temperatur) \
               VALUES( '{inv.sSn}', SYSDATE(),{inv.d_yieldTotalAll}, {inv.d_yieldTodayAll}, {inv.d_yieldTotal}, {inv.d_yieldToday},\
               {inv.d_yieldModule11}, {inv.d_yieldModule12}, {inv.d_yieldModule13}, {inv.d_yieldModule14},\
               {inv.d_yieldModule11Day}, {inv.d_yieldModule12Day}, {inv.d_yieldModule13Day}, {inv.d_yieldModule14Day},\
               {inv.d_yieldModule11Now}, {inv.d_yieldModule12Now}, {inv.d_yieldModule13Now}, {inv.d_yieldModule14Now},\
              {self.nSendeDbm}, {inv.d_temperature1} )"

            cur = self.mdb.cursor()
            cur.execute( stmt)
            self.mdb.commit()

      except Exception as e:
         self.Error2Log( f'Ausnahme in HoleErtragswerte(): {e}')
         return 'notreachable'


   ###### SetzeLimit(self) ##############################################################################
   def SetzeLimit(self):
      try:

         # Abfrage des aktuellen Limits:
         #  http://xxx.xxx.xxx.xxx/api/limit/status
         #  Antwort: {"11649nnnnnnn":{"limit_relative":40,"max_power":2000,"limit_set_status":"Ok"}}
         #                |____das ist die Seriennummer der OpenDTU-Unit, nicht des Wechselrichters

         # Limit für den Wechselrichter setzen: 600W dauerhaft
         #  https://github.com/tbnobody/OpenDTU/discussions/742
         # limit_type = 0 AbsoluteNonPersistent
         # limit_type = 1 RelativeNonPersistent
         # limit_type = 256 AbsolutePersistent
         # limit_type = 257 RelativePersistent

         bFehler = False
         for inv in self.aInv:
            if inv.sName == '?':
               self.Error2Log( f'Limit {self.nLimit} setzen für {inv.sSn}/{inv.sName} nicht möglich')         
               bFehler = True
               continue;
            if inv.altes_limit == self.nLimit:
               continue;

            ret = requests.post(
                  url = f'http://{self.sDtuIp}/api/limit/config',
                  data = f'data={{"serial":"{inv.sSn}", "limit_type":256, "limit_value":{self.nLimit}}}',
                  auth = HTTPBasicAuth(dtu_nutzer, dtu_passwort),
                  headers = {'Content-Type': 'application/x-www-form-urlencoded'}
            ).json()
         
            if ret["type"] != 'success':
               self.Error2Log(f'Fehler beim Setzen des Limits für {inv.sName}: code: {ret["code"]}, message: {ret["message"]}')
               bFehler = True
               continue;
               
            self.Info2Log( f'Limit {self.nLimit} für {inv.sName} gesetzt')         

         return not bFehler


      except Exception as e:
        self.vScriptAbbruch(f'Ausnahme beim Setzen des Limits({self.nLimit}): {e}')
        return False

   ###### AktualisiereCrontab(self) ##############################################################################
   # Den cron-Einträge für den Aufruf beim Sonnenuntergang aktualisieren
   # Dafür wurde https://pypi.org/project/python-crontab/ installiert
   def AktualisiereCrontab(self):
      try:
         tTest = datetime.datetime( self.tSonnenuntergang.year, self.tSonnenuntergang.month, self.tSonnenuntergang.day, self.tSonnenuntergang.hour, self.tSonnenuntergang.minute)
         if self.tNow >= tTest:
            return
         
         #fkt, aber leer: cron    = CronTab()
         #fkt: cron    = CronTab(user='admin2')
         #fkt nicht: cron = CronTab(user='root')   
         cron  = CronTab(user=True)

         # Eintrag für das Scripts zum Einschalten der OpenDTU:
         itr = cron.find_command('sh /mnt/wd2tb/script/opendtu/opendtu_switch_on.sh')
         content = list(itr)
         if len(content) <= 0:
            return
         job = content[0]
         job.setall(f'{self.tSonnenuntergang.minute - 10} {self.tSonnenuntergang.hour - 1} * * *')
         job.enable()

         # Eintrag für das Ausführen des Abfragescripts:
         itr = cron.find_command('sh /mnt/wd2tb/script/opendtu/opendtu_sunset.sh')
         content = list(itr)
         if len(content) <= 0:
            return
         job = content[0]
         job.setall(f'{self.tSonnenuntergang.minute} {self.tSonnenuntergang.hour - 1} * * *')
         job.enable()
         #self.Info2Log(f'Cronjob-Kommentar: {job.comment}')
         #self.Info2Log(f'Cronjob-Befehl: {self.tSonnenuntergang.minute} {self.tSonnenuntergang.hour - 1} * * * {job.command}')
         cron.write()
         # for line in cron.lines:
         #     print(f'crontab line: {line}')

         # Löschen und de-/aktivieren:
         # cron.remove( job )
         # job.enable(False)
         # job.enable()
         # if job.is_enabled():
         #    print('Enabled')

      except Exception as e:
        self.vScriptAbbruch(f'Ausnahme in AktualisiereCrontab: {e}')


###### COpenDtuSteuerung } ##############################################################################

def main(argv):
   ods = COpenDtuSteuerung()           # u.a. die Konfigdatei lesen 

   ods.VerbindeMitMariaDb()            # Verbindung zur DB herstellen, zweite Verbindung fürs Log

   if ods.sHostName == 'solarraspi':
      ods.AktualisiereCrontab()

   if not ods.bIstOpenDtuErreichbar():
         sErr = f"Das Gerät mit der IP-Adresse {ods.sDtuIp} ist im Netzwerk nicht verfügbar."   
         ods.vScriptAbbruch(sErr)

   bErfolg = False
   for ods.nSendeDbm in range(2,20,1): # Sendeleistung steigern...im Sommer mit viel Blattwerk kann der Wechselrichter auf dem Gartenhaus nur mit 16dBm erreicht werden!

      if not ods.SetzeSendeleistung( ods.nSendeDbm):
         break

      if ods.HoleErtragswerte() == 'notreachable':      # Ertragswerte auslesen und in DB speichern
         continue
   
      if not ods.SetzeLimit():         # Vorgeschriebenes Limit kontrollieren und ggf einstellen
         continue

      bErfolg = True
      break



   if bErfolg: 
      ods.vEndeNormal(f'Limit setzen und Abfragen erfolgreich mit {ods.nSendeDbm} dbm.')
   else:
      ods.vScriptAbbruch(f'Limit setzen und Abfragen nicht oder nur teilweise möglich.')


if __name__ == "__main__":
    main(sys.argv)

