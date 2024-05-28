import tkinter as tk
import socket
import struct
import threading
import queue
import csv
import time
import pandas as pd
import math

# Configuración
LOCAL_UDP_IP = "192.168.1.14"
ESP_IPS = ["192.168.1.18", "192.168.1.19", "192.168.1.20", "192.168.1.21"]
SHARED_UDP_PORT = 4210
NUM_ESPS = 4
MAX_TIME_DIFF = 10  # Máxima diferencia de tiempo permitida (10 ms)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LOCAL_UDP_IP, SHARED_UDP_PORT))

struct_format = "i fff fff Q"

# Variables para la grabación de datos
recording = False
recorded_data = []
start_time = None
buffers = [[] for _ in range(NUM_ESPS)]


def get_ACC_state(data):
    xz_margin_degrees = 50
    yz_margin_degrees = 50
    sensor_state = ""

    x = data[1]
    y = data[2]
    z = data[3]

    xz_orientation_degrees = math.atan(y / math.sqrt(x * x + z * z)) * (180.0 / math.pi)
    yz_orientation_degrees = math.atan(x / math.sqrt(y * y + z * z)) * (180.0 / math.pi)

    if (
        abs(xz_orientation_degrees - 0) <= xz_margin_degrees
        and abs(yz_orientation_degrees - (-90)) <= yz_margin_degrees
    ):
        sensor_state = "Base"
    elif (
        abs(xz_orientation_degrees - 90) <= xz_margin_degrees
        and abs(yz_orientation_degrees - 0) <= yz_margin_degrees
    ):
        sensor_state = "Boton hacia abajo"
    else:
        sensor_state = "En movimiento o no definida"

    return sensor_state


def analyze_event(esp_id, data):
    yxDiff = abs(data[2] - data[1])
    yzDiff = abs(data[2] - data[3])
    accState = get_ACC_state(data)
    acc_z = data[2]

    if (esp_id in [2, 3] and accState == "Boton hacia abajo" and
            (8 <= yxDiff <= 15) and (7 <= yzDiff <= 10) and
            ((acc_z - 9.8) < -2 or (acc_z - 9.8) > 8)):
        print(data)
        print(f"Talón ESP {esp_id + 1}")

        if esp_id == 2:
            # Enviar señal para activar el motor
            send_control_signal(0, "1")  # '1' para activar el motor
            send_control_signal(3, "1")
        elif esp_id == 3:
            # Enviar señal para activar el motor
            send_control_signal(1, "1")  # '1' para activar el motor
            send_control_signal(2, "1")



def send_control_signal(esp_id, message):
    if 0 <= esp_id < len(ESP_IPS):
        esp_ip = ESP_IPS[esp_id]
        try:
            sock.sendto(message.encode(), (esp_ip, SHARED_UDP_PORT))
            print(f"Activar motor ESP {esp_id+1}")
        except Exception as e:
            print(f"Error enviando señal al ESP {esp_id+1}: {e}")


# Función para actualizar los datos en la interfaz gráfica
def update_data(data):
    global start_time
    if recording:
        if start_time is None:
            start_time = time.time()
        elapsed_time = time.time() - start_time

        for i in range(NUM_ESPS):
            if data[i] is not None:
                buffers[i].append(data[i])

        # Intentar sincronizar los datos dentro del margen de tiempo permitido
        while all(buffers):
            timestamps = [buffers[i][0][7] for i in range(NUM_ESPS)]
            min_timestamp = min(timestamps)
            max_timestamp = max(timestamps)

            if max_timestamp - min_timestamp <= MAX_TIME_DIFF:
                record_entry = [elapsed_time]
                for i in range(NUM_ESPS):
                    synchronized_data = buffers[i].pop(0)
                    record_entry.extend(
                        [
                            synchronized_data[7],
                            synchronized_data[1],
                            synchronized_data[2],
                            synchronized_data[3],
                            synchronized_data[4],
                            synchronized_data[5],
                            synchronized_data[6],
                        ]
                    )
                    # Verificar si se cumple cierta condición para el ESP en particular (por ejemplo, eje Y del acc)
                    analyze_event(i, synchronized_data)
                recorded_data.append(record_entry)
            else:
                # Si la diferencia de tiempo es mayor al margen, eliminar el dato más antiguo
                oldest_index = timestamps.index(min_timestamp)
                buffers[oldest_index].pop(0)

    for i in range(NUM_ESPS):
        if data[i] is not None:
            board_id = data[i][0]
            label_texts[i].set(
                f"Board ID: {board_id}\n"
                f"Acc X: {round(data[i][1], 3)}\n"
                f"Acc Y: {round(data[i][2], 3)}\n"
                f"Acc Z: {round(data[i][3], 3)}\n"
                f"Gyr X: {round(data[i][4], 3)}\n"
                f"Gyr Y: {round(data[i][5], 3)}\n"
                f"Gyr Z: {round(data[i][6], 3)}\n"
                f"Timestamp: {data[i][7]}"
            )
        else:
            label_texts[i].set(f"Board {i+1} no conectada")


# Función para recibir y procesar los datos de los ESP
def receive_data():
    while True:
        data, _ = sock.recvfrom(1024)
        if len(data) == struct.calcsize(struct_format):
            mpu_readings = struct.unpack(struct_format, data)
            esp_id = mpu_readings[0]
            esp_data[esp_id - 1] = mpu_readings
            data_queue.put(esp_data.copy())


# Función para actualizar la interfaz gráfica
def update_gui():
    while True:
        if not data_queue.empty():
            data = data_queue.get()
            root.after(0, update_data, data)


# Función para iniciar/detener la grabación de datos
def toggle_recording():
    global recording, recorded_data, start_time
    recording = not recording
    if recording:
        start_time = None
        recorded_data = []
        record_button.config(text="Stop Recording", bg="red", fg="white")
    else:
        save_data_to_csv()
        record_button.config(text="Start Recording", bg="green", fg="white")
        clean_data()


def get_first_and_last_timestamp(csv_filename):
    df = pd.read_csv(csv_filename)
    first_timestamp = df["timestamp_1"].iloc[0]
    last_timestamp = df["timestamp_1"].iloc[-1]
    return first_timestamp, last_timestamp


def clean_data():
    csv_filename = "recorded_data.csv"
    df = pd.read_csv(csv_filename, delimiter=",")
    for column in ["timestamp_1", "timestamp_2", "timestamp_3", "timestamp_4"]:
        df = df.drop_duplicates(subset=[column])
    df.insert(0, "index", range(len(df)))
    first_timestamp, last_timestamp = get_first_and_last_timestamp(csv_filename)
    df.to_csv(f"{first_timestamp}_{last_timestamp}.csv", index=False)


def save_data_to_csv():
    with open("recorded_data.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        header = ["elapsed_time"]
        for i in range(1, NUM_ESPS + 1):
            header.extend(
                [
                    f"timestamp_{i}",
                    f"acc_x_{i}",
                    f"acc_y_{i}",
                    f"acc_z_{i}",
                    f"gyr_x_{i}",
                    f"gyr_y_{i}",
                    f"gyr_z_{i}",
                ]
            )
        csvwriter.writerow(header)
        csvwriter.writerows(recorded_data)


# Configurar la interfaz gráfica
root = tk.Tk()
root.geometry("1600x900")
root.option_add("*Font", "Helvetica 20")

label_texts = [tk.StringVar() for _ in range(NUM_ESPS)]
for i, text in enumerate(label_texts):
    text.set(f"Board {i+1} no conectada")

panels = [
    tk.Label(
        root,
        textvariable=text,
        padx=10,
        pady=10,
        borderwidth=2,
        relief="solid",
        width=75,
        height=20,
    )
    for text in label_texts
]

for i, panel in enumerate(panels):
    if i < 2:
        panel.grid(row=0, column=i, padx=10, pady=10, sticky="nsew")
    else:
        panel.grid(row=1, column=i - 2, padx=10, pady=10, sticky="nsew")

for i in range(2):
    root.grid_rowconfigure(i, weight=1)
    root.grid_columnconfigure(i, weight=1)

record_button = tk.Button(
    root, text="Start Recording", command=toggle_recording, bg="green", fg="white"
)
record_button.grid(row=2, column=0, columnspan=2, pady=20)

esp_data = [None] * NUM_ESPS
data_queue = queue.Queue()

receive_thread = threading.Thread(target=receive_data)
receive_thread.daemon = True
receive_thread.start()

update_thread = threading.Thread(target=update_gui)
update_thread.daemon = True
update_thread.start()

root.mainloop()
