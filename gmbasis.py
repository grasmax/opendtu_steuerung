import os
import sys
import base64

import time
import datetime
import suntime  #pip install suntime am 27.2.25, auch auf dem Solarraspi
import pytz     #pip install pytz am 27.2.25, auch auf dem Solarraspi


import json

import logging
from logging.handlers import RotatingFileHandler

from Crypto.Cipher import AES
from Crypto import Random
import smtplib
from email.mime.text import MIMEText

import mariadb

import socket
import subprocess

###### CAesCipher    ##############################################################################
#  https://stackoverflow.com/questions/12524994/encrypt-and-decrypt-using-pycrypto-aes-256 / 258
BS = 16
pad = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS).encode()
unpad = lambda s: s[:-ord(s[len(s)-1:])]
class CAesCipher:

   def __init__( self, TestCode):
        self.key = bytes(TestCode, 'utf-8')

   def encrypt( self, Text ):
      encText = Text.encode()
      raw = pad(encText)

      iv = Random.new().read( AES.block_size )
      cipher = AES.new( self.key, AES.MODE_CBC, iv )

      ce = base64.b64encode( iv + cipher.encrypt( raw ) )
      print (ce)
      return ce

   def decrypt( self, Text ):
      enc = base64.b64decode(Text)
      iv = enc[:16]
      cipher = AES.new(self.key, AES.MODE_CBC, iv )
      dec = cipher.decrypt( enc[16:] )
      u = unpad(dec)
      return u.decode("utf-8") 


###### CMailVersand   ##############################################################################
class CMailVersand:
   def __init__(self, sSmtpUser, sSmtpPwdCode, Von, An):
      
      self.SmtpUser = sSmtpUser
      self.SmtpPwdCode = sSmtpPwdCode
      self.Von = Von
      self.An = An

   ###### EmailVersenden(self, sBetreff, sText) ##############################################################################
   def EmailVersenden(self, sBetreff, sText, sTestCode):

    server = smtplib.SMTP_SSL('smtp.ionos.de',465,)
    # server.set_debuglevel(1)

    a = CAesCipher( sTestCode)
    server.login( self.SmtpUser, a.decrypt(self.SmtpPwdCode))
    
    message = MIMEText(sText, 'plain')
    message['Subject'] = sBetreff
    message['From'] = self.Von
    message['To'] = ", ".join(self.An)
    
    server.sendmail( self.Von, self.An,  message.as_string())
    # liefert sText nur als Byte-Folge: print(message.as_string()) 
    print(f'Von: {self.Von}, An: {self.An}, Betreff: {sBetreff}, Text: {sText}')
    server.quit()

###### CBaseApp {   ##############################################################################

class CBaseApp:

   ###### __init__(self) ##############################################################################
   def __init__(self):
      self.tNow = datetime.datetime.now()
      self.sNow = self.tNow.strftime("%Y-%m-%d-%H-%M")
      self.tJetztStunde = datetime.datetime( self.tNow.year, self.tNow.month, self.tNow.day, self.tNow.hour, 0)



   ###### def vInit(self, sAppName) ##############################################################################
   def vInit(self, sAppName):

      sLogDir = './log'
      if not os.path.exists(sLogDir):
         os.mkdir(sLogDir)
      
      logging.basicConfig(encoding='utf-8', level=logging.INFO, # absteigend: DEBUG, INFO, WARNING,ERROR, CRITICAL
                          # DEBUG führt dazu, dass der HTTP-Request samt Passwörtern und APIKeys geloggt wird!
                          style='{', datefmt='%Y-%m-%d %H:%M:%S', format='{asctime} {levelname} {filename}:{lineno}: {message}',
                          handlers=[RotatingFileHandler(f'{sLogDir}/{sAppName}.txt', maxBytes=100000, backupCount=20)],)
      logging.info(f'Programmstart um {self.sNow}')

      sCfgFile = f'{sAppName}.cfg' # sFile = "E:\\dev_priv\\python_svn\\opendtu\\opendtu.cfg"
      try:
         f = open(sCfgFile, "r")
      except Exception as e:
         logging.error(f'Fehler in open({sCfgFile}): {e}')
         quit()

      try:
         self.Settings = json.load(f)
         f.close()
      except Exception as e:
         logging.error(f'Fehler in json.load(): {e}')
         quit()

      self.sHostName = "unknown"
      try:
         self.sHostName =  socket.gethostname()
      except Exception as e:
          logging.error(f'Fehler bei socket.gethostname(): {e}')
          self.sHostName = "unknown"
      
      if self.sHostName == 'unknown':
         logging.error(f'Fehler: Hostname konnte nicht ermittelt werden')
         quit()      
      else:
         logging.info(f'Hostname: {self.sHostName}')

      
      try:
         self.bTestMode = True if self.Settings['Entwickler']['Testmode'] == 1 else False
         self.MariaIp = self.Settings['MariaDb']['IP']
         self.MariaUserCode = self.Settings['MariaDb']['User']
         self.MariaPwdCode = self.Settings['Pwd']['MariaDb']
         
         self.TestCode = self.Settings['Pwd']['Test']
         self.aes = CAesCipher(self.TestCode)

         self.mail = CMailVersand( self.Settings['Mail']['User'], self.Settings['Pwd']['Smtp'], self.Settings['Mail']['Von'], self.Settings['Mail']['An'])

         self.bSommerZeit = False
         sSommerzeit = 'nein'
         lt = time.localtime()
         if lt.tm_isdst:
            self.bSommerZeit = True
            sSommerzeit = 'ja'
         
         # 27.2.25
         # Aufgang:	06:57 Ortszeit Untergang:	17:42 Ortszeit
         self.latitude = self.Settings['Inverter']['latitude']
         self.longitude = self.Settings['Inverter']['longitude']

         sun = suntime.Sun(self.latitude, self.longitude)
         today_sr = sun.get_sunrise_time()
         today_ss = sun.get_sunset_time()

         tzBerlin = pytz.timezone('Europe/Berlin')
         self.tSonnenaufgang = today_sr.astimezone(tzBerlin)
         self.tSonnenuntergang = today_ss.astimezone(tzBerlin)
         # 2025-02-27 06:58:48+01:00    2025-02-27 17:40:48+01:00

         # jSun = {
         #    "Tag": self.sNow,
         #    "Aufgang": self.tSonnenaufgang.strftime("%Y-%m-%d-%H-%M"),
         #    "Untergang": self.tSonnenuntergang.strftime("%Y-%m-%d-%H-%M")
         # }
         # f = open("sunset.json", "w", encoding='utf-8')
         # json.dump(jSun, f, ensure_ascii=False, indent=4)
         # f.close()


         sF = "%d.%m.%Y %H:%M"
         sNow = f'Jetzt: {self.tNow.strftime(sF)}, Jetzt: {self.tJetztStunde.strftime(sF)}, Sommerzeit: {sSommerzeit}, Sonnenaufgang: {self.tSonnenaufgang.strftime(sF)}, Sonnenuntergang: {self.tSonnenuntergang.strftime(sF)}'
         print(sNow)
         logging.info(sNow)

      except Exception as e:
         logging.error(f'Fehler beim Einlesen von: {sCfgFile}: {e}')
         quit()

###### __Record2Log(self, eTyp, eLadeart, sText) ##############################################################################
   def __Record2Log(self, eTyp, sText):
   # Logeintrag in die Datenbank schreiben, bei Fehler auch in die Log-Datei
   #$$ stext auf 250 begrenzen, wenn länger -->Fehlermeldung und Text in die Logdatei
      cur = self.mdbLog.cursor()
      sStmt = f'insert into solar2023.t_prognose_log (tLog, eTyp, sText) values (sysdate(), "{eTyp}","{sText}")'
      try:
         cur.execute( sStmt)
         self.mdbLog.commit()
         if eTyp == "info":
            logging.info(sText)
         else:
            logging.error(sText)
         print(f'Logeintrag: {eTyp}: {sText}')

      except Exception as e:
         sErr = f'Fehler beim insert ({eTyp},{sText}) in mariadb.solar2023.t_charge_log: {e}'
         self.vScriptAbbruch(sErr)


   ###### Info2Log(self, sText) ##############################################################################
   def Info2Log(self, sText):
      self.__Record2Log( "info", sText)


   ###### Error2Log(self, sText) ##############################################################################
   def Error2Log(self, sText):
      self.__Record2Log( "error", sText)

  ###### vEndeNormal(self) ##############################################################################
   def vEndeNormal(self, sEnde):
   #Script beenden und aufräumen
      self.Info2Log(sEnde)
      self.Info2Log('mdb-close')
      self.mdb.close()
      self.mdbLog.close()
      print("Programmende")
      #unklar, wozu das gut ist: sys.stdout.flush() # write out cached messages to stdout
      quit()


   ###### vScriptAbbruch(self) ##############################################################################
   def vScriptAbbruch(self, sGrund):
   #Script beenden und aufräumen
      self.Error2Log(sGrund)
      self.Error2Log('Programmabbruch mit mdb-close und email')
      self.mdb.close()
      self.mdbLog.close()
      self.mail.EmailVersenden(f'OpenDTU-Problem. Script abgebrochen!', sGrund, self.TestCode)
      #unklar, wozu das gut ist: sys.stdout.flush() # write out cached messages to stdout
      quit()




###### VerbindeMitMariaDb(self) ##############################################################################
###### 2 Verbindungen zur MariaDB aufbauen
   def VerbindeMitMariaDb(self):
      
      bConn = False
      bConnLog = False
      for i in range(1,10+1):
         try:
            self.mdb = mariadb.connect( host=self.MariaIp, port=3306,user=str(self.aes.decrypt(self.MariaUserCode)), password=str(self.aes.decrypt(self.MariaPwdCode)))
            bConn = True
         except Exception as e:
            self.logging.error(f'Fehler in mariadb.connect(): {e}')

         try:
            self.mdbLog = mariadb.connect( host=self.MariaIp, port=3306,user=str(self.aes.decrypt(self.MariaUserCode)), password=str(self.aes.decrypt(self.MariaPwdCode)))
            bConnLog = True

         except Exception as e:
            self.logging.error(f'Fehler in mariadb.connect() fürs Logging: {e}')

         if bConnLog == True and bConn == True:
            break
         time.sleep(2)

      if bConnLog != True or bConn != True:
         sErr = f'Fehler in VerbindeMitMariaDb(): Conn: {bConn}, ConnLog: {bConnLog}'
         self.vScriptAbbruch(sErr)


      # ab hier Logging in die MariaDb-Tabelle t_charge_log
      self.Info2Log('mdb-connect ok')

###### CBaseApp }   ##############################################################################
