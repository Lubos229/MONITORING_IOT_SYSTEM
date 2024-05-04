import dlib
import numpy as np
import cv2
import os
import shutil
import time
import logging
import tkinter as tk
from tkinter import font as tkFont
from PIL import Image, ImageTk
from tkinter import PhotoImage
from threading import Thread, Event
import threading
from flask import Flask, request, jsonify
from werkzeug.serving import make_server
import requests
import psycopg2
from queue import Queue
from tkinter import ttk
from tkinter.ttk import Treeview


# Database connection settings
db_settings = {
    'user': '',
    'password': '',
    'host': '',
    'port': '',
    'database': ''
}

connection = psycopg2.connect(**db_settings)
cursor = connection.cursor()


app = Flask(__name__)

fingerprint_id: int
fingerprint_id = 0
podmienka = False

class FingerprintDeleteGUI:
    def __init__(self, root):

        self.root = root
        self.root.title("Fingerprint Operations")
        self.spustenie_flask = False
        self.data_queue = Queue()
        self.stop_threads = False
        self.flask_thread = None
        self.arduino_window = None

        # GUI components
        self.label_instruction = tk.Label(root, text="Napis ID:")
        self.entry_id = tk.Entry(root)
        self.button_delete = tk.Button(root, text="Vymazanie odtlacku AR", command=self.start_flask_server)
        self.button_view = tk.Button(root, text="Zobrazenie databazy", command=self.view_all_fingerprints)
        self.label_odpoved = tk.Label(root, text="")
        self.label_arduino_text = tk.Label(root, text="Prosim napiste ID ktore chcete vymazat a vyberte moznost")
        self.button_delete_row = tk.Button(root, text="Vymazanie riadku z databazy podla ID", command=self.delete_row)

        # Bind the Enter key to the enter_fingerprint method
        self.root.bind("<Return>", lambda event: self.spustame())

        # GUI layout
        self.label_instruction.grid(row=0, column=0, pady=10)
        self.entry_id.grid(row=0, column=1, pady=10)
        self.button_delete.grid(row=1, column=1, pady=10)
        self.button_view.grid(row=1, column=2, pady=10)
        self.button_delete_row.grid(row=1, column=0, pady=10)
        self.label_odpoved.grid(row=2, column=0, columnspan=5, pady=10)
        self.label_arduino_text.grid(row=3, column=0, columnspan=5, pady=10)



    @app.route('/send_fingerprint', methods=['GET', 'POST'])
    def send_fingerprint_vymazanie():
        global fingerprint_id
        if request.method == 'POST':
            sample_data1 = {"message": "SKUSKA POST"}
            # CHCEME GET
            # Return the received data
            return jsonify(sample_data1)
        elif request.method == 'GET':
            # Handle GET request
            pomocna = str(fingerprint_id)

            return jsonify(pomocna)
        if __name__ == '__main__':
            app.run(host='0.0.0.0', port=5000)




    def spustame(self):
        global fingerprint_id
        fingerprint_id = self.entry_id.get()
        print(fingerprint_id)
        

        response = requests.get("http://localhost:5000/send_fingerprint", json=fingerprint_id)


        print("Response status code:", response.status_code)
        print("Response content:", response.content.decode('utf-8'))

        if response.status_code == 200:
            print("Data sent successfully.")
        else:
            print(f"Failed to send data. Server returned status code {response.status_code}")

    



    def view_all_fingerprints(self):
        # zobrazenie databazy
        all_fingerprints_data = self.fetch_all_fingerprints_data()

        # zobrazit ich v novom okne
        self.show_all_fingerprints_details(all_fingerprints_data)

    def delete_from_database(self, fingerprint_id):
        try:
            dochadzka_query = "DELETE FROM dochadzka WHERE employee_id = %s;"
            cursor.execute(dochadzka_query, (fingerprint_id,))
            
            # najprv dochadzka, ptm person_data
            person_data_query = "DELETE FROM person_data WHERE id = %s;"
            cursor.execute(person_data_query, (fingerprint_id,))

            connection.commit()
            return "Uspesne odstranene z databazy."
        except Exception as e:
            return f"Chyba pri odstraneni z databazy: {e}"

    def delete_row(self):
        fingerprint_id = self.entry_id.get()
        if fingerprint_id:
            # Vymazanie riadky podla ID
            db_response = self.delete_from_database(fingerprint_id)
            self.label_odpoved["text"] = f"Database odpoved: {db_response}"
        else:
            self.label_odpoved["text"] = "Ak chcete odstranit, zadajte ID"

    def send_delete_request(self, arduino_url, fingerprint_id):
        try:
            response = requests.post(arduino_url, data={"fingerprint_id": fingerprint_id})
            arduino_text = response.text  # Odpoved arduino 
            return response.text, arduino_text
        except Exception as e:
            return f"Error: {e}", ""

    def fetch_all_fingerprints_data(self):
        try:
            query = "SELECT * FROM person_data;"
            cursor.execute(query)
            all_fingerprints_data = cursor.fetchall()
            return all_fingerprints_data
        except Exception as e:
            return f"Error fetching all fingerprints data: {e}"

    def show_all_fingerprints_details(self, all_fingerprints_data):
        details_window = tk.Toplevel(self.root)
        details_window.title("All Fingerprints Details")

        # tree view na vytvorenie tabulky
        columns = ("ID", "First Name", "Last Name", "Features", "Fingerprint ID")
        tree = ttk.Treeview(details_window, columns=columns, show="headings")

        for col in columns:
            tree.heading(col, text=col)

        # vlozit data 
        for fingerprint_data in all_fingerprints_data:
            tree.insert("", "end", values=fingerprint_data)

        tree.pack(expand=True, fill="both")
        self.label_odpoved["text"] = ""  




    def start_flask_server(self):
        global podmienka
        if podmienka == False:
            def receive_data():
                try:
                    prijate_data = request.form.get('data')
                    print(f"Received data: {prijate_data}")

                    # vlozit data do queqe
                    self.data_queue.put(prijate_data)
                    return "Success"
                except Exception as e:
                    print(f"Error processing data: {e}")
                    return "Error"

            flask_server = make_server('0.0.0.0', 5000, app)
            app.config['stop_flask_event'] = self.stop_threads  

            if not self.spustenie_flask:
                app.add_url_rule('/input_data', 'input_data', receive_data, methods=['POST'])
                print("Flask server bezi...")
                

            # vlakno na vytvorenie FLASK
            self.flask_thread = Thread(target=flask_server.serve_forever)
            self.flask_thread.daemon = True
            self.flask_thread.start()
            self.spustame()
            # Update Tkinter labelsv hlavon vlakne
            self.root.after(1000, self.update_labels)
            podmienka = True

        else:
            self.spustame()

            
        
        #self.root.after(1000, self.update_labels)

        
    def update_labels(self):
        # pozriet ci je nieco v queue
        if not self.data_queue.empty():
            # Ziskat data z queue a updateovat labely
            arduino_data = self.data_queue.get()
            self.label_arduino_text["text"] = f"Text from Arduino: {arduino_data}"

        # Schedule the update_labels method to be called after 1000 milliseconds (1 second)
        self.root.after(1000, self.update_labels)

   

    def on_closing(self):
        try:
            self.stop_threads = True
            self.spustenie_flask = True
            print(self.spustenie_flask)
            # zýastavanie flask servera
            self.flask_server.shutdown()
            self.flask_server.server_close()

            if self.arduino_window:
                #zrusenie tk inter window
                self.arduino_window.destroy()
                self.arduino_window = None

        except Exception as e:
            print(f"Error on closing: {e}")



def main():
    root = tk.Tk()
    app = FingerprintDeleteGUI(root)
    root.mainloop()

if __name__ == '__main__':
    main()
