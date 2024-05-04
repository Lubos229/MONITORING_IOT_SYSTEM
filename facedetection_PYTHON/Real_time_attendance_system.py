import dlib
import numpy as np
import cv2
import os
import pandas as pd
import time
import logging
import sqlite3
import datetime
import psycopg2
import tkinter as tk
from tkinter import messagebox
from tkinter import ttk, simpledialog
from tkinter.ttk import Treeview
from threading import Thread, Event
import threading
from datetime import datetime, date
from gtts import gTTS
import pyttsx3
from flask import Flask, request, jsonify
from werkzeug.serving import make_server





app = Flask(__name__)
  # Databaza postgres, mozne pripojenie aj v lokalnej sieti...
db_settings = {
            'user': '',
            'password': '',
            'host': '',
            'port': '',
            'database': ''
        }
connection = psycopg2.connect(**db_settings)
cursor = connection.cursor()


# Dlib  / Pouzitie face detector Dlib
detector = dlib.get_frontal_face_detector()

# Dlib landmark 
predictor = dlib.shape_predictor('data/data_dlib/shape_predictor_68_face_landmarks.dat')

# Dlib a ziskanie 128D deskriptora tvare
face_reco_model = dlib.face_recognition_model_v1("data/data_dlib/dlib_face_recognition_resnet_model_v1.dat")
posledna_akcia = None

extracted_id = 10000
extracted_comparision=0
extracted_id_dochadzka = 0

class Face_Recognizer:
    
    def __init__(self):
        self.root = None
        self.info_fingerprint= None
        self.worker_options_root = None
        self.worker_options_gui = None
        self.Skusame = False
        self.flask_server = None
        self.flask_thread = None
        self.stop_threads = threading.Event()
        self.zastavanie_kamery = False
        self.frame_pocet = 0  #  frame pocitanie
        self.pause_event = threading.Event()  # Create a threading event
        self.face_recognition_thread = None 
        
        
        self.font = cv2.FONT_ITALIC
        # FPS
        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0
        self.fps_show = 0
        self.start_time = time.time()

        # pocitadlo na frame
        self.frame_pocet = 0

        #  Ulozit the features tvari z databazy
        self.tvare_vektory_databaza = []
        self.tvare_fingerprinty_databaza = []
        # / Uloz mena  tvari in the database
        self.tvare_mena_databaza= []

        # SkuSKA S centroidom,....
        self.posledny_frame_tvare_centroid_list = []
        self.sucasny_frame_tvare_centroid_list = []

        self.posledny_frame_tvare_meno_list = []
        self.sucasny_frame_tvare_meno_list = []

        #  pocet  tvari vo frame N-1 and N
        self.posledny_frame_tvare_pocet = 0
        self.sucasny_frame_tvare_pocet = 0

        # Ulozenie sucasnej  e-vzdialenosť pre faceX pri rozpoznávaní
        self.sucasny_frame_tvar_X_e_vzdialenost_list = []

        # Ulozit polohy a mená aktuálnych zachytenych tvari
        self.sucasny_frame_tvar_position_list = []
        #  Ulozit features ludi v sucasnom frame
        self.sucasny_frame_tvar_vektor_list = []

        # e vzdialenost medzi centroid of ROI in last and current frame
        self.posledny_sucasny_frame_centroid_e_vzdialenost = 0

        #  reklasifikacia po 'reclassify_interval' pocet frames
        self.reklasifikacia_interval_pocet = 0
        self.reklasifikacia_interval = 10



    def stop_threads_metoda(self):
        print("Stopping Flask server...")
        self.stop_threads.set()
        if self.flask_server:
            self.flask_server.shutdown()


    def stop_worker_options_gui(self):
        print("Stopping worker options GUI...")
        if self.worker_options_root:
            self.worker_options_root.destroy()
          
            

   
    def show_zamestnancec_moznosti_gui(self, cele_meno, dany_vektor_tvare):
        
        self.root.withdraw()
        self.Skusame = True
        
      
    
        self.root.after(0, self.vytvor_zamestnanec_moznosti_gui, cele_meno, dany_vektor_tvare)

       




    def vytvor_zamestnanec_moznosti_gui(self, cele_meno, dany_vektor_tvare):
    # Vytvorte okno možností pracovníka

        self.sucasny_stav = "pociatocny"  # 
        zamestnanec_moznosti_frame = tk.Toplevel(self.worker_options_root)
        zamestnanec_moznosti_frame.title("Zamestnanec Moznosti")

        self.prichod_button = tk.Button(zamestnanec_moznosti_frame, text="Prichod", command=lambda: oznacit_prichod_or_odchod(True))
        self.odchod_button = tk.Button(zamestnanec_moznosti_frame, text="Odchod", command=lambda: oznacit_prichod_or_odchod(False))

        self.prichod_button.pack()
        self.odchod_button.pack()



        def zatvorenie_okna_zamestnanec():
            global extracted_id
            
            #self.stop_threads_metoda()
            self.stop_worker_options_gui()
            

           
            print("zatvorenie_okna_zamestnanec")
            

            self.Skusame = False
            print ("zatvorenie_okna_zamestnanec")
            print (self.Skusame)
            
            print ("IDE FACE RECOGNIZER")
            extracted_id = 10000
            extracted_comparision = 0
            Face_Recognizer_con = Face_Recognizer()
            Face_Recognizer_con.run()
            
            
            
       

        zamestnanec_moznosti_frame.protocol("WM_DELETE_WINDOW", zatvorenie_okna_zamestnanec)

 
       
        # Kontrolovat, či poslednou akciou bol príchod alebo odchod
      
        def update_button_visibility():
            if self.sucasny_stav == "pociatocny":
                self.prichod_button.pack()
                self.odchod_button.pack()
                dochadzka_button.pack()
                back_button.pack_forget()  # Skrytie tlačidla „zobrazenie dochadzky“.
            elif self.sucasny_stav == "zobrazenie dochadzky":
                self.prichod_button.pack_forget()  # Skryť button príchod
                self.odchod_button.pack_forget()  # Skryť button odchod
                dochadzka_button.pack_forget()  # Skryť button dochadzka
    

        dochadzka_button = tk.Button(zamestnanec_moznosti_frame, text="Dochadzka", command=lambda: zobrazenie_dochadzky(dany_vektor_tvare, zamestnanec_moznosti_frame))
        dochadzka_button.pack()

        back_button = tk.Button(zamestnanec_moznosti_frame, text="Zobrazenie Dochadzky", command=lambda: zobrazenie_dochadzky(dany_vektor_tvare, zamestnanec_moznosti_frame))
       
        back_button.pack_forget()




        def zobrazenie_dochadzky(dany_vektor_tvare, zamestnanec_moznosti_frame):
        # Ziskad  ID  zamestnanca na zaklade vektora tvare
            global extracted_id_dochadzka
            select_employee_query = '''
            SELECT id, first_name, last_name FROM person_data 
            WHERE features = %s OR fingerprint = %s
            '''


            cursor.execute(select_employee_query, (dany_vektor_tvare,extracted_id_dochadzka))
            employee_id = cursor.fetchone()

            self.current_state = "zobrazenie_dochadzky"

            update_button_visibility()

            if employee_id:
                employee_id = employee_id[0]

                # Ziskat aktualne datumy, casy
                aktualny_datum = datetime.now()
                start_date = aktualny_datum.replace(day=1)
                end_date = aktualny_datum.replace(month=aktualny_datum.month + 1, day=1)

                # Ziskanie udajov o dochadzke zamestnanca za aktualny mesiac
                select_attendance_query = """
                SELECT attendance_date, arrival_time, departure_time, time_difference
                FROM dochadzka
                WHERE employee_id = %s
                AND attendance_date >= %s
                AND attendance_date < %s
                """
                cursor.execute(select_attendance_query, (employee_id, start_date, end_date))
                attendance_data = cursor.fetchall()

                # celkovy casovy cas odpracovany za mesiac
                total_time_difference = sum(row[3] if row[3] is not None else 0 for row in attendance_data)

                # Vytvorenie tabulky zobrazovat dochadzku ako tabulku
                table = ttk.Treeview(zamestnanec_moznosti_frame, columns=("Datum", "Cas prichodu", "Cas odchodu", "Pocet hodin"))
                table.heading("#1", text="Datum")
                table.heading("#2", text="Cas prichodu")
                table.heading("#3", text="Cas odchodu")
                table.heading("#4", text="Pocet hodin")

                for row in attendance_data:
                    table.insert("", "end", values=row)

                table.pack()

                # Zobrazenie kolko hodin teda odpracoval zamestnanec
                total_label = tk.Label(zamestnanec_moznosti_frame, text=f"Celkovy odpracovany cas za  {aktualny_datum.strftime('%B')}: {total_time_difference} hours")
                total_label.pack()

                
            
       
 


        def oznacit_prichod_or_odchod(arrival):
            global posledna_akcia
            global extracted_id_dochadzka
            aktualny_datum = datetime.now().date()
            aktualny_cas = datetime.now().time()

            # Najdenie zamestnanec_id na základe dany_vektor_tvare v  databaze
            select_employee_query = '''
            SELECT id, first_name, last_name FROM person_data 
            WHERE features = %s OR fingerprint = %s
            '''
            cursor.execute(select_employee_query, (dany_vektor_tvare,extracted_id_dochadzka))
            result = cursor.fetchone()
            zvuk = pyttsx3.init()
            zvuk.setProperty('rate', 150)  #  rýchlosť reči
            zvuk.setProperty('volume', 1.0)  # hlasitost
            zvuk.setProperty('voice', 'sk-SK') #  snaha ale nefunguje
            for voice in zvuk.getProperty('voices'):
                print(voice)

            if result:
                employee_id, first_name, last_name = result
                
                check_attendance_query = '''
                SELECT id, arrival_time, departure_time FROM dochadzka
                WHERE employee_id = %s AND attendance_date = %s 
                '''
                cursor.execute(check_attendance_query, (employee_id, aktualny_datum))
                existujuca_dochadzka = cursor.fetchall()  # všetky záznamy za daný deň
                cele_meno = f"{first_name} {last_name}" 

                if arrival:
                    if existujuca_dochadzka:
                        for record in existujuca_dochadzka:
                            if record[1] is not None and record[2] is None:  # ci je prichod zaznamenany a ci je odchod nulovy
                                print("Prichod uz je zaznamenany")
                                os.system("prichod_zaznamenany")
                                break
                        else:
                            # vytvor novy riadok
                            insert_query = '''
                            INSERT INTO dochadzka (employee_id, attendance_date, arrival_time)
                            VALUES (%s, %s, %s)
                            RETURNING id
                            '''
                            cursor.execute(insert_query, (employee_id, aktualny_datum, aktualny_cas))
                            new_record_id = cursor.fetchone()[0]
                            posledna_akcia = 'arrival'
                            # os.system("prichod_zaznamenany1.mp3")
                            print(f"{cele_meno} prichod zaznamenany.")
                            message = "Príchod už je zaznamenaný"
                            zvuk.say(message)
                            zvuk.runAndWait()
                    else:
                        # vytvor novy riadok
                        insert_query = '''
                        INSERT INTO dochadzka (employee_id, attendance_date, arrival_time)
                        VALUES (%s, %s, %s)
                        RETURNING id
                        '''
                        cursor.execute(insert_query, (employee_id, aktualny_datum, aktualny_cas))
                        new_record_id = cursor.fetchone()[0]
                        posledna_akcia = 'arrival'
                        print(f"{cele_meno} prichod zaznamenany.")
                        message = "Príchod zaznamenaný"
                        zvuk.say(message)
                        zvuk.runAndWait()
                else:
                    for record in existujuca_dochadzka:
                        if record[2] is None and record[1] is not None:  # ak je odchod nulovy a prichod je zaznamenany
                            # updatni riadok s prichodom 
                            update_query = '''
                            UPDATE dochadzka
                            SET departure_time = %s
                            WHERE id = %s
                            '''
                            cursor.execute(update_query, (aktualny_cas, record[0]))
                            # vypocitaj rozdiel casovy
                            time_difference = casovy_rozdiel(record[1], aktualny_cas)
                            update_time_difference_query = '''
                            UPDATE dochadzka
                            SET time_difference = %s
                            WHERE id = %s
                            '''
                            cursor.execute(update_time_difference_query, (time_difference, record[0]))
                            posledna_akcia = 'departure'
                            print(f"{cele_meno} odchod zaznamenany.")
                            message = "Odchod zaznamenaný"
                            zvuk.say(message)
                            zvuk.runAndWait()
                            break
                    else:

                        message = "Neexistuje príchod"
                        zvuk.say(message)
                        zvuk.runAndWait()
                connection.commit()

        # Vypočítanie časoveho rozdielu medzi dvoma časmi
        
        def casovy_rozdiel(arrival_time, departure_time):
            prichod_datum_cas = datetime.combine(date.today(), arrival_time)
            odchod_datum_cas = datetime.combine(date.today(), departure_time)
            cas_rozdiel_sekundy = (odchod_datum_cas - prichod_datum_cas).total_seconds()
            cas_rozdiel_minuty = cas_rozdiel_sekundy / 60.0  # na minuty

            cas_rozdiel_minuty_zvysok = cas_rozdiel_minuty%60
            #print(cas_rozdiel_minuty_zvysok)
            cas_rozdiel_hodiny=cas_rozdiel_minuty//60
            #cas_rozdiel_minuty


            if cas_rozdiel_minuty_zvysok > 30:
                cas_rozdiel_hodiny= cas_rozdiel_hodiny+0.5
                #print(cas_rozdiel_minuty)
                

            # AK je viac ako 6 hodin - pol hodina prestavka zakon
            if cas_rozdiel_hodiny > 6:
                cas_rozdiel_hodiny -= 0.5  # - 0,5 
                
            return cas_rozdiel_hodiny



        


 # Ziskat údaje z databázy PostgreSQL
    def ziskat_tvare_databaza(self):
        # ziskat data z databazy
        select_query = "SELECT first_name, last_name, features, fingerprint FROM person_data"
        cursor.execute(select_query)
        records = cursor.fetchall()

        if records:
            for record in records:
                first_name, last_name, features, fingerprint = record
                self.tvare_mena_databaza.append(f"{first_name} {last_name}")
                self.tvare_vektory_databaza.append(features)
                self.tvare_fingerprinty_databaza.append(fingerprint)
            logging.info("tvare v databaze: %d", len(self.tvare_vektory_databaza))
            logging.info("Fingerprinty v databaze: %d", len(self.tvare_fingerprinty_databaza))
            return 1
        else:
            logging.warning("V databaze nie su ziadne tvare !")
            return 0

    def update_fps(self):
        now = time.time()
        # Refresh fps per second
        if str(self.start_time).split(".")[0] != str(now).split(".")[0]:
            self.fps_show = self.fps
        self.start_time = now
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now

    @staticmethod
    # Vypocitanie e-vzdialenosti medzi 128 d vektormi
    def return_euklidovsku_vzdialenost(vektor_1, vektor_2):
        vektor_1 = np.array(vektor_1).astype(float)  # Convert to float
        vektor_2 = np.array(vektor_2).astype(float)  # Convert to float
        vzdialenost = np.sqrt(np.sum(np.square(vektor_1 - vektor_2)))
        return vzdialenost
    

    # / Pouzitie centroid sledovanie  na danu tvar v sucasnom frame s person_x v poslednom frame
    def centroid_sledovanie(self):
        for i in range(len(self.sucasny_frame_tvare_centroid_list)):
            e_vzdialenost_sucasny_frame_person_x_list = []
            # Pre objekt 1 v aktuálnom rámci vypočítanie e-vzdialenosť s objektom 1/2/3/4/... v poslednom rámci
            for j in range(len(self.posledny_frame_tvare_centroid_list)):
                self.posledny_sucasny_frame_centroid_e_vzdialenost = self.return_euklidovsku_vzdialenost(
                    self.sucasny_frame_tvare_centroid_list[i], self.posledny_frame_tvare_centroid_list[j])

                e_vzdialenost_sucasny_frame_person_x_list.append(
                    self.posledny_sucasny_frame_centroid_e_vzdialenost)

            posledny_frame_cislo = e_vzdialenost_sucasny_frame_person_x_list.index(
                min(e_vzdialenost_sucasny_frame_person_x_list))
            self.sucasny_frame_tvare_meno_list[i] = self.posledny_frame_tvare_meno_list[posledny_frame_cislo]

    #  cv2 okno / text do okna cv2
    def info_note_gui(self, img_rd):
        #  / Dalsie informacie, tvar,fps, zrusenie appky
        cv2.putText(img_rd, "Detekcia tvare", (20, 40), self.font, 1, (255, 255, 255), 1, cv2.LINE_AA)
        cv2.putText(img_rd, "Frame:  " + str(self.frame_pocet), (20, 100), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "FPS:    " + str(self.fps.__round__(2)), (20, 130), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "Tvare:  " + str(self.sucasny_frame_tvare_pocet), (20, 160), self.font, 0.8, (0, 255, 0), 1,
                    cv2.LINE_AA)
        cv2.putText(img_rd, "Q: Zrusit", (20, 450), self.font, 0.8, (255, 255, 255), 1, cv2.LINE_AA)

        for i in range(len(self.sucasny_frame_tvare_meno_list)):
            img_rd = cv2.putText(img_rd, "Tvar" + str(i + 1), tuple(
                [int(self.sucasny_frame_tvare_centroid_list[i][0]), int(self.sucasny_frame_tvare_centroid_list[i][1])]),
                                 self.font,
                                 0.8, (255, 190, 0),
                                 1,
                                 cv2.LINE_AA)
        
        if self.info_fingerprint is not None:
            cv2.putText(img_rd, "Fingerprint nie je ulozeny v databaze " + str(extracted_id), (20, 550), self.font, 0.8, (255, 255, 255), 1, cv2.LINE_AA)   
 
  

    # Detekcia a rozpoznávanie tváre s OT zo vstupného video streamu
    def process(self, stream):
      
        global extracted_id
        global extracted_comparision
        global extracted_id_dochadzka
        # 1.  Tahanie tvare z  pola uz (z databazy)
        if self.ziskat_tvare_databaza():
            while not self.zastavanie_kamery:
                self.frame_pocet += 1
                logging.debug("Frame " + str(self.frame_pocet) + " starts")
                flag, img_rd = stream.read()
                kk = cv2.waitKey(1)

                # 2.  Rozpoznat  tvar pre frame X
                tvare = detector(img_rd, 0)


                if not self.pause_event.is_set(): 

                    # 3.  Aktualizacia poctu pre tvare v frames
                    self.posledny_frame_tvare_pocet = self.sucasny_frame_tvare_pocet
                    self.sucasny_frame_tvare_pocet = len(tvare)

                    # 4.  Aktualizovat zoznam mien tvari v list v poslednom frame
                    self.posledny_frame_tvare_meno_list = self.sucasny_frame_tvare_meno_list[:]

                    # 5.  aktualizovat frame centroid list
                    self.posledny_frame_tvare_centroid_list = self.sucasny_frame_tvare_centroid_list
                    self.sucasny_frame_tvare_centroid_list = []
                   

                  
                    for i in range(len(self.tvare_fingerprinty_databaza)):
                        if str(self.tvare_fingerprinty_databaza[i]).strip() == str(extracted_id).strip() and int(extracted_comparision)> 70:
                            self.info_fingerprint = None
                            print(f"Fingerprint ID {i} matches with extracted ID {extracted_id} and comparison is greater than 70.")
                            print ("splnili sme")
                            extracted_id_dochadzka = extracted_id
                            extracted_id = 10000;
                            print("OPAT 100"+str(extracted_id))
                            
                            cele_meno = self.tvare_mena_databaza[i]
                            dany_vektor_tvare = self.tvare_vektory_databaza[i]
                            self.show_zamestnancec_moznosti_gui(cele_meno, dany_vektor_tvare)
                            self.pause_event.set()
                            #self.pause_event.clear()
                            print("toto je skusame")
                            print (self.Skusame)

                            while not self.Skusame:
                                self.pause_event.clear()
                                print("clear")
                                print("cistim okno")
                    # SANCA AK JE ULOZENE VO FINGERPRINTE ALE NENI V NASEJ DATABAZE, FINGERPRINT MA SVOJU DATABAZU
                    if 1 <= int(extracted_id) <= 162 and all(str(extracted_id).strip() != str(fp_id).strip() for fp_id in self.tvare_fingerprinty_databaza):
                        self.info_fingerprint= True
                       
      

                    # 6.1  ak sa pocet tvari not changes
                    if (self.sucasny_frame_tvare_pocet == self.posledny_frame_tvare_pocet) and (
                            self.reklasifikacia_interval_pocet != self.reklasifikacia_interval):
                        logging.debug("scene 1:   Nezmenila sa ziadna zmena tvare v tomto frame!!!")

                        self.sucasny_frame_tvar_position_list = []

                        if "tvar neznama" in self.sucasny_frame_tvare_meno_list:
                            self.reklasifikacia_interval_pocet += 1

                        if self.sucasny_frame_tvare_pocet != 0:
                            for k, d in enumerate(tvare):
                                self.sucasny_frame_tvar_position_list.append(tuple(
                                    [tvare[k].left(), int(tvare[k].bottom() + (tvare[k].bottom() - tvare[k].top()) / 4)]))
                                self.sucasny_frame_tvare_centroid_list.append(
                                    [int(tvare[k].left() + tvare[k].right()) / 2,
                                    int(tvare[k].top() + tvare[k].bottom()) / 2])

                                img_rd = cv2.rectangle(img_rd,
                                                    tuple([d.left(), d.top()]),
                                                    tuple([d.right(), d.bottom()]),
                                                    (255, 255, 255), 2)

                        # Viac  tvári v aktuálnom frame, na sledovanie použit centroid-tracker
                        if self.sucasny_frame_tvare_pocet != 1:
                            self.centroid_sledovanie()

                        for i in range(self.sucasny_frame_tvare_pocet):
                            # 6.2 Napisat mena
                            img_rd = cv2.putText(img_rd, self.sucasny_frame_tvare_meno_list[i],
                                                self.sucasny_frame_tvar_position_list[i], self.font, 0.8, (0, 255, 255), 1,
                                                cv2.LINE_AA)
                        self.info_note_gui(img_rd)

                    # 6.2  Ak sa zmeni pocet tvari 0->1 or 1->0 or ...
                    else:
                        logging.debug("scene 2: / pocet tvari sa zmenil v tomto frame")
                        self.sucasny_frame_tvar_position_list = []
                        self.sucasny_frame_tvar_X_e_vzdialenost_list = []
                        self.sucasny_frame_tvar_vektor_list = []
                        self.reklasifikacia_interval_pocet = 0

                        # 6.2.1  Pocet tvari klesol: 1->0, 2->1, ...
                        if self.sucasny_frame_tvare_pocet == 0:
                            logging.debug("  / Nie su ziadne tvare v tomto frame!!!")
                            # vycistit  list mien a vektorov
                            self.sucasny_frame_tvare_meno_list = []
                        # 6.2.2 / Pocet tvari narastol: 0->1, 0->2, ..., 1->2, ...
                        else:
                            logging.debug("  scene 2.2  Ziskat tvare v tomto frame a spravit recognizaciu")
                            self.sucasny_frame_tvare_meno_list = []
                            for i in range(len(tvare)):
                                shape = predictor(img_rd, tvare[i])
                                self.sucasny_frame_tvar_vektor_list.append(
                                    face_reco_model.compute_face_descriptor(img_rd, shape))
                                self.sucasny_frame_tvare_meno_list.append("tvar neznama")

                            # 6.2.2.1 Prejdenie všetkych tvári v databáze
                            for k in range(len(tvare)):
                                logging.debug("  For face %d in current frame:", k + 1)
                                self.sucasny_frame_tvare_centroid_list.append(
                                    [int(tvare[k].left() + tvare[k].right()) / 2,
                                    int(tvare[k].top() + tvare[k].bottom()) / 2])

                                self.sucasny_frame_tvar_X_e_vzdialenost_list = []

                                # 6.2.2.2  Zachytené polohy tvárí
                                self.sucasny_frame_tvar_position_list.append(tuple(
                                    [tvare[k].left(), int(tvare[k].bottom() + (tvare[k].bottom() - tvare[k].top()) / 4)]))

                                # 6.2.2.3 
                                # Pre každú rozpoznanú tvár porovnat tváre s databázou
                                for i in range(len(self.tvare_vektory_databaza)):
                                    if self.tvare_vektory_databaza[i] is not None and str(self.tvare_vektory_databaza[i][0]) != '0.0':
                                        e_distance_tmp = self.return_euklidovsku_vzdialenost(
                                            self.sucasny_frame_tvar_vektor_list[k],
                                            self.tvare_vektory_databaza[i])
                                        logging.debug("      with person %d, the e-distance: %f", i + 1, e_distance_tmp)
                                        self.sucasny_frame_tvar_X_e_vzdialenost_list.append(e_distance_tmp)
                                    else:
                                        #  person_X
                                        self.sucasny_frame_tvar_X_e_vzdialenost_list.append(999999999)
                                logging.debug ("skusame totoce%f", extracted_id)


                                
                              

                                

                                # 6.2.2.4 / Nájdenie tvare  s minimálnou vzdialenosťou e. prahova hodnota 0,4 
                                similar_person_num = self.sucasny_frame_tvar_X_e_vzdialenost_list.index(
                                    min(self.sucasny_frame_tvar_X_e_vzdialenost_list))

                                if min(self.sucasny_frame_tvar_X_e_vzdialenost_list) < 0.1:
                                    cele_meno = self.tvare_mena_databaza[similar_person_num]
                                
                                    
                                    dany_vektor_tvare= self.tvare_vektory_databaza[similar_person_num]
                    #print(dany_vektor_tvare)

                                    self.sucasny_frame_tvare_meno_list[k] = cele_meno
                                    logging.debug("  Tvar rozpoznana: %s", cele_meno,dany_vektor_tvare)

                                    
                                    self.show_zamestnancec_moznosti_gui(cele_meno,dany_vektor_tvare)
                                    self.pause_event.set()  

                                    
                                    print("toto je skusame")
                                    print (self.Skusame)

                                    while not self.Skusame:
                                        self.pause_event.clear()
                                        print("clear")
                                        print("cistim okno")
                                        
                                    
                                   
                                    print("MAM TA")
                                    print(self.Skusame)
                                    #print(type(cele_meno))
                                    #print(dany_vektor_tvare)
                                    # print("MAM TA")
                                    
                                
                                else:
                                    logging.debug("  Face recognition result: Neznama osoba")

                            # 7.  / Add note on cv2 window
                            self.info_note_gui(img_rd)

                    # 8.  'q'  / Press 'q' to exit
                    if kk == ord('q'):
                        print("zmackol si Q")
                        self.on_closing()
                        
                        
                        
                    self.update_fps()
                    cv2.namedWindow("camera", 1)
                    cv2.imshow("camera", img_rd)

                    logging.debug("Frame ends\n\n")
    




    def on_closing(self):    
        print("Aplikacia zatvorena.")
        self.stop_threads_metoda()
        self.zastavanie_kamery = True
        self.worker_options_root.destroy()
        self.root.destroy()  #  main okno zrusenie
       

        




    
    def start_flask_server(self):
            def receive_data():
                global extracted_id
                global extracted_comparision
                data_received = request.form.get('data')
                print(f"Received data: {data_received}")

                if 'toto' in data_received:
                    id_value = data_received.split('toto')
                    extracted_id = id_value[-1]
                    print(f"Extracted ID value: {extracted_id}")
                    return extracted_id

                if 'compare' in data_received:
                    id_comparision = data_received.split('compare')
                    extracted_comparision = id_comparision[-1]

                    print(f"Comparison value: {extracted_comparision}")
                    return extracted_comparision

            if not any(rule.endpoint == 'receive_data' for rule in app.url_map.iter_rules()):
                # Pridat "cestu" iba ak neexistuje
                self.flask_server = make_server('0.0.0.0', 5000, app)
                app.config['stop_flask_event'] = self.stop_threads  
                app.add_url_rule('/receive_data', 'receive_data', receive_data, methods=['POST'])

            if self.flask_server:
            
                self.flask_thread = Thread(target=self.flask_server.serve_forever)
                self.flask_thread.daemon = True
                self.flask_thread.start()

            print("Flask server is Funguje...")


    

    def run(self):
        esp32_ip = ""
        camera_url = esp32_ip
        cap = cv2.VideoCapture(camera_url)

        face_recognition_thread = threading.Thread(target=self.process, args=(cap,))
        face_recognition_thread.daemon = True
        face_recognition_thread.start()

        self.start_flask_server()

        # Initialize root properly
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.tk.call("source", "forest-dark.tcl")
        


        
        style = ttk.Style(self.root)
        style.theme_use("forest-dark")
        # Use Toplevel for additional windows
        self.worker_options_root = tk.Toplevel(self.root)
        self.worker_options_root.withdraw()
        self.worker_options_gui = WorkerOptionsGUI(self.worker_options_root)

        self.root.protocol("WM_DELETE_WINDOW")
        self.root.mainloop()
    
    
class WorkerOptionsGUI:
    def __init__(self, root):
        self.root = root

   


def main():
    #logging.basicConfig(level=logging.DEBUG) 
    logging.basicConfig(level=logging.INFO)
    Face_Recognizer_con = Face_Recognizer()
    Face_Recognizer_con.run()


if __name__ == '__main__':
    main()
