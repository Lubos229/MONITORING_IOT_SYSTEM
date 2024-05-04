Inštrukcie/Instruction SVK /ENG 

SVK------------------------------------------------------------------------------------------------------------------------------------------------------------
Aby tie scripty mohli fungovať je potrebné mat vytvorený MJPEG, stream, obraz spracovavame a pracujeme sním.

SPRAVNE PORADIE SPUSTENIE SCRIPTOV. 1. Registration.py, 2. extraction_into_database.py, real_time_attendance_system.py

Je potrebné mať súbory :  data_dlib ( dlib_face_recognition_resnet_model_v1, shape_predictor_68_face_landmarks)
Predtrenovaný model facenet, bez týchto suborov by nebola možná detekcia  tváre !!! 

záloha na súbory. link: https://drive.google.com/drive/u/2/folders/1oD7QMyvHiH8qHl1UoG1-w5G2nzbaqBpM
priečinok data_faces_from_camera (registracia - vytvorenie jednotlivých priečinkov pre každu osobu.)

je treba mať vytorené tieto priečinky !!
------------------------------------------------------------------------------------------------------------------------------------------------------
[Registration.py,] 
PRACOVAVANIE OBRAZU Z URL/ip ADRESY VYTVORENOU ARDUINO SKRIPTOM
REGISTROVANIE POUZIVATELOV, SNIMANIE FOTOGRAFIÍ TVARI, FINGERPRINT, ulozenie do priecinku

pripojenie PostgreSql databaza, svoje vlastné atributy 
Riadky 30 -37

riadok 136 URL/IP adresa vytvorená arduinom scriptom Vlozenie:
 esp32_ip = ""

self.flask_server = make_server('0.0.0.0', 5000, app)
vytvorenie API je nastavené na local ip, tato local ip sa zadáva do arduino_scriptu esp32_fingerprint


-----------------------------------------------------------------------------------------------------------------------------------------------------------
[extraction_into_database.py]
PRACA S ULOZENYMI SNIMKAMI TVARE, FINGERPRINT, SPRACOVANIE, APLIKOVANIE MODELU FACENET, SPRAVENIE STREDNEJ HODNOTY 128D VEKTORA ULOZENIE DO DATABAZY,
POSTGRESQL DATABAZA

pripojenie PostgreSql databaza - 13-18 riadky
26-34, 38,46 vytvorenie tabuliek, 

Pristupujeme ku "data/data_faces_from_camera/"
Spracovávame obrazky, fingerprint.

taktiez potrebne mat oba modely, spomenute vyššie link hore na google drive
data/data_dlib/shape_predictor_68_face_landmarks.dat'
data/data_dlib/dlib_face_recognition_resnet_model_v1.dat
-----------------------------------------------------------------------------------------------------------------------------------------------------------
[real_time_attendance_system.py]
SNIMANIE TVARE ODTLACKU PRSTA V REALNOM CASE, SPRACOVAVANIE OBRAZU Z URL/ip ADRESY VYTVORENOU ARDUINO SKRIPTOM, DETEKCIA TVARE POMOCOU DLIB MODELOV FACENET VEKTOR POROVNAVAME S NASOU DATABAZOU S PRAHOVOU HODNOTOU, A NA ZAKLADE EUKLIDOVSKEJ VZDIALENOSTI DOKAZEME DEFINOVAT POUZIVATELA. 


29-37, POSTGRESQL databaza 

Opat pristupujeme a potrebujeme subory DLIB, 
PRIKLADAME AJ MP3 subory PRI STLACENI TLACIDLA ARRIVAL, DEPARTURE....
RIADOK 742 esp32_ip = "" Vlozenie svojej vytvorenej URL adresy.

Je tu aj pouzity dark mode forest-dark prikladame do priečinku vsetky subory, ktore su nutne. NEVYMAZAVAT !! 


{ENG}}----------------------------------------------------------------------------------------------------------------------------------------------------
In order for those scripts to work, it is necessary to have an MJPEG created, a stream, we process the image and work with it
RUN SCRIPTS IN THE CORRECT ORDER. 1. Registration.py, 2. extract_into_database.py, real_time_attendance_system.py


Need to have files: data_dlib ( dlib_face_recognition_resnet_model_v1, shape_predictor_68_face_landmarks)
Pre-trained facenet model, face detection would not be possible without these files !!!

file backup. link: https://drive.google.com/drive/u/2/folders/1oD7QMyvHiH8qHl1UoG1-w5G2nzbaqBpM
folder data_faces_from_camera (registration - creation of individual folders for each person.)

these folders must not  be deleted!!
-----------------------------------------------------------------------------------------------------------------------------------------------------
[Registration.py,]

PROCESSING IMAGE FROM URL/IP ADDRESS CREATED BY ARDUINO SCRIPT
USER REGISTRATION, FACE PHOTO CAPTURE, fingerprints, save to folder
PostgreSql database connection, its own attributes
Lines 30-37

line 136 URL/IP address created by arduino script Insertion:
   esp32_ip = ""

self.flask_server = make_server('0.0.0.0', 5000, application)
API setting is installed local on local ip, ip is entered in arduino_script esp32_fingerprint

------------------------------------------------------------------------------------------------------------------------------------------------------

[Extraction_into_database.py]

WORKING WITH SAVED SHAPE SNAPSHOTS, FINGERPRINT, PROCESSING, APPLYING THE FACENET MODEL, MEANING A 128D VECTOR SAVING IN A DATABASE,
POSTGRESQL DATABASE

connection to the PostgreSql database - 13-18 lines
26-34, 38,46 creating tables,

Accessing "data/data_faces_from_camera/"
We process images, fingerprint.

it is also necessary to have both models, mentioned above in the link above on google drive
data/data_dlib/shape_predictor_68_face_landmarks.dat'
data/data_dlib/dlib_face_recognition_resnet_model_v1.dat
----------------------------------------------------------------------------------------------------------------------------------------------------------
[real-time_attendance_system.py]
FINGERPRINT SHAPE SENSING IN REAL CASE, IMAGE PROCESSING FROM URL/IP ADDRESS CREATED BY ARDUINO SCRIPT, SHAPE DETECTION USING DLIB MODELS FACENET VECTOR WE COMPARE USER EUOTO OVAT LOADING WITH OUR PRAGUE-BASED DATABASE.


29-37, POSTGRESQL database

Again we access and need DLIB files,
WE ALSO ATTACH MP3 files WHEN YOU PRESS THE ARRIVAL, DEPARTURE BUTTON....
LINE 742 esp32_ip = "" Inserting your generated URL.

There is also the use of dark mode forest-dark, we add all the necessary files to the folder. DO NOT DELETE!!







