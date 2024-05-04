Inštrukcie/Instructions SVK /ENG  monitoring_environment.ino

[SK]

Vytvorenie WIFI, MJPEG streamu, návod:
home_wifi_multi.h TREBA SSID, heslo
esp32_fingerprint/Insctruction.txt

Camera - M5Stack ESP32 PSRAM Timer Kamera X  (https://rpishop.cz/kamery/4232-m5stack-esp32-psram-timer-kamera-x-ov3660.html)
FINGERPRINT - AS 608 (https://techfun.sk/en/product/as608-fingerprint-sensor/)
PORTHUB - https://rpishop.cz/bloky/3307-m5stack-grove-io-pbhub-se-6-porty-mega328.html
BZUCIAK - https://rpishop.cz/moduly/2125-grove-bzucak.html
PIR , POHYBOVY SENZOR - https://rpishop.cz/bloky/2771-m5stack-pir-pohybove-cidlo-as312.html
prepojenie GROOVE KONEKTOR

riadky 7-11
Google drive nastavenia, nazvy priečinku, suboru, treba vytvorit API kluc citaj subor google_drive.txt


35   define PIN_PORTHUB_MODULE 13  TREBA NASTAVIT NA PIN 13, citaj datasheet : https://docs.m5stack.com/en/unit/timercam_x?ref=langship

riadky 42- 47
NASTAVENIE : Gmail pre odosielanie e-mailov, povoliť prístup menej zabezpečeným aplikáciám vo svojom účte Gmail. Následne vygenerovat heslo pre aplikáciu, ktoré sme použili na autentifikáciu pri pripájaní k serveru SMTP.

sender_password "******** TOTO JE TO HESLO 



uint8_t HUB_ADDR[6] = { HUB1_ADDR, HUB2_ADDR, HUB3_ADDR,
                        HUB4_ADDR, HUB5_ADDR, HUB6_ADDR };

HUB MA 6 PORTOV, POZOR KDE ZAPAJATE PIR, BZUCIAK 

#define PIR_SENSOR_CHANNEL HUB2_ADDR  // Zadajte správny kanál pre PIR senzor na PortHub,
#define BUZZER_CHANNEL HUB1_ADDR      // Zadajte správny kanál pre BZUCIAK senzor na PortHub , 


PO nahratí scriptu monitoring_environment.ino, PIR MOTION SENSOR ZACHYTI POHYB, BZUCIAK ZAPIPA, KAMERA SPRAVI FOTKU UPLOADNE NA GOOGLE DRIVE A PRIJDE MAILOVE UPOZORNENIE

-------------------------------------------------------------------------------------------------------------------------------------------------------------------

[ENG] 
Creating a WIFI, MJPEG stream, instructions:
home_wifi_multi.h NEED SSID, password
esp32_fingerprint/Instruction.txt

Camera - M5Stack ESP32 PSRAM Timer Camera X (https://rpishop.cz/kamery/4232-m5stack-esp32-psram-timer-kamera-x-ov3660.html)
FINGER - AS 608 (https://techfun.sk/sk/produkt/as608-fingerprint sensor/)
PORTHUB - https://rpishop.cz/bloky/3307-m5stack-grove-io-pbhub-se-6-porty-mega328.html
BZUCIAK - https://rpishop.cz/moduly/2125-grove-bzucak.html
PIR, MOTION SENSOR - https://rpishop.cz/bloky/2771-m5stack-pir-pohybove-cidlo-as312.html
connection GROOVE CONNECTOR

lines 7-11
Google drive settings, folder, file names, you need to create an API key, read the file google_drive.txt


35 define PIN_PORTHUB_MODULE 13 MUST BE SET TO PIN 13, read datasheet: https://docs.m5stack.com/en/unit/timercam_x?ref=langship

lines 42-47
SETUP : Gmail for email verification, allow access to less secure applications in your Gmail account. Then generate the password for the application that we used for authentication when connecting to the SMTP server.

   Sender_password "******** THIS IS THE PASSWORD



uint8_t HUB_ADDR[6] = { HUB1_ADDR, HUB2_ADDR, HUB3_ADDR,
                          HUB4_ADDR, HUB5_ADDR, HUB6_ADDR };

THE HUB HAS 6 PORTS, BEWARE OF WHERE YOU PLUG IN THE PIR, BUZZER

#define PIR_SENSOR_CHANNEL HUB2_ADDR // Specify the correct channel for the PIR sensor on the PortHub,
#define BUZZER_CHANNEL HUB1_ADDR // Specify the correct channel for the BUZZER sensor on the PortHub,


AFTER LOADING THE SCRIPT monitoring_environment.ino, THE PIR MOTION SENSOR DETECTS MOTION, THE BUZZER GOES OFF, THE CAMERA TAKES A PHOTO RECORDED ON GOOGLE DRIVE AND AN EMAIL NOTIFICATION COMES

