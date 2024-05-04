import dlib
import numpy as np
import cv2
import os
import shutil
import time
import logging
import tkinter as tk
from tkinter import ttk, simpledialog
from tkinter import font as tkFont
from PIL import Image, ImageTk
from tkinter import PhotoImage
from threading import Thread, Event
import threading
from flask import Flask, request, jsonify
from werkzeug.serving import make_server
import requests
import psycopg2

# NUTNA INSTALACIA KNIZNIC,/ PLEASE INSTALL ALL LIBRARIES 


# PRED SPUSTENIM PROSIM CITAJ INSTRUCTIONS_PYTHON.txt


# FOR UNDERSTANDING PLEASE READ INSTRUCTIONS_PYTHON.txt




app = Flask(__name__)

volne_id_fingerprint_poslat: int
volne_id_fingerprint_poslat = 0
# frontal face detector of Dlib
detektor = dlib.get_frontal_face_detector()

# PostgreSQL databaza, nastav SVOje hodnoty, PLEASE UPDATE YOUR DATABASE VALUES
db_settings = {
    'user': '',
    'password': '',
    'host': '',
    'port': '',
    'database': ''
}



# Pripojenie k databaze
connection = psycopg2.connect(**db_settings)
cursor = connection.cursor()




class Face_Register:

    
    def __init__(self):

        self.spustenie_flask = False
        self.stream = None
        self.ziskanyfingerprint = None
        self.current_frame_tvari_pocet = 0  #  pocitadlo pre tvare v sučasnom frame
        self.ulozene_tvare_pocet = 0  # pocitadlo pre ulozene tvare
        self.id_finger = 0
        self.ss_pocet = 0  #  pocitadlo  pre spravene fotky 
        # Tkinter GUI
        self.okno = tk.Tk()
         #self.okno.tk.call("source", "forest-dark.tcl")
         #style = ttk.Style(self.okno)
         #style.theme_use("forest-dark")

        self.okno.title("Registracia zamestnancov")
        self.okno.geometry("1000x500")
        self.stop_threads = False 
        
        self.arduino_window = None 
        self.arduino_messages = ""
        self.arduino_text = None



      




       




       
       

        # GUI lava strana
        self.frame_left_camera = tk.Frame(self.okno)
        self.label = tk.Label(self.okno)
        self.label.pack(side=tk.LEFT)
        self.frame_left_camera.pack(side=tk.LEFT, padx=10)

        # GUI prava strana
        self.frame_right_info = tk.Frame(self.okno)
        self.label_pocet_tvari_uloz = tk.Label(self.frame_right_info, text=str(self.ulozene_tvare_pocet))
        self.label_fps_info = tk.Label(self.frame_right_info, text="")
        self.input_meno = tk.Entry(self.frame_right_info)
        self.input_meno_char = ""
        self.input_priezvisko_char = ""
        self.label_warning = tk.Label(self.frame_right_info)
        self.label_tvare_pocet = tk.Label(self.frame_right_info, text="Pocet tvari vo frame: ")
        self.log_all = tk.Label(self.frame_right_info)

        self.font_title = tkFont.Font(family='Helvetica', size=20, weight='bold')
        self.font_step_title = tkFont.Font(family='Helvetica', size=15, weight='bold')
        self.font_warning = tkFont.Font(family='Helvetica', size=15, weight='bold')

        self.path_photos_from_camera = "data/data_faces_from_camera/"
        self.current_face_dir = ""
        self.font = cv2.FONT_ITALIC

        # Current frame and face ROI position
        self.current_frame = np.ndarray
        self.face_ROI_image = np.ndarray
        self.face_ROI_width_start = 0
        self.face_ROI_height_start = 0
        self.face_ROI_width = 0
        self.face_ROI_height = 0
        self.ww = 0
        self.hh = 0

        self.out_of_range_flag = False
        self.face_folder_created_flag = False
        

        # FPS
        self.frame_time = 0
        self.frame_start_time = 0
        self.fps = 0
        self.fps_show = 0
        self.start_time = time.time()
        
        # Initialize camera stream from ESP32
        esp32_ip = ""
        camera_url = esp32_ip
        
        
        try:
            self.stream = cv2.VideoCapture(camera_url)
            self.stream.set(3, 320)  # Set width
            self.stream.set(4, 240)  # Set height
            
            if not self.stream.isOpened():
                raise Exception("Chyba: Nie je možné získať prístup k zdroju camere")
        except Exception as e:
            print(f"Error: {e}")

        

        


  # Odstráňte staré priečinky tváre
            

   
    def start_flask_server(self):
        def receive_data():
            
            prijate_data = request.form.get('data')
            print(f"Received data: {prijate_data}")

    # Update Tkinter text widget in Arduino window
            self.arduino_text.insert(tk.END, f"{prijate_data}\n")
            self.arduino_text.see(tk.END)  # Scroll to the end

            if 'ID=' in prijate_data:
                # Extrahovanie hodnotu ID z data_prijatych
                id_value = prijate_data.split('ID=')[1]
                print(f"ID hodnota: {id_value}")

                # Ulozit extrahovanu hodnotu ID do ziskanyfingerprint
                self.ziskanyfingerprint = id_value
                ziskanyfingerprint_file_path = os.path.join(self.current_face_dir, "ziskanyfingerprint.txt")
                with open(ziskanyfingerprint_file_path, "w") as fingerprint_file:
                    fingerprint_file.write(self.ziskanyfingerprint)

                print(f"Ziskanyfingerprint saved to: {ziskanyfingerprint_file_path}")

        self.flask_server = make_server('0.0.0.0', 5000, app)
        app.config['stop_flask_event'] = self.stop_threads  


        if not self.spustenie_flask:
            app.add_url_rule('/receive_data', 'receive_data', receive_data, methods=['POST'])
            print("Flask server is running...")

        # Použiť samostatné vlákno pre server Flaskr
        self.flask_thread = Thread(target=self.flask_server.serve_forever)
        self.flask_thread.daemon = True  # Umožnenie programu ukončiť, aj keď toto vlákno stále beží
        self.flask_thread.start()


   
    def on_closing(self):
        try:
            self.stop_threads = True
            self.spustenie_flask = True
            print (self.spustenie_flask)
            # Zastavenie server Flask
            self.flask_server.shutdown()
            self.flask_server.server_close()

            if self.arduino_window:
                # Zničenie Tkinter oknmo fingerprint
                self.arduino_window.destroy()
                self.arduino_window = None
                
        except Exception as e:
            print(f"Chyba pri zatvarani: {e}")



    
    def get_all_fingerprints(self):
        global volne_id_fingerprint_poslat
        try:
            query = "SELECT fingerprint FROM person_data;"
            cursor.execute(query)
            existing_fingerprints = [row[0] for row in cursor.fetchall()]
            print("Existing Fingerprints:", existing_fingerprints)

            new_fingerprints = [value for value in range(1, 163) if value not in existing_fingerprints]
            print("New Fingerprints:", new_fingerprints)
            volne_id_fingerprint_poslat = new_fingerprints[0] if new_fingerprints else None


            return volne_id_fingerprint_poslat
        
        except Exception as e:
            print(f"Error: {e}")
        finally:
        
            if connection:
                cursor.close()
                connection.close()


    @app.route('/send_fingerprint_data', methods=['GET', 'POST'])

    def send_fingerprint_data():
        global volne_id_fingerprint_poslat
        if request.method == 'POST':
            # Spracovanie POST
            sample_data1 = {"message": "SKUSKA POST"}
            # CHCEME GET
            # Return the received data
            return jsonify(sample_data1)
        elif request.method == 'GET':
            # Handle GET request
            
            #volne_id_fingerprint_poslat = Face_Register().ulozenie_tvare()
            sample_data = { str(volne_id_fingerprint_poslat)}
            return jsonify(volne_id_fingerprint_poslat)

        if __name__ == '__main__':
            app.run(host='0.0.0.0', port=5000)

    

   

    def fingerprint(self):
        # Check if the Toplevel window is already created
        #self.get_all_fingerprints()
        fingerprint_data = None 
        if self.arduino_window is None:
            # Create the Toplevel window
            self.arduino_window = tk.Toplevel(self.okno)
            self.arduino_text = tk.Text(self.arduino_window, height=10, width=50)
            self.arduino_text.pack()

            # Bind the cleanup function to the window close event
            self.arduino_window.protocol("WM_DELETE_WINDOW", self.on_closing)

            # Lift and deiconify the Arduino window
            self.start_flask_server()
            self.arduino_window.lift()
            self.arduino_window.deiconify()
            self.kontrola_existujucich_tvari()

            

    

        
            # Use requests.post for making the HTTP POST request
            response = requests.post("http://localhost:5000/send_fingerprint_data", json=fingerprint_data)

            print("Response status code:", response.status_code)
            print("Response content:", response.content.decode('utf-8'))

            if response.status_code == 200:
                print("Data sent successfully.")
            else:
                print(f"Failed to send data. Server returned status code {response.status_code}")

          




    def GUI_vymazanie_dat(self):
        #  "/data_faces_from_camera/person_x/"...
        folders_rd = os.listdir(self.path_photos_from_camera)
        for i in range(len(folders_rd)):
            shutil.rmtree(self.path_photos_from_camera + folders_rd[i])
        self.label_pocet_tvari_uloz['text'] = "0"
        self.ulozene_tvare_pocet = 0
        self.log_all["text"] = "Fotky boli vymazane!"
        

    def GUI_ziskat_meno_priezvisko(self):
        self.input_meno_char = self.input_meno.get()
        self.input_priezvisko_char = self.input_priezvisko.get()  # meno a priezvisko
        self.vytvorenie_priecinka_fotky()
        self.face_folder_created_flag = True 
        self.label_pocet_tvari_uloz['text'] = str(self.ulozene_tvare_pocet)










    def GUI_info(self):
        

        tk.Label(self.frame_right_info,
                 text="Registracia Tvare",
                 font=self.font_title).grid(row=0, column=0, sticky=tk.W, padx=2, pady=0)

        tk.Label(self.frame_right_info, text="FPS: ").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.label_fps_info.grid(row=1, column=0, sticky=tk.W, padx=35, pady=2)

        tk.Label(self.frame_right_info, text="Pocet ulozenych Tvari: ").grid(row=2, column=0, sticky=tk.W, padx=5, pady=0)
        self.label_pocet_tvari_uloz.grid(row=2, column=0, sticky=tk.W, padx=135, pady=2)

        tk.Label(self.frame_right_info,
                 text="Faces in current frame: ").grid(row=3, column=0,columnspan=3, sticky=tk.W, padx=5, pady=2)
        self.label_tvare_pocet.grid(row=3, column=0, sticky=tk.W, padx=135, pady=2)

        self.label_warning.grid(row=4, column=0, columnspan=3, sticky=tk.W, padx=0, pady=2)

        # Step 1: Clear old data
        tk.Label(self.frame_right_info,
                 font=self.font_step_title,
                 text="Krok 1: Vymazat vsetky fotky").grid(row=4, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        tk.Button(self.frame_right_info,
                  text='Vymazat',
                  command=self.GUI_vymazanie_dat).grid(row=5, column=0, columnspan=3, sticky=tk.W, padx=15, pady=2)

        # Step 2: Input name and create folders for face
        
        
        tk.Label(self.frame_right_info,
                 font=self.font_step_title,
                 text="Krok 2: Zadajte meno a priezvisko").grid(row=7, column=0, columnspan=3, sticky=tk.W, padx=5, pady=5)

        tk.Label(self.frame_right_info, text="Meno").grid(row=8, column=0,columnspan=3, sticky=tk.W, padx=15, pady=0)
        self.input_meno = tk.Entry(self.frame_right_info)
        self.input_meno.grid(row=8, column=0, sticky=tk.W, padx=70, pady=2)

        tk.Label(self.frame_right_info, text="Priezvisko:").grid(row=9, column=0,columnspan=3, sticky=tk.W, padx=15, pady=0)
        self.input_priezvisko = tk.Entry(self.frame_right_info)
        self.input_priezvisko.grid(row=9, column=0, sticky=tk.W, padx=70, pady=2)

        tk.Button(self.frame_right_info,
                  text='Vlozit',
                  command=self.GUI_ziskat_meno_priezvisko).grid(row=10, column=0,columnspan=3,sticky=tk.W, padx=15, pady=0)

        # Step 3: Save current face in frame
        tk.Label(self.frame_right_info,
                 font=self.font_step_title,
                 text="Krok 3: Ulozenie obrazku").grid(row=11, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)

        tk.Button(self.frame_right_info,
                  text='Ulozit',
                  command=self.ulozenie_tvare).grid(row=12, column=0, columnspan=2, sticky=tk.W, padx=15, pady=0)



        tk.Label(self.frame_right_info,
                 font=self.font_step_title,
                 text="Krok 4: FingerPrint").grid(row=13, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)


        tk.Button(self.frame_right_info,
                  text='FINGERPRINT',
                  command=self.fingerprint).grid(row=14, column=0, columnspan=2, sticky=tk.W, padx=15, pady=0)
        # Show log in GUI
        self.log_all.grid(row=15, column=0, columnspan=20, sticky=tk.W, padx=5, pady=20)

        self.frame_right_info.pack()

        

    # Mkdir for saving photos and csv
    def ukladanie_fotiek_mkdir(self):
        # ytvorte priečinky na ukladanie obrázkov a fingerprint
        if os.path.isdir(self.path_photos_from_camera):
            pass
        else:
            os.mkdir(self.path_photos_from_camera)








    # Start from person_x+1
    def kontrola_existujucich_tvari(self):
        global volne_id_fingerprint_poslat
        if os.listdir("data/data_faces_from_camera/"):
            # Get the order of latest person
            person_list = os.listdir("data/data_faces_from_camera/")
            person_num_list = []
            for person in person_list:
                person_order = person.split('_')[1].split('_')[0]
                person_num_list.append(int(person_order))
            self.ulozene_tvare_pocet = max(person_num_list)
            #volne_id_fingerprint_poslat=max(person_num_list)


        # Start from person_1
        else:
            self.ulozene_tvare_pocet = 0

    # Update FPS of Video stream
    def update_fps(self):
        now = time.time()
        #  Refresh fps per second
        if str(self.start_time).split(".")[0] != str(now).split(".")[0]:
            self.fps_show = self.fps
        self.start_time = now
        self.frame_time = now - self.frame_start_time
        self.fps = 1.0 / self.frame_time
        self.frame_start_time = now

        self.label_fps_info["text"] = str(self.fps.__round__(2))

    def vytvorenie_priecinka_fotky(self):
        # Create the folders for saving faces with both name and surname
        self.ulozene_tvare_pocet += 1
        if self.input_meno_char:
            if self.input_priezvisko_char:
                self.current_face_dir = self.path_photos_from_camera + \
                                        "person_" + str(self.ulozene_tvare_pocet) + "_" + \
                                        self.input_meno_char + "_" + self.input_priezvisko_char
            else:
                self.current_face_dir = self.path_photos_from_camera + \
                                        "person_" + str(self.ulozene_tvare_pocet) + "_" + \
                                        self.input_meno_char
        else:
            self.current_face_dir = self.path_photos_from_camera + \
                                    "person_" + str(self.ulozene_tvare_pocet)
        os.makedirs(self.current_face_dir)
        self.log_all["text"] = "\"" + self.current_face_dir + "/\" created!"
        logging.info("\n%-40s %s", "Create folders:", self.current_face_dir)

    def ulozenie_tvare(self):
        if self.face_folder_created_flag:
            if self.current_frame_tvari_pocet == 1:
                if not self.out_of_range_flag:
                    self.ss_pocet += 1
                    #  Create blank image according to the size of face detected
                    self.face_ROI_image = np.zeros((int(self.face_ROI_height * 2), self.face_ROI_width * 2, 3),
                                                   np.uint8)
                    for ii in range(self.face_ROI_height * 2):
                        for jj in range(self.face_ROI_width * 2):
                            self.face_ROI_image[ii][jj] = self.current_frame[self.face_ROI_height_start - self.hh + ii][
                                self.face_ROI_width_start - self.ww + jj]
                    self.log_all["text"] = "\"" + self.current_face_dir + "/img_face_" + str(
                        self.ss_pocet) + ".jpg\"" + " saved!"
                    self.face_ROI_image = cv2.cvtColor(self.face_ROI_image, cv2.COLOR_BGR2RGB)

                    cv2.imwrite(self.current_face_dir + "/img_face_" + str(self.ss_pocet) + ".jpg", self.face_ROI_image)
                    logging.info("%-40s %s/img_face_%s.jpg", "Save into：",
                                 str(self.current_face_dir), str(self.ss_pocet) + ".jpg")
                else:
                    self.log_all["text"] = "Please do not out of range!"
            else:
                self.log_all["text"] = "No face in current frame!"
        else:
            self.log_all["text"] = "Please run step 2!"

    def get_frame(self):
        try:
            if self.stream.isOpened():
                ret, frame = self.stream.read()
            
                #print(self.stream.read())
                
                frame = cv2.resize(frame, (640,480))
                return ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        except:
            print("Error: No video input!!!")

    #  Main process of face detection and saving
    def process(self):
        ret, self.current_frame = self.get_frame()
        faces = detektor(self.current_frame, 0)
        # Get frame
        if ret:
            self.update_fps()
            self.label_tvare_pocet["text"] = str(len(faces))
            #  Face detected
            if len(faces) != 0:
                #   Show the ROI of faces
                for k, d in enumerate(faces):
                    self.face_ROI_width_start = d.left()
                    self.face_ROI_height_start = d.top()
                    #  Compute the size of rectangle box
                    self.face_ROI_height = (d.bottom() - d.top())
                    self.face_ROI_width = (d.right() - d.left())
                    self.hh = int(self.face_ROI_height / 2)
                    self.ww = int(self.face_ROI_width / 2)

                    # If the size of ROI > 480x640
                    if (d.right() + self.ww) > 640 or (d.bottom() + self.hh > 480) or (d.left() - self.ww < 0) or (
                            d.top() - self.hh < 0):
                        self.label_warning["text"] = "OUT OF RANGE"
                        self.label_warning['fg'] = 'red'
                        self.out_of_range_flag = True
                        color_rectangle = (255, 0, 0)
                    else:
                        self.out_of_range_flag = False
                        self.label_warning["text"] = ""
                        color_rectangle = (255, 255, 255)
                    self.current_frame = cv2.rectangle(self.current_frame,
                                                       tuple([d.left() - self.ww, d.top() - self.hh]),
                                                       tuple([d.right() + self.ww, d.bottom() + self.hh]),
                                                       color_rectangle, 2)
            self.current_frame_tvari_pocet = len(faces)

            # Convert PIL.Image.Image to PIL.Image.PhotoImage
            img_Image = Image.fromarray(self.current_frame)
            img_PhotoImage = ImageTk.PhotoImage(image=img_Image)
            self.label.img_tk = img_PhotoImage
            self.label.configure(image=img_PhotoImage)

        # Refresh frame
        self.okno.after(5, self.process)

    def run(self):
        self.ukladanie_fotiek_mkdir()
        self.kontrola_existujucich_tvari()
        self.GUI_info()
        self.get_all_fingerprints()
        # Start the Tkinter main loop
        self.process()
        self.okno.mainloop()
        



def main():
    logging.basicConfig(level=logging.INFO)
    Face_Register_con = Face_Register()
    Face_Register_con.run()


if __name__ == '__main__':
    main()
