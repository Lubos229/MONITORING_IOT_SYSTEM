/***************************************************
  This is an example sketch for our optical Fingerprint sensor

  Designed specifically to work with the Adafruit Fingerprint sensor
  ----> http://www.adafruit.com/products/751

  These displays use TTL Serial to communicate, 2 pins are required to
  interface
  Adafruit invests time and resources providing this open source code,
  please support Adafruit and open-source hardware by purchasing
  products from Adafruit!

  Written by Limor Fried/Ladyada for Adafruit Industries.
  BSD license, all text above must be included in any redistribution
 ****************************************************/

#include <Adafruit_Fingerprint.h>
#include <SoftwareSerial.h>
#include <WiFi.h>
#include <HTTPClient.h>
const char* ssid = "******";
const char* password = "********";
String hlavna;

#define FINGERPRINT_RX 13
#define FINGERPRINT_TX 4

SoftwareSerial mySerial(FINGERPRINT_RX, FINGERPRINT_TX);

Adafruit_Fingerprint finger = Adafruit_Fingerprint(&mySerial);
const char* serverAddress = "http://*************/input_data";
const char* serverAddressPython = "http://****************/send_fingerprint";

void setup()
{
WiFi.begin(ssid, password);
while (WiFi.status() != WL_CONNECTED) {
  delay(500);
  Serial.print(".");
}
Serial.println("WiFi connected");
 Serial.begin(115200);
  mySerial.begin(57600);

  // set the data rate for the sensor serial port
  finger.begin(57600);

  if (finger.verifyPassword()) {
    Serial.println("Found fingerprint sensor!");
  } else {
    Serial.println("Did not find fingerprint sensor :(");
    while (1);
  }

  finger.getTemplateCount();

  if (finger.templateCount == 0) {
    Serial.print("Sensor neobsahuje ziadne fingerprint data. Prosim spusti registraciu a vytvor");
  }
  else {
    Serial.println("Waiting for valid finger...");
      Serial.print("Sensor ma: "); Serial.print(finger.templateCount); Serial.println(" odtlackov");
  }
}

void loop() {
  /*
  String enrolledIDs[127];
  int count = 0;

  for (uint8_t id = 1; id <= 127; ++id) {
    if (finger.getTemplateCount() > 0) {
      // Convert the ID to a string and store it in the array
      enrolledIDs[count++] = String(id);
    }
  }

  // Convert the array of enrolled IDs to a single string
  String enrolledIDsString = "Enrolled Fingerprint IDs: ";
  for (int i = 0; i < count; ++i) {
    enrolledIDsString += enrolledIDs[i];
    if (i < count - 1) {
      enrolledIDsString += ", ";
    }
  }


  // Send the enrolled fingerprint IDs string to the server
  hlavna= enrolledIDsString;
  hlavnasendFingerprintData();
*/
  delay(5000);  // Delay for 5 seconds before repeating

  hlavna = "Prosim napiste ID ktore chcete vymazat # (from 1 to 127)...";
  hlavnasendFingerprintData();


  HTTPClient http;

  http.begin(serverAddressPython);
  int httpResponseCode = http.GET();

  if (httpResponseCode == 200) {
    Serial.printf("HTTP Response code: %d\n", httpResponseCode);
    String fingerprintData = http.getString();

    Serial.println("Fingerprint data received: " + fingerprintData);

// Remove double quotes from the received data
fingerprintData.trim();
fingerprintData.remove(0, 1);
fingerprintData.remove(fingerprintData.length() - 1);

uint8_t id_delete = static_cast<uint8_t>(fingerprintData.toInt());

if (id_delete >= 1 && id_delete <= 127) {
    deleteFingerprint(id_delete);
} else {
    Serial.println("Invalid ID received from the server.");
}
    http.end();

  }
  else {
    Serial.printf("HTTP Request failed. Error code: %d. Details: %s\n", httpResponseCode, http.errorToString(httpResponseCode).c_str());
    delay(200);
  }
  
}






uint8_t deleteFingerprint(uint8_t id) {
  uint8_t p = -1;

  p = finger.deleteModel(id);

  if (p == FINGERPRINT_OK) {
    Serial.println("Deleted!");
    Serial.println("Fingerprint deleted successfully!");
  } else if (p == FINGERPRINT_PACKETRECIEVEERR) {
    Serial.println("Communication error");
  } else if (p == FINGERPRINT_BADLOCATION) {
    Serial.println("Could not delete in that location");
  } else if (p == FINGERPRINT_FLASHERR) {
    Serial.println("Error writing to flash");
  } else {
    Serial.print("Unknown error: 0x"); Serial.println(p, HEX);
  }

  return p;
}



void hlavnasendFingerprintData() {
  String fingerprintData = hlavna;

  // Create an HTTP object
  HTTPClient http;

  // Make a POST request to the server
  http.begin(serverAddress);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  int httpResponseCode = http.POST("data=" + fingerprintData);



  // Check for a successful request
  if (httpResponseCode > 0) {
    Serial.printf("HTTP Response code: %d\n", httpResponseCode);
    Serial.println(http.getString());
  } else {
    Serial.printf("HTTP Request failed. Error code: %d. Details: %s\n", httpResponseCode, http.errorToString(httpResponseCode).c_str());
  }

  // End the request
  http.end();

  delay(5); // Adjust delay based on your requirements
}

