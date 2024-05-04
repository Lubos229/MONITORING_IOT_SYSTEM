
import os
import dlib
import csv
import numpy as np
import logging
import cv2
import psycopg2



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


# Vytvorenie tabulky person_data
create_person_data_table_query= '''
CREATE TABLE  IF NOT EXISTS person_data (
    id SERIAL PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50)NOT NULL,
    features NUMERIC[] UNIQUE,
    fingerprint INTEGER UNIQUE
);
'''

# Vytvorenie tabulky dochadzka
create_table_query = '''
CREATE TABLE IF NOT EXISTS dochadzka (
    id SERIAL PRIMARY KEY,
    employee_id INT REFERENCES person_data(id) NOT NULL,
    attendance_date DATE,
    arrival_time TIME,
    departure_time TIME,
    time_difference NUMERIC
);
'''

cursor.execute(create_person_data_table_query)
cursor.execute(create_table_query)

connection.commit()










#  Cesta ku obrazkom
path_images_from_camera = "data/data_faces_from_camera/"

#  Pouzitie face detectora  Dlib
detector = dlib.get_frontal_face_detector()

#  face landmarks
predictor = dlib.shape_predictor('data/data_dlib/shape_predictor_68_face_landmarks.dat')

#  Pouzitie Dlib resnet50 modelu na 128D face descriptor
face_reco_model = dlib.face_recognition_model_v1("data/data_dlib/dlib_face_recognition_resnet_model_v1.dat")


def insert_person_data(primary_key, first_name, last_name, features, fingerprint):
    # Prevedenie the NumPy array to a Python list
    features_list = features.tolist() if features is not None else None


    # Skontrolovat, či už existuje záznam s rovnakým ID
    cursor.execute("SELECT id FROM person_data WHERE id = %s", (primary_key,))
    exististujuca_hodnota = cursor.fetchone()

    if not exististujuca_hodnota:
        # If the record doesn't exist, insert it
        if fingerprint is not None:
            insert_riadok = "INSERT INTO person_data (id, first_name, last_name, features, fingerprint) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(insert_riadok, (primary_key, first_name, last_name, features_list, fingerprint))
            
        
        else:
            insert_riadok = "INSERT INTO person_data (id, first_name, last_name, features, fingerprint) VALUES (%s, %s, %s, %s, %s)"
            cursor.execute(insert_riadok, (primary_key, first_name, last_name, features_list, None))

    else:
            insert_riadok = "INSERT INTO person_data (id, first_name, last_name, features) VALUES (%s, %s, %s, %s)"
            cursor.execute(insert_riadok, (primary_key, first_name, last_name, features_list))

    connection.commit()
    
def oddelenie_primary_key_firstname_lastname(file_name):
    parts = file_name.split("_")
    if len(parts) == 4 and parts[0] == "person":
        primary_key, firstname, lastname = parts[1], parts[2], parts[3]
    else:
        primary_key, firstname, lastname = None, None, None
    return primary_key, firstname, lastname



#  Vrati vektor 128D pre jeden obrázok

def return_128d_vektor(path_img):
    img_rd = cv2.imread(path_img)
    
    if img_rd is None:
        logging.warning("Could not read image: %s", path_img)
        return None

    tvare = detector(img_rd, 1)

    logging.info("%-40s %-20s", "Obrazok s rozpoznanymi tvarami", path_img)

    if len(tvare) != 0:
        shape = predictor(img_rd, tvare[0])
        face_descriptor = face_reco_model.compute_face_descriptor(img_rd, shape)
    else:
        face_descriptor = None
        logging.warning("Nerozpoznala sa ziadna tvar")
    return face_descriptor

# Vrati strednu hodnotu 128D deskriptora tvare pre osobu X
def return_stredna_hodnota_vektora(path_face_personX):
    vektor_list_osoby = []
    fotky_vektor = os.listdir(path_face_personX)
    if fotky_vektor:
        for photo in fotky_vektor:
            logging.info("%-40s %-20s", "Reading obrazok:", path_face_personX + "/" + photo)
            vektor_128d = return_128d_vektor(path_face_personX + "/" + photo)
            if vektor_128d is not None:
                vektor_list_osoby.append(vektor_128d)

    if vektor_list_osoby:
        features_mean_personX = np.array(vektor_list_osoby).mean(axis=0)
    else:
        features_mean_personX = None
    return features_mean_personX


def main():
    logging.basicConfig(level=logging.INFO)
    person_list = os.listdir("data/data_faces_from_camera/")
    person_list.sort()

    for person in person_list:
        primary_key, firstname, lastname = oddelenie_primary_key_firstname_lastname(person)
        
        # skontrolovat, či existuje záznam s rovnakým primárnym kľúčom
        cursor.execute("SELECT id FROM person_data WHERE id = %s", (primary_key,))
        exististujuca_hodnota = cursor.fetchone()

        if exististujuca_hodnota:
            print(f"Zaznam s id {primary_key} uz existuje. Preskakujem image processing.")
            continue
        
        

        logging.info("%sperson_%s", path_images_from_camera, person)
        features_mean_personX = return_stredna_hodnota_vektora(path_images_from_camera + person)


        fingerprint_file_path = os.path.join(path_images_from_camera, person, "ziskanyfingerprint.txt")
        fingerprint_value = read_fingerprint_value(fingerprint_file_path)

            # Vlozenie person data do databazy s fingerprint
        insert_person_data(primary_key, firstname, lastname, features_mean_personX, fingerprint_value)


        # Vlozenie person data do databaz



def read_fingerprint_value(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            fingerprint_value = int(file.read().strip())
        return fingerprint_value
    else:
        return None



if __name__ == '__main__':
    main()
    # Close the database connection after processing
    cursor.close()
    connection.close()