// PROSIM PRECITAJ NAJPRV INSTRUKCIE, PLEASE READ INSCRUCTION FIRST ........
// 


// PRE toto čitaj prosim google_drive.txt
// FOR THIS google Drive read please google_drive.txt
const char* driveScriptDomain = "script.google.com";
String driveFoldername = "&myFoldername=*****************";      // PRIECINOK, FOLDER
String driveFilename = "&myFilename=******************";        // NAZOV SUBORU, file name
String driveImage = "&myFile=";
String driveScriptPath = "/macros/s/***********************/exec";     // PRIDANIE  API SVOJHO KLUCA, NUTNE VYTVORIT GOOGLE APPS PROJEKT  A NAHRAT  -- google_drive.txt 

String SendCapturedImageToGoogleDrive(const char* image, size_t imageSize);

#define APP_CPU 1
#define PRO_CPU 0
//#include <M5Stack.h>
#include "OV2640.h"
#include "WiFi.h"
#include <WebServer.h>
#include <WiFiClient.h>

#include <WiFi.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"




#include <WiFiClientSecure.h>
#include "Base64.h"



#define PIN_PORTHUB_MODULE 13
#define CAMERA_MODEL_M5STACK_PSRAM
#include "porthub.h"
#include <WiFi.h>
#include <ESP_Mail_Client.h>
//#define WIFI_SSID ""
//#define WIFI_PASSWORD "2"
#define SMTP_server "smt.gmail.com"
#define SMTP_Port 465
#define sender_email "*************"    // Odosielatel email, sender email 
#define sender_password "********"  // heslo, 
#define Recipient_email "**********"  // E-mail príjemcu,  Recipient_email
#define Recipient_name ""
SMTPSession smtp;

uint8_t HUB_ADDR[6] = { HUB1_ADDR, HUB2_ADDR, HUB3_ADDR,
                        HUB4_ADDR, HUB5_ADDR, HUB6_ADDR };



#define PIR_SENSOR_CHANNEL HUB2_ADDR  // Zadajte správny kanál pre PIR senzor na PortHub, Specify the correct channel for the PIR sensor on PortHub
#define BUZZER_CHANNEL HUB1_ADDR      // Zadajte správny kanál pre BZUCIAK senzor na PortHub , Specify the correct channel for the buzzer on PortHub
PortHub porthub;
#include <Wire.h>

#include "camera_pins.h"


//#define WIFI_SSID ""
//#define WIFI_PASSWORD ""
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



void setup() {
  Serial.begin(115200);

  porthub.begin();
 
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);  // disable   detector
 
  Serial.setDebugOutput(true);
  Serial.println();
  pinMode(2, OUTPUT);
  digitalWrite(2, HIGH);



  delay(1000);  


  camera_config_t config;

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
  config.frame_size = FRAMESIZE_SVGA;  // Set the resolution to 800x600
  config.jpeg_quality = 14;
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

  sensor_t* s = esp_camera_sensor_get();

  s->set_vflip(s, 1);        
  s->set_brightness(s, 1);   
  s->set_saturation(s, -2);  


  IPAddress ip;

  WiFi.mode(WIFI_STA);
  WiFi.begin(SSID1, PWD1);
  Serial.print("Connecting to WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(F("."));
  }
  ip = WiFi.localIP();
  Serial.println(F("WiFi connected"));
  Serial.println("");
  Serial.print("Stream Link: http://");
  Serial.print(ip);
  Serial.println("/mjpeg/1");



  xTaskCreatePinnedToCore(
    mjpegCB,
    "mjpeg",
    4 * 1024,
    NULL,
    2,
    &tMjpeg,
    APP_CPU);

}
// kódovanie niektorých špeciálnych znakov v reťazci (napríklad medzery, symboly atď.), ktoré by mohli spôsobiť problémy pri odosielaní cez URL.
String urlencode(String str) {
  const char* msg = str.c_str();
  const char* hex = "0123456789ABCDEF";
  String encodedMsg = "";
  while (*msg != '\0') {
    if (('a' <= *msg && *msg <= 'z') || ('A' <= *msg && *msg <= 'Z') || ('0' <= *msg && *msg <= '9') || *msg == '-' || *msg == '_' || *msg == '.' || *msg == '~') {
      encodedMsg += *msg;
    } else {
      encodedMsg += '%';
      encodedMsg += hex[(unsigned char)*msg >> 4];
      encodedMsg += hex[*msg & 0xf];
    }
    msg++;
  }
  return encodedMsg;
}

void sendEmail() {

  ESP_Mail_Session session;

  session.server.host_name = SMTP_server;

  session.server.port = SMTP_Port;

  session.login.email = sender_email;

  session.login.password = sender_password;

  session.login.user_domain = "";

  SMTP_Message message;
  // NASTAVENIE SPRAVY
  message.sender.name = "*******";   // ODKOHO 
  message.sender.email = sender_email;
  message.subject = "*********";   // PREDMET , SUBJECT
  message.addRecipient(Recipient_name, Recipient_email);

  //Send HTML message
  String htmlMsg = "<div style=\"color: #000000;\"><h1> PRIDAJ SVOJE VLASTNE UPOZORNENIE TEXT, ADD YOUR OWN WARNIIING !!!!!!!</h1><p> Timer Camera X  M5STACK</p></div>";
  message.html.content = htmlMsg.c_str();
  message.text.charSet = "us-ascii";
  message.html.transfer_encoding = Content_Transfer_Encoding::enc_7bit;

  
  if (!smtp.connect(&session))
    return;
  if (!MailClient.sendMail(&smtp, &message))
    Serial.println("Error sending Email, " + smtp.errorReason());
}

// METODA NA ZAPNUTIE BZUCIAKA A VYPNUTIE 
void controlBuzzer(bool on) {
  if (on) {
    porthub.hub_d_wire_value_A(BUZZER_CHANNEL, HIGH);  // ZAPNI BZUCIAK
  } else {
    porthub.hub_d_wire_value_A(BUZZER_CHANNEL, LOW);  // VYPNI BZUCIAK
  }
}

// Táto metóda prijíma obrázok vo formáte reťazca dát a jeho veľkosť
// a posiela ho na Google Drive pomocou HTTPS POST požiadavky.

String SendCapturedImageToGoogleDrive(const char* image, size_t imageSize) {
    // Doména, na ktorú budeme posielať požiadavku
  const char* myDomain = "script.google.com";
    // Premenné na ukladanie získaného tela odpovede a všetkých dát odpovede
  String getAll="", getBody = "";
  
    // Získanie obrázka z kamery
  camera_fb_t * fb = NULL;
  fb = esp_camera_fb_get(); 

  // Kontrola, či bolo úspešne získaný obrázok
  if(!fb) {
    Serial.println("Camera capture failed");
    delay(1000);
   ESP.restart();
   return "Camera capture failed";  }  
  
  // Pripojenie na danú doménu pomocou HTTPS
  Serial.println("Connect to " + String(myDomain));
  WiFiClientSecure client_tcp;
  client_tcp.setInsecure();   
  
   // Ak sa podarilo pripojiť
  if (client_tcp.connect(myDomain, 443)) {
    Serial.println("Connection successful");
    
    char *input = (char *)fb->buf;
    char output[base64_enc_len(3)];
        // Pridanie zakódovaného reťazca do URL reťazca
    String imageFile = "data:image/jpeg;base64,";
    for (int i=0;i<fb->len;i++) {
      base64_encode(output, (input++), 3);
      if (i%3==0) imageFile += urlencode(String(output));
    
    }
      // Zostavenie reťazca dát, ktoré budú odoslané
    String Data = driveFoldername+driveFilename+driveImage;
    
     // Nastavenie hlavičiek HTTP požiadavky
    client_tcp.println("POST " + driveScriptPath + " HTTP/1.1");
    client_tcp.println("Host: " + String(myDomain));
    client_tcp.println("Content-Length: " + String(Data.length()+imageFile.length()));
    client_tcp.println("Content-Type: application/x-www-form-urlencoded");
    client_tcp.println("Connection: keep-alive");
    client_tcp.println();
    
      // Odoslanie dát na server
    client_tcp.print(Data);
    int Index;
    for (Index = 0; Index < imageFile.length(); Index = Index+1000) {
      client_tcp.print(imageFile.substring(Index, Index+1000));
    }
    esp_camera_fb_return(fb);
    
    // Čakanie na odpoveď od serveru
    int waitTime = 10000;   // timeout 10 seconds
    long startTime = millis();
    boolean state = false;
    
       // Kým neuplynie timeout, čítaj odpoveď od serveru
    while ((startTime + waitTime) > millis())
    {
      Serial.print(".");
      delay(100);      
      while (client_tcp.available()) 
      {
          char c = client_tcp.read();
          if (state==true) getBody += String(c);        
          if (c == '\n') 
          {
            if (getAll.length()==0) state=true; 
            getAll = "";
          } 
          else if (c != '\r')
            getAll += String(c);
          startTime = millis();
       }
       if (getBody.length()>0) break;
    }
    client_tcp.stop();
    Serial.println(getBody);
  }
  else {
       // Ak sa nepodarilo pripojiť na danú doménu
    getBody="Connected to " + String(myDomain) + " failed.";
    Serial.println("Connected to " + String(myDomain) + " failed.");
  }
  
  return getBody;
}

void loop() {

  // Čítanie hodnoty z PIR senzora pripojeného k PortHub
  uint8_t pirValue = porthub.hub_d_read_value_A(PIR_SENSOR_CHANNEL);

  // Spracovanie hodnoty PIR , LOGIKA JE NASTAVENA NNA PIR AK DETEGUJE POHYB AZ VTEDY NECH SA NIECO DEJE
  if (pirValue == HIGH) {

    controlBuzzer(true);
    delay(2000);
    controlBuzzer(false);
    SendCapturedImageToGoogleDrive((const char*)camBuf, camSize);
    sendEmail();
/*
    if (!isCameraActive) {
      //activateCamera();
      isCameraActive = true;
      lastActivationTime = millis();
    }
*/
    // Turn off the buzzer
  } else {
    //Serial.println("No motion detected.");
    //esp_sleep_enable_ext0_wakeup((gpio_num_t)porthub.hub_d_read_value_A(PIR_SENSOR_CHANNEL), HIGH);
    // Check if the camera has been active for more than 10 minutes (adjust as needed)
   // if (isCameraActive && (millis() - lastActivationTime > activationInterval)) {
         
      //isCameraActive = false;
    }
    //controlBuzzer(false);
  
  // Delay for another 100 milliseconds, then turn on the LED
  delay(100);
  //digitalWrite(2, LOW);
}


