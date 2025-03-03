
# Crontab-Einträge modifizieren in Abhängigkeit von Sommerzeit und Sonnenuntergang

import time, sys

import mariadb
import base64

from gmbasis import CBaseApp
from crontab import CronTab


class CModifyCrontab(CBaseApp):

   ###### __init__(self) ##############################################################################
   def __init__(self):
       super().__init__()
       self.vInit('opendtu')

     
   ###### vInit(self, sAppName) ##############################################################################
   def vInit(self, sAppName):
      super().vInit(sAppName)

   ###### AktualisiereCrontab(self) ##############################################################################
   # Den cron-Einträge für den Aufruf beim Sonnenuntergang aktualisieren
   # Dafür wurde https://pypi.org/project/python-crontab/ installiert
   def AktualisiereCrontab(self):
      try:
         #fkt, aber leer: cron    = CronTab()
         #fkt: cron    = CronTab(user='admin2')
         #fkt nicht: cron = CronTab(user='root')   
         cron  = CronTab(user=True)

         # Eintrag für das Scripts zum Einschalten der OpenDTU mittags:
         itr = cron.find_command('sh /mnt/wd2tb/script/opendtu/opendtu_switch_on_1200.sh')
         content = list(itr)
         if len(content) <= 0:
            return False
         job = content[0]
         job.setall(f'48 {12 if self.bSommerZeit else 11} * * *')
         job.enable()

         # Eintrag für das Ausführen des Abfragescripts mittags:
         itr = cron.find_command('sh /mnt/wd2tb/script/opendtu/opendtu.sh')
         content = list(itr)
         if len(content) <= 0:
            return
         job = content[0]
         job.setall(f'2 {13 if self.bSommerZeit else 12} * * *')
         job.enable()

         # Eintrag für das Scripts zum Einschalten der OpenDTU zum Sonnenuntergang:
         itr = cron.find_command('sh /mnt/wd2tb/script/opendtu/opendtu_switch_on_sunset.sh')
         content = list(itr)
         if len(content) <= 0:
            return False
         job = content[0]
         job.setall(f'{self.tSonnenuntergang.minute-10} {self.tSonnenuntergang.hour - 1} * * *')
         job.enable()


         # Eintrag für das Ausführen des Abfragescripts zum Sonnenuntergang:
         itr = cron.find_command('sh /mnt/wd2tb/script/opendtu/opendtu_sunset.sh')
         content = list(itr)
         if len(content) <= 0:
            return
         job = content[0]
         job.setall(f'{self.tSonnenuntergang.minute} {self.tSonnenuntergang.hour - 1} * * *')
         job.enable()

         cron.write()

         # weitere Job-Befehle
         #self.Info2Log(f'Cronjob-Kommentar: {job.comment}')
         #self.Info2Log(f'Cronjob-Befehl: {self.tSonnenuntergang.minute} {self.tSonnenuntergang.hour - 1} * * * {job.command}')

         # for line in cron.lines:
         #     print(f'crontab line: {line}')

         # Löschen und de-/aktivieren:
         # cron.remove( job )
         # job.enable(False)
         # job.enable()
         # if job.is_enabled():
         #    print('Enabled')

         return True
      
      except Exception as e:
        self.vScriptAbbruch(f'Ausnahme in CModifyCrontab: {e}')

def main(argv):
   mc = CModifyCrontab()           # u.a. die Konfigdatei lesen 

   mc.VerbindeMitMariaDb()            # Verbindung zur DB herstellen, zweite Verbindung fürs Log

   if mc.sHostName != 'solarraspi':
      mc.vEndeNormal(f'Script kann nur auf dem Raspi ausgeführt werden.')
      
   try:
      if not mc.AktualisiereCrontab():
         mc.vScriptAbbruch('Fehler beim Modifizieren der Crontab-Einträge.')
   
   except Exception as e:
         mc.vScriptAbbruch(f'Ausnahme in CModifyCrontab: {e}')

   mc.vEndeNormal(f'Crontab-Einträge wurden modifiziert.')




if __name__ == "__main__":
    main(sys.argv)

