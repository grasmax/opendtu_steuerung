# opendtu_steuerung
Mehrere Python-Scriptdateien für die Ausführung auf einem Raspberry Pi zur Konfiguration und Abfrage von Wechselrichtern mit Hilfe von OpenDTU.

Getestet unter Windows10 und raspberry pi os v11 mit mit HMS 2000 4T und [OpenDTU Hybrid](https://selbstbau-pv.de/products/opendtu-hybrid). 
Details zum RaspberryPi siehe https://github.com/grasmax/AcOnOff

Idee: Einsatz der [OpenDTU](https://github.com/tbnobody/OpenDTU) für
1. das Einstellen von Sendestärke und Abfrageintervall,
2. das Setzen des Limits für den Wechselrichter und
3. die Abfrage der Ertragswerte vom Wechselrichter.
4. Die Versorgungsspannung für die OpenDTU (+5VDC) wird nur für die Dauer der Abfragen eingeschaltet. Die Versorgungsspannung wird über ein 3-Kanal-Relaisboard auf dem RaspberryPi geschaltet.
   
