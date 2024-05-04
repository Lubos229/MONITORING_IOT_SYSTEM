/*

 Jedná sa o jednoduchý MJPEG streamovací webový server implementovaný pre moduly ESP32-CAM TEDA PRE NAS M5STACK TIMER CAMERA X .
   môže podporovať až 10 súčasne pripojených streamovacích klientov. 
  Simultánne streamovanie je implementované s úlohami FreeRTOS tasky v podstate


*/

//
#define APP_CPU 1
#define PRO_CPU 0

#include "M5TimerCAM.h"
#include "OV2640.h"
#include <WebServer.h>
#include <WiFiClient.h>
#include <WiFi.h>
#include <Adafruit_Fingerprint.h>
#include <SoftwareSerial.h>
#include <HTTPClient.h>



#define CAMERA_MODEL_M5STACK_PSRAM   // ukladame do toho ..

#define FINGERPRINT_RX 13            // fingerprint vysielanie, prijimanie
#define FINGERPRINT_TX 4            

SoftwareSerial mySerial(FINGERPRINT_RX, FINGERPRINT_TX);

Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);


const char* serverAddress = "http://***************/receive_data";      // ZMEN na local ip svoju.., change to your LOCAL IP 


const char* serverAddressPython = "http://************/send_fingerprint_data"; // ZMEN na local ip svoju.., change to your LOCAL IP 

String hlavna;
#include "camera_pins.h"

uint8_t id;

// NASTAV SI V TOMTO SUBORE WIFI SSID A HESLO / SET SSID AND PASSWORD..
#include "home_wifi_multi.h"

OV2640 cam;
// mame 33... ale pouzivame tuto kniznicu  

WebServer server(80);  // web server 80 port



String receivedIdFinger;        // praca s API 

// ===== rtos task handles =========================
// Streamovanie je implementované s 3 taskami:
TaskHandle_t tMjpeg;   // spracováva pripojenia klientov k webovému serveru
TaskHandle_t tCam;     // spravuje získavanie rámov obrázkov z fotoaparátu a ich lokálne ukladanie
TaskHandle_t tStream;  // streamovanie snímok všetkým pripojeným klientom

// frameSync semaphore sa používa na zabránenie vyrovnávacej pamäte streamovania, keď je nahradená ďalšou snímkou
SemaphoreHandle_t frameSync = NULL;

// Fronta ukladá aktuálne pripojených klientov, ktorým streamujeme
QueueHandle_t streamingClients;

// FPS CO NAJVIAC CHCEME
const int FPS = 50;            // co najviac :D

// Požiadavky webového klienta budeme spracovávať každých 200
const int WSINTERVAL = 200;


// ======== Server Connection Handler Task ==========================
void mjpegCB(void* pvParameters) {
  TickType_t xLastWakeTime;
  const TickType_t xFrequency = pdMS_TO_TICKS(WSINTERVAL);

  // Vytvorenie semaforu synchronizácie snímok a jeho inicializácia
  frameSync = xSemaphoreCreateBinary();
  xSemaphoreGive( frameSync );

  // Vytvorenie frontu na sledovanie všetkých pripojených klientov
  streamingClients = xQueueCreate( 10, sizeof(WiFiClient*) );

  //=== setup section  ==================

  //  Vytvorenie úlohy RTOS na uchopenie snímok z fotoaparátu
  xTaskCreatePinnedToCore(
    camCB,        // callback
    "cam",        // name
    4096,         // stack size
    NULL,         // parameters
    2,            // priority
    &tCam,        // RTOS task handle
    APP_CPU);     // core

  //  Vytvára sa úloha na odoslanie streamu všetkým pripojeným klientom
  xTaskCreatePinnedToCore(
    streamCB,
    "strmCB",
    4 * 1024,
    NULL, //(void*) handler,
    2,
    &tStream,
    APP_CPU);

  //  Registrácia postupov obsluhy webového servera
  server.on("/mjpeg/1", HTTP_GET, handleJPGSstream);
  server.on("/jpg", HTTP_GET, handleJPG);
  server.onNotFound(handleNotFound);

  //  Spustenie webového servera
  server.begin();

  //=== loop() section  ===================
  xLastWakeTime = xTaskGetTickCount();
  for (;;) {
    server.handleClient();

    //  Po každej požiadavke klienta servera necháme bežať ďalšie úlohy a potom ich pozastavíme
    taskYIELD();
    vTaskDelayUntil(&xLastWakeTime, xFrequency);
  }
}


// premmenne dolezite, co posielame hlavne
volatile size_t camSize;    // veľkosť aktuálneho frane, byte
volatile char* camBuf;      // pointer na aktualny frame


// ==== Úloha RTOS na uchopenie snímok z kamery =========================
void camCB(void* pvParameters) {

  TickType_t xLastWakeTime;

  //  Interval chodu spojený s aktuálne požadovanou snímkovou frekvenciou
  const TickType_t xFrequency = pdMS_TO_TICKS(1000 / FPS);

  // Mutex pre kritickú časť prepínania aktívnych snímok
  portMUX_TYPE xSemaphore = portMUX_INITIALIZER_UNLOCKED;

  //  Ukazovatele na 2 snímky, ich príslušné veľkosti a index aktuálnej snímky
  char* fbs[2] = { NULL, NULL };
  size_t fSize[2] = { 0, 0 };
  int ifb = 0;

  //=== loop() section  ===================
  xLastWakeTime = xTaskGetTickCount();

  for (;;) {

    //  Ziskat frame z kamery a spytat sa na velkost
    cam.run();
    size_t s = cam.getSize();

  

    //  Ak je veľkosť rámca väčšia, ako sme predtým pridelili, ziadame o 125 % aktuálneho priestoru pre frame
    if (s > fSize[ifb]) {
      fSize[ifb] = s * 4 / 3;
      fbs[ifb] = allocateMemory(fbs[ifb], fSize[ifb]);
    }

    //  Vlozeniem skorpiropvanie aktuálny framu do lokálnej vyrovnávacej pamäte
    char* b = (char*) cam.getfb();
    memcpy(fbs[ifb], b, s);

    // Nechaj bežať ostatné úlohy a počkaj do konca aktuálneho intervalu snímkovej frekvencie
    taskYIELD();
    vTaskDelayUntil(&xLastWakeTime, xFrequency);

    //  Snímky prepínať iba vtedy, ak sa do klienta neprenáša žiadny frame
    // Počkaj  na semafor, kým sa nedokončí operácia klienta
    xSemaphoreTake( frameSync, portMAX_DELAY );

    //  Počas prepínania aktuálneho framu nedovoľiť prerušenia
    portENTER_CRITICAL(&xSemaphore);
    camBuf = fbs[ifb];
    camSize = s;
    ifb++;
    ifb &= 1;  
    portEXIT_CRITICAL(&xSemaphore);

    //  čakanie na frame nech vie ze je pripravena 
    xSemaphoreGive( frameSync );

    //   potrebné iba raz: úlohe streamovania vedieť, že máme aspoň jeden rámec
    //  a moze začať posielať frame klientom, ak existujú
    xTaskNotifyGive( tStream );

    //  Ihneď nechajte bežať iné (streamingové) úlohy
    taskYIELD();

    //  Ak sa úloha streamovania sama pozastavila (žiadni aktívni klienti na streamovanie)
    //  nie je potrebné zachytávať snímky z fotoaparátu. Trochu šťavy si môžeme odložiť pozastavením úloh
    if ( eTaskGetState( tStream ) == eSuspended ) {
      vTaskSuspend(NULL);  // nulla - pozastaviť sa
    }
  }
}


// ====Alokátor pamäte, ktorý využíva výhody PSRAM, ak je prítomný =======================
char* allocateMemory(char* aPtr, size_t aSize) {

  //  eďže súčasná vyrovnávacia pamäť je príliš malá, uvoľniť ju
  if (aPtr != NULL) free(aPtr);


  size_t freeHeap = ESP.getFreeHeap();
  char* ptr = NULL;

  // Ak je požadovaná pamäť väčšia ako 2/3 aktuálne voľnej hromady, okamžite skús PSRAM
  if ( aSize > freeHeap * 2 / 3 ) {
    if ( psramFound() && ESP.getFreePsram() > aSize ) {
      ptr = (char*) ps_malloc(aSize);
    }
  }
  else {
    // Dosť voľnej hromady - skúsme alokovať rýchlu pamäť RAM ako vyrovnávaciu pamäťr
    ptr = (char*) malloc(aSize);

    //  Ak alokácia na hromade zlyhala, dajme PSRAM ešte jednu šancu::
    if ( ptr == NULL && psramFound() && ESP.getFreePsram() > aSize) {
      ptr = (char*) ps_malloc(aSize);
    }
  }

  // A nakoniec, ak je ukazovateľ pamäte NULL, nemohli sme alokovať žiadnu pamäť, a to je koncový stav.
  if (ptr == NULL) {
    ESP.restart();
  }
  return ptr;
}


// ==== STREAMING ======================================================
const char HEADER[] = "HTTP/1.1 200 OK\r\n" \
                      "Access-Control-Allow-Origin: *\r\n" \
                      "Content-Type: multipart/x-mixed-replace; boundary=123456789000000000000987654321\r\n";
const char BOUNDARY[] = "\r\n--123456789000000000000987654321\r\n";
const char CTNTTYPE[] = "Content-Type: image/jpeg\r\nContent-Length: ";
const int hdrLen = strlen(HEADER);
const int bdrLen = strlen(BOUNDARY);
const int cntLen = strlen(CTNTTYPE);


//Spracovanie požiadavky na pripojenie od klientov 
void handleJPGSstream(void)
{
  //  Tento limit je predvolený pre WiFi pripojenia IBA 10 klientov
  if ( !uxQueueSpacesAvailable(streamingClients) ) return;


  // Vytvorenie nového objektu klienta WiFi na sledovanie tohto objektu
  WiFiClient* client = new WiFiClient();
  *client = server.client();

  // Okamžite pošlanie klientovi hlavičku
  client->write(HEADER, hdrLen);
  client->write(BOUNDARY, bdrLen);

  //  Odoslanie klienta do frontu na streamovaniee
  xQueueSend(streamingClients, (void *) &client, 0);

  // Prebudenie úloh streamovania, ak boli predtým pozastavené:
  if ( eTaskGetState( tCam ) == eSuspended ) vTaskResume( tCam );
  if ( eTaskGetState( tStream ) == eSuspended ) vTaskResume( tStream );
}


// Skutočné streamovanie obsahu všetkým pripojeným klientom 
void streamCB(void * pvParameters) {
  char buf[16];
  TickType_t xLastWakeTime;
  TickType_t xFrequency;

  //   Počkaj, kým sa nezachytí prvá snímka a bude čo odoslať klientom
  ulTaskNotifyTake( pdTRUE,          
                    portMAX_DELAY ); 

  xLastWakeTime = xTaskGetTickCount();
  for (;;) {
    // Predvolený predpoklad,  podľa FPS
    xFrequency = pdMS_TO_TICKS(1000 / FPS);

   // Posielaj čokoľvek, len ak sa niekto pozerá

    UBaseType_t activeClients = uxQueueMessagesWaiting(streamingClients);
    if ( activeClients ) {
      // Prispôsobte periódu počtu pripojených klientov
      xFrequency /= activeClients;

      //  Keďže všetkým posielame rovnaký frame
      //  vymaz klienta z čela na začiatku myslené
      WiFiClient *client;
      xQueueReceive (streamingClients, (void*) &client, 0);

      //   Skontrolujte, či je tento klient stále pripojený.
      if (!client->connected()) {
        //  vymaž referenciu klienta, ak sa odpojil a už ho nevracaj do poradia.
        delete client;
      }
      else {

        //  Ide o aktívne pripojeného klienta. vezmu  semafor, zabrániť zmenám framu počas podávania tohto framu
  
        xSemaphoreTake( frameSync, portMAX_DELAY );

        client->write(CTNTTYPE, cntLen);
        sprintf(buf, "%d\r\n\r\n", camSize);
        client->write(buf, strlen(buf));
        client->write((char*) camBuf, (size_t)camSize);
        client->write(BOUNDARY, bdrLen);

        // Keďže tento klient je stále pripojený, presun ho na koniec fronty na ďalšie spracovanie
        xQueueSend(streamingClients, (void *) &client, 0);

        //  Frame bol doručený. Uvoľnite semafor a nechajte ostatné úlohy bežať.
        //  Ak je pripravený switch snímok, stane sa to teraz medzi snímkami
        xSemaphoreGive( frameSync );
        taskYIELD();
      }
    }
    else {
      //Keďže neexistujú žiadni pripojení klienti, nechceme minat batériou
      vTaskSuspend(NULL);
    }
    // Nechaj ostatné úlohy bežať po obsluhe každého klienta
    taskYIELD();
    vTaskDelayUntil(&xLastWakeTime, xFrequency);
  }
}


// ANO POSIELAME HTTP A JE TAM JPEG FILE IMAGE FILE 
const char JHEADER[] = "HTTP/1.1 200 OK\r\n" \
                       "Content-disposition: inline; filename=capture.jpg\r\n" \
                       "Content-type: image/jpeg\r\n\r\n";
const int jhdLen = strlen(JHEADER);

// ====Podávanie  obrázku JPEG=============================================
void handleJPG(void)
{
  WiFiClient client = server.client();

  if (!client.connected()) return;
  cam.run();
  client.write(JHEADER, jhdLen);
  client.write((char*)cam.getfb(), cam.getSize());
}


// ==== Hpracovať neplatné žiadosti o adresy URL ============================================
void handleNotFound()
{
  String message = "Server is running!\n\n";
  message += "URI: ";
  message += server.uri();
  message += "\nMethod: ";
  message += (server.method() == HTTP_GET) ? "GET" : "POST";
  message += "\nArguments: ";
  message += server.args();
  message += "\n";
  server.send(200, "text / plain", message);
}



// ==== SETUP method ==================================================================
void setup()
{
   Serial.begin(115200);
  TimerCAM.begin(true);
  mySerial.begin(57600);

  // rýchlosť prenosu dát pre sériový port snímača
  finger.begin(57600);

  pinMode(2, OUTPUT);
  digitalWrite(2, HIGH);
  // 
  Serial.begin(115200);
  delay(1000); // počkaj sekundu, aby ste umožnili sériové pripojeniet
   // Spustite časovač hlbokého spánku
  //esp_sleep_enable_timer_wakeup(DEEP_SLEEP_TIME_US);


  camera_config_t config;


  


  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;

  Serial.println(F("Reading sensor parameters"));
  finger.getParameters();
  Serial.print(F("Status: 0x")); Serial.println(finger.status_reg, HEX);


  
    config.ledc_channel = LEDC_CHANNEL_0;
    config.ledc_timer = LEDC_TIMER_0;
    config.pin_d0 = Y2_GPIO_NUM;
    config.pin_d1 = Y3_GPIO_NUM;
    config.pin_d2 = Y4_GPIO_NUM;
    config.pin_d3 = Y5_GPIO_NUM;
    config.pin_d4 = Y6_GPIO_NUM;
    config.pin_d5 = Y7_GPIO_NUM;
    config.pin_d6 = Y8_GPIO_NUM;
    config.pin_d7 = Y9_GPIO_NUM;
    config.pin_xclk = XCLK_GPIO_NUM;
    config.pin_pclk = PCLK_GPIO_NUM;
    config.pin_vsync = VSYNC_GPIO_NUM;
    config.pin_href = HREF_GPIO_NUM;
    config.pin_sscb_sda = SIOD_GPIO_NUM;
    config.pin_sscb_scl = SIOC_GPIO_NUM;
    config.pin_pwdn = PWDN_GPIO_NUM;
    config.pin_reset = RESET_GPIO_NUM;
    config.xclk_freq_hz = 20000000;
    config.pixel_format = PIXFORMAT_JPEG;
    config.frame_size = FRAMESIZE_SVGA; // resolution  800x600
    config.jpeg_quality = 5;
    config.fb_count = 2;
 


#if defined(CAMERA_MODEL_ESP_EYE)
  pinMode(13, INPUT_PULLUP);
  pinMode(14, INPUT_PULLUP);
#endif

  if (cam.init(config) != ESP_OK) {
    Serial.println("Error initializing the camera");
    delay(10000);
    ESP.restart();
  }

sensor_t *s = esp_camera_sensor_get();
    // farby sú trochu sýte
    s->set_vflip(s, 1);        // pretoc ich
    s->set_brightness(s, 1);   // trochu zvýšiť jast
    s->set_saturation(s, -2);  // znížiť saturáciu

    // rozbaľovacia veľkosť snímky pre vyššiu počiatočnú snímkovú frekvenciu
  //  s->set_framesize(s, FRAMESIZE_QVGA);




  //  Nakonfiguruj a pripojsa k WiFi
  IPAddress ip;

  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID1, PWD1);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(F("."));
  }
  ip = WiFi.localIP();
  Serial.println(F("WiFi connected"));
  Serial.println("");
  Serial.print("Stream Link: http://");
  Serial.print(ip);
  Serial.println("/mjpeg/1");


  // Začni s mainstreamingom úlohy RTOS
  xTaskCreatePinnedToCore(
    mjpegCB,
    "mjpeg",
    4 * 1024,
    NULL,
    2,
    &tMjpeg,
    APP_CPU);
}

void loop() {
  
  

  vTaskDelay(5000);

  digitalWrite(2, HIGH);
  
  Serial.println("HEEEEEEEEEEEEJ!");
  HTTPClient http;

  http.begin(serverAddressPython);
  int httpResponseCode = http.GET();

  if (httpResponseCode == 200) {
    Serial.printf("HTTP Response code: %d\n", httpResponseCode);
    String fingerprintData = http.getString();
    Serial.println("Fingerprint data received: " + fingerprintData);
    // Spracuj prijaté údaje o odtlačkoch prstov a extrahujte ID
    id = fingerprintData.toInt();  // PREMENA the String na integer

    hlavna="Prilozte prst na senzor#";
    hlavnasendFingerprintData();

    while (!getFingerprintEnroll());
    sendFingerprintData();
    delay(1000);
    http.end();
   

    //delay(5000); // Sleep after 5 seconds of inactivity

    // Enter deep sleep
    // esp_deep_sleep_start();
  } else {
    
    Serial.printf("HTTP Request failed. Error code: %d. Details: %s\n", httpResponseCode, http.errorToString(httpResponseCode).c_str());
    
    delay(200);
    
    getFingerprintID();
    delay(200);

 }
}


void sendFingerprintData() {
  String fingerprintData = "ID=" + String(id) + "&EnrolledID=" + String(finger.fingerID);

  // Vytvorenie objektu HTTP
  HTTPClient http;

  // Urobte požiadavku POST na server
  http.begin(serverAddress);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  int httpResponseCode = http.POST("data=" + fingerprintData);
  http.end();
  // úspešnosť žiadosti
  if (httpResponseCode > 0) {
    Serial.printf("HTTP Response code: %d\n", httpResponseCode);
    Serial.println(http.getString());
  } else {
    Serial.printf("HTTP Request failed. Error code: %d. Details: %s\n", httpResponseCode, http.errorToString(httpResponseCode).c_str());
  }

  //Koniec requestu
  http.end();
  delay(500);

  //delay(1000); // Adjust delay based on your requirements
}


void hlavnasendFingerprintData() {
  String fingerprintData = hlavna;

  // Vytvorenie objektu HTTP
  HTTPClient http;

  // Urob post poziadavku
  http.begin(serverAddress);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  int httpResponseCode = http.POST("data=" + fingerprintData);

  // uspešna ziadost
  if (httpResponseCode > 0) {
    Serial.printf("HTTP Response code: %d\n", httpResponseCode);
    Serial.println(http.getString());
  } else {
    Serial.printf("HTTP Request failed. Error code: %d. Details: %s\n", httpResponseCode, http.errorToString(httpResponseCode).c_str());
  }

  // koniec ziadosti
  http.end();

  delay(5); // pridaj menši dealy
}




uint8_t getFingerprintEnroll() {

  int p = -1;
  hlavna="Platný prst na registráciu #";
  hlavnasendFingerprintData();
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    switch (p) {
    case FINGERPRINT_OK:
      Serial.println("Image taken");
      hlavna="Image zhotoveny";

      hlavnasendFingerprintData();
      break;
    case FINGERPRINT_NOFINGER:
      Serial.print(".");
      break;
    case FINGERPRINT_PACKETRECIEVEERR:
      Serial.println("Communication error");
      hlavna="Communication error";
      hlavnasendFingerprintData();
      break;
    case FINGERPRINT_IMAGEFAIL:
      Serial.println("Imaging error");
      break;
    default:
      Serial.println("Unknown error");
      break;
    }
  }



  p = finger.image2Tz(1);
  switch (p) {
    case FINGERPRINT_OK:
      Serial.println("Image converted");
      break;
    case FINGERPRINT_IMAGEMESS:
      Serial.println("Image too messy");
      return p;
    case FINGERPRINT_PACKETRECIEVEERR:
      Serial.println("Communication error");
      return p;
    case FINGERPRINT_FEATUREFAIL:
      Serial.println("Could not find fingerprint features");
      return p;
    case FINGERPRINT_INVALIDIMAGE:
      Serial.println("Could not find fingerprint features");
      return p;
    default:
      Serial.println("Unknown error");
      return p;
  }

  Serial.println("Remove finger");
  hlavna="Odstrante prst";
  hlavnasendFingerprintData();
  delay(2000);
  p = 0;
  while (p != FINGERPRINT_NOFINGER) {
    p = finger.getImage();
  }
  Serial.print("ID "); Serial.println(id);
  p = -1;
  Serial.println("Place same finger again");
  hlavna="Znova prilozte ten isty prst";
  hlavnasendFingerprintData();
  while (p != FINGERPRINT_OK) {
    p = finger.getImage();
    switch (p) {
    case FINGERPRINT_OK:
      Serial.println("Image taken");
      hlavna="Image spracovany";
      hlavnasendFingerprintData();
      break;
    case FINGERPRINT_NOFINGER:
      Serial.print(".");
      break;
    case FINGERPRINT_PACKETRECIEVEERR:
      Serial.println("Communication error");
      break;
    case FINGERPRINT_IMAGEFAIL:
      Serial.println("Imaging error");
      break;
    default:
      Serial.println("Unknown error");
      break;
    }
  }



  p = finger.image2Tz(2);
  switch (p) {
    case FINGERPRINT_OK:

      break;
    case FINGERPRINT_IMAGEMESS:
      Serial.println("Image too messy");
      return p;
    case FINGERPRINT_PACKETRECIEVEERR:
      Serial.println("Communication error");
      return p;
    case FINGERPRINT_FEATUREFAIL:
      Serial.println("Could not find fingerprint features");
      return p;
    case FINGERPRINT_INVALIDIMAGE:
      Serial.println("Could not find fingerprint features");
      return p;
    default:
      Serial.println("Unknown error");
      return p;
  }


  Serial.print("Creating model for #");  Serial.println(id);

  p = finger.createModel();
  if (p == FINGERPRINT_OK) {
  } else if (p == FINGERPRINT_PACKETRECIEVEERR) {
    Serial.println("Communication error");
    return p;
  } else if (p == FINGERPRINT_ENROLLMISMATCH) {
    Serial.println("Fingerprints did not match");
    hlavna="Odtlacky prstov sa nezhoduju";
    hlavnasendFingerprintData();
    return p;
  } else {
    Serial.println("Unknown error");
    return p;
  }
  Serial.print("ID "); Serial.println(id);
  p = finger.storeModel(id);



Serial.print("Store model result: "); Serial.println(p);
hlavna="Ulozene : ";
hlavnasendFingerprintData();


  Serial.print("ID "); Serial.println(id);
  p = finger.storeModel(id);
  if (p == FINGERPRINT_OK) {
    Serial.println("Stored!");
  } else if (p == FINGERPRINT_PACKETRECIEVEERR) {
    Serial.println("Communication error");
    return p;
  } else if (p == FINGERPRINT_BADLOCATION) {
    Serial.println("Could not store in that location");
    return p;
  } else if (p == FINGERPRINT_FLASHERR) {
    Serial.println("Error writing to flash");
    return p;
  } else {
    Serial.println("Unknown error");
    return p;
  }

  return true;
}


uint8_t getFingerprintID() {
  uint8_t p = finger.getImage();
  switch (p) {
    case FINGERPRINT_OK:
      Serial.println("Image taken");
      break;
    case FINGERPRINT_NOFINGER:
      Serial.println("No finger detected");
      return p;
    case FINGERPRINT_PACKETRECIEVEERR:
      Serial.println("Communication error");
      return p;
    case FINGERPRINT_IMAGEFAIL:
      Serial.println("Imaging error");
      return p;
    default:
      Serial.println("Unknown error");
      return p;
  }



  p = finger.image2Tz();
  switch (p) {
    case FINGERPRINT_OK:
      Serial.println("Image converted");
      break;
    case FINGERPRINT_IMAGEMESS:
      Serial.println("Image too messy");
      return p;
    case FINGERPRINT_PACKETRECIEVEERR:
      Serial.println("Communication error");
      return p;
    case FINGERPRINT_FEATUREFAIL:
      Serial.println("Could not find fingerprint features");
      return p;
    case FINGERPRINT_INVALIDIMAGE:
      Serial.println("Could not find fingerprint features");
      return p;
    default:
      Serial.println("Unknown error");
      return p;
  }


  p = finger.fingerSearch();
  if (p == FINGERPRINT_OK) {
    Serial.println("Found a print match!");
  } else if (p == FINGERPRINT_PACKETRECIEVEERR) {
    Serial.println("Communication error");
    return p;
  } else if (p == FINGERPRINT_NOTFOUND) {
    Serial.println("Did not find a match");
    return p;
  } else {
    Serial.println("Unknown error");
    return p;
  }


  Serial.println("Found ID #");
Serial.println(finger.fingerID);


  String fingerIDString = String(finger.fingerID);
  String fingerConfidence = String(finger.confidence);
// pouzitie pomocneho slova na definovanie v python skripte, pomoze rozoznat premenne..
  hlavna = "toto" + fingerIDString;
  Serial.println("IDE HLAVNA");
  hlavnasendFingerprintData();
  Serial.println(hlavna);

// pouzitie pomocneho slova na definovanie v python skripte, pomoze rozoznat premenne..
  hlavna = "compare" + fingerConfidence;
  hlavnasendFingerprintData();
  Serial.println(" with confidence of"); Serial.println(finger.confidence);
  //hlavna=finger.confidence;
  hlavnasendFingerprintData();

  return finger.fingerID;
}


int getFingerprintIDez() {
  uint8_t p = finger.getImage();
  if (p != FINGERPRINT_OK)  return -1;

  p = finger.image2Tz();
  if (p != FINGERPRINT_OK)  return -1;

  p = finger.fingerFastSearch();
  if (p != FINGERPRINT_OK)  return -1;


  Serial.print("Found ID #"); Serial.print(finger.fingerID);
  Serial.print(" with confidence of "); Serial.println(finger.confidence);
  return finger.fingerID;
}
