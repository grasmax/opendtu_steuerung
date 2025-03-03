# opendtu_steuerung
Mehrere Python-Scriptdateien für die Ausführung auf einem Raspberry Pi zur Konfiguration und Abfrage von Wechselrichtern mit Hilfe von OpenDTU.

Getestet unter Windows10 und raspberry pi os v11 mit mit HMS 2000 4T und [OpenDTU Hybrid](https://selbstbau-pv.de/products/opendtu-hybrid). 
Details zum RaspberryPi siehe https://github.com/grasmax/AcOnOff

Idee: Einsatz der [OpenDTU](https://github.com/tbnobody/OpenDTU) für
1. das Einstellen von Sendestärke und Abfrageintervall,
2. das Setzen des Limits für den Wechselrichter und
3. die Abfrage der Ertragswerte vom Wechselrichter.
4. Die Versorgungsspannung für die OpenDTU (+5VDC) wird nur für die Dauer der Abfragen eingeschaltet. Die Versorgungsspannung wird über ein 3-Kanal-Relaisboard auf dem RaspberryPi geschaltet.
   
* [opendtu.cfg](https://github.com/grasmax/opendtu_steuerung/blob/main/opendtu.cfg) Die Konfigurationsdatei.

* [gmbasis.py](https://github.com/grasmax/opendtu_steuerung/blob/main/gmbasis.py) Einige Basisklassen.
* [opendtu_switch_on_off.py](https://github.com/grasmax/opendtu_steuerung/blob/main/opendtu_switch_on_off.py) Versorgungsspannung per GPIO/Relaisboard ein- und ausschalten.

* [opendtu_modify_crontab.py](https://github.com/grasmax/opendtu_steuerung/blob/main/opendtu_modify_crontab.py) Minute und Stunde der Crontab-Einträge in Abhängigkeit von Sommerzeit und Sonnenuntergang modifizieren.

* [opendtu.py](https://github.com/grasmax/opendtu_steuerung/blob/main/opendtu.py) Das Script zum Konfigurieren und Abfragen.

* [opendtu_switch_on_1200.sh](https://github.com/grasmax/opendtu_steuerung/blob/main/opendtu_switch_on_1200.sh) Schaltet mit opendtu_switch_on_off.py kurz vor Mittag die Versorgungsspannung ein.
* [opendtu.sh](https://github.com/grasmax/opendtu_steuerung/blob/main/opendtu.sh) Mittags-Aufruf von opendtu.py. Schaltet auch die Versorgungspannung wieder aus.

* [opendtu_switch_on_sunset.sh](https://github.com/grasmax/opendtu_steuerung/blob/main/opendtu_switch_on_sunset.sh) Schaltet mit opendtu_switch_on_off.py kurz vor dem Sonenuntergang die Versorgungsspannung ein.
* [opendtu_sunset.sh](https://github.com/grasmax/opendtu_steuerung/blob/main/opendtu_sunset.sh) Aufruf von opendtu.py kurz vor dem Sonnenuntergang. Schaltet auch die Versorgungspannung wieder aus.

Auszug aus crontab:
```
# Das Script prueft die Sommerzeit und ermittelt den Sonnuntergang und modifiziert Minute und Stunden der nachfolgenden Eintraege
1 5 * * * sh /mnt/wd2tb/script/opendtu/opendtu_modify_crontab.sh

# Taeglich mittags um 12:02 (Winterzeit 13:02) die maximalen Ertragswerte auslesen und danach die Steuerspannung ausschalten. 14 Minuten vorher die Steuerspannung 5VDC einschalten
48 11 * * * sh /mnt/wd2tb/script/opendtu/opendtu_switch_on_1200.sh
2 12 * * * sh /mnt/wd2tb/script/opendtu/opendtu.sh

# Taeglich eine Stunde vor Sonnenuntergang die Ertragswerte auslesen. 10 Minuten vorher die Steuerspannung einschalten
38 16 * * * sh /mnt/wd2tb/script/opendtu/opendtu_switch_on_sunset.sh
48 16 * * * sh /mnt/wd2tb/script/opendtu/opendtu_sunset.sh
```

