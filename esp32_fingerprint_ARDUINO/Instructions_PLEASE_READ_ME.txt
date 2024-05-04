Inštrukcie/Instruction SVK /ENG  esp32_fingerprint.ino

[SVK]

Camera - M5Stack ESP32 PSRAM Timer Kamera X  (https://rpishop.cz/kamery/4232-m5stack-esp32-psram-timer-kamera-x-ov3660.html)
FINGERPRINT - AS 608 (https://techfun.sk/en/product/as608-fingerprint-sensor/)
connected via groove connector (13 RX, 4 TX) !



súbor - home_wifi_multi.h
Nastav SSID a heslo na pripojenie WIFI

Potrebné vytvorenie API, senzor AS608 ukladá odtlačky prstov do svojej pamäte, chceme totožné ID v pamäti senzora mať aj v našej databáze. 
const char* serverAddress = "http://***************/receive_data";      // ZMEN na local ip svoju.., change to your LOCAL IP 
const char* serverAddressPython = "http://************/send_fingerprint_data"; // ZMEN na local ip svoju.., change to your LOCAL IP 


riadky 400 - nastavenie parametrov kamery, rozlíšenie atd. 


void loop()
je tam delay nastavený 5 sekund, chceli sme vytvoriť iba jeden kod ktory by obsluhoval aj registráciu aj realne prihlasenie pomocou 1. kodu.
V praxi vytvorenie 2 skriptov zvlášť. Registrácia a real time prihlasenie bez delayu ( čo najrýchlejšia detekcia pre fingerprint)
IF () logika - REGISTRACIA odtlačku prsta
ELSE - realne prihlasenie, overenie odtlačku prsta.

po nahratí kodu do kamery
vytvorenie URL / IP  :: NAPR:::: http://192.168.1.33/mjpeg/1

ZDIELANIE MJPEG STREAMU

TATO URL ADRESA BUDE NUTNA NA DALSIE SPRACOVANIE V PYTHON SKRIPTOCH!!!!!!


[ENG]


Camera - M5Stack ESP32 PSRAM Timer Camera X (https://rpishop.cz/kamery/4232-m5stack-esp32-psram-timer-kamera-x-ov3660.html)
FINGERPRINT - AS 608 (https://techfun.sk/en/product/as608-fingerprint-sensor/)
connected via groove connector (13 RX, 4 TX) !



file - home_wifi_multi.h
Set SSID and password for WIFI connection

Necessary API creation, the AS608 sensor stores fingerprints in its memory, we want to have the same ID in the sensor's memory and in our database.
35    const char* serverAddress = "http://****************/receive_data"; // CHANGE to your local ip.., change to your LOCAL IP
38    const char* serverAddressPython = "http://************/send_fingerprint_data"; // CHANGE to your local ip.., change to your LOCAL IP


lines 400 - setting camera parameters, resolution, etc.


void loop()
there is a delay set to 5 seconds, we wanted to create only one code that would handle both registration and real login attendance using only one script.
In practice, the creation of 2 scripts separately. Registration and real time login without delay (fastest possible fingerprint detection)
IF () logic - FINGERPRINT REGISTRATION
ELSE - real login, fingerprint verification.

after uploading the code to the camera
creation of URL / IP :: FOR EXAMPLE:::: http://192.168.1.33/mjpeg/1

MJPEG STREAM SHARING

THIS URL WILL BE REQUIRED FOR FURTHER PROCESSING IN PYTHON SCRIPTS!!!!!!