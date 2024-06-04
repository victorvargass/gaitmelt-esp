import pandas as pd
import matplotlib.pyplot as plt
import math
import csv
import socket
import struct
import time
import concurrent.futures
import os
import numpy as np

# Configuración
LOCAL_UDP_IP = "192.168.50.82"
ESP_IPS = ["192.168.50.11", "192.168.50.12"]

SHARED_UDP_PORT = 4210
NUM_ESPS = 2
MAX_TIME_SYNC_DIFF = 8  # Máxima diferencia de tiempo permitida (10 ms)
VIBRATION_TIME_DIFF = 0.5  # (1500ms)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((LOCAL_UDP_IP, SHARED_UDP_PORT))

struct_format = "i fff fff i"

# Variables para la grabación de datos
recording = False
recorded_data = []
start_time = None
buffers = [[] for _ in range(NUM_ESPS)]

output_folder = "output_data/"
csv_filename = "recorded_data.csv"

heel_times = []
walking_times = []

esp_steps = []
first_step_esp = 0
first_step_time = 0
last_heel_timestamp = 0

diff_heel_time = 0
# Agregar un diccionario para rastrear el tiempo de la última vibración de cada ESP
last_vibration_time = 0
last_heel_time = 0

last_vibration_esp = 0
vibration_time = 100
is_vibrating = False


def send_esp_message(IP, message):
    try:
        sock.sendto(message.encode(), (IP, SHARED_UDP_PORT))
        # print(f"Send {message} to {IP}")
    except Exception as e:
        print(f"Error sending message {message} to {IP}: {e}")


def sync_devices():
    set_selected_motors_vibration_time([0, 1], vibration_time)
    message = "reset"
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(send_esp_message, IP, message) for IP in ESP_IPS]
        concurrent.futures.wait(futures)


def all_motors_on():
    message = "motor"
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [executor.submit(send_esp_message, IP, message) for IP in ESP_IPS]
        concurrent.futures.wait(futures)


def set_vibration_time(esp_id, vibration_time):
    selected_ip = ESP_IPS[esp_id]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(send_esp_message, selected_ip, str(vibration_time))
        concurrent.futures.wait([future])


def set_selected_motors_vibration_time(selected_motors, vibration_time):
    selected_ips = [ESP_IPS[i] for i in selected_motors]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(send_esp_message, IP, str(vibration_time))
            for IP in selected_ips
        ]
        concurrent.futures.wait(futures)


def motor_on(esp_id):
    set_vibration_time(esp_id, vibration_time)
    message = "motor"
    selected_ip = ESP_IPS[esp_id]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(send_esp_message, selected_ip, message)
        concurrent.futures.wait([future])


def activate_selected_motors(selected_motors):
    message = "motor"
    selected_ips = [ESP_IPS[i] for i in selected_motors]
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = [
            executor.submit(send_esp_message, IP, message) for IP in selected_ips
        ]
        concurrent.futures.wait(futures)


def update_thresholds(acc_y_threshold):
    global acc_y_threshold_value
    acc_y_threshold_value = acc_y_threshold


# Configuración de los umbrales iniciales
acc_y_threshold_value = 4


def analyze_event(esp_id, data):
    global last_heel_time, diff_heel_time, last_vibration_time, last_vibration_esp, last_step, first_step_esp, heel_times, esp_steps, first_step_time, walking_times, last_heel_timestamp
    accState = get_acc_state(data)
    acc_y = data[2]
    current_time = time.time()
    if (
        current_time - last_heel_timestamp >= np.mean(walking_times[1:])
        and current_time - last_vibration_time > VIBRATION_TIME_DIFF
        #and esp_steps[-1] != last_vibration_esp
    ):
        print(
            "Demoró mucho, activar motor",
            esp_steps[-2],
            current_time - last_heel_timestamp,
        )
        last_vibration_esp = esp_steps[-2]
        last_vibration_time = current_time
        activate_selected_motors([esp_steps[-2] - 1])

    
    if (
        accState == "Boton hacia abajo"
        and ((acc_y - 9.8) > acc_y_threshold_value)
        and current_time - last_heel_time > VIBRATION_TIME_DIFF
    ):
        print("Pie actual", esp_id + 1)
        esp_steps.append(esp_id + 1)
        if len(esp_steps) == 1:
            first_step_esp = esp_id + 1
            if first_step_esp == 1:
                print("First step izq")
            else:
                print("First step der")
            last_step = first_step_esp
        else:
            if last_step != esp_id + 1:
                last_step = esp_id + 1
                if (
                    len(esp_steps) >= 2
                ):
                    print("Debería contar tiempo")
                    diff_heel_time = current_time - last_heel_timestamp
                    last_heel_timestamp = time.time()
                    walking_times.append(diff_heel_time)
            else:
                print("Mismo pie seguido, reiniciando")
                esp_steps = []
                walking_times = []
        print("diff_heel_time", diff_heel_time)
        print("mean", np.mean(walking_times[1:]))
        print("acc_y", (acc_y - 9.8))
        print("------------------------------------------")
        last_heel_time = current_time


def update_data(data, label_texts):
    global start_time
    if recording:
        if start_time is None:
            start_time = time.time()
        elapsed_time = time.time() - start_time

        for i in range(NUM_ESPS):
            if data[i] is not None:
                buffers[i].append(data[i])

        while all(buffers):
            timestamps = [buffers[i][0][7] for i in range(NUM_ESPS)]
            min_timestamp = min(timestamps)
            max_timestamp = max(timestamps)

            if max_timestamp - min_timestamp <= MAX_TIME_SYNC_DIFF:
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
                    analyze_event(i, synchronized_data)

                recorded_data.append(record_entry)
            else:
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


def receive_data(data_queue, esp_data):
    while True:
        data, _ = sock.recvfrom(1024)
        if len(data) == struct.calcsize(struct_format):
            mpu_readings = struct.unpack(struct_format, data)
            esp_id = mpu_readings[0]
            esp_data[esp_id - 1] = mpu_readings
            data_queue.put(esp_data.copy())


def update_gui(data_queue, label_texts, root):
    while True:
        if not data_queue.empty():
            data = data_queue.get()
            root.after(0, update_data, data, label_texts)


def toggle_recording(record_button):
    global recording, recorded_data, start_time, csv_filename, heel_times
    recording = not recording
    if recording:
        start_time = None
        recorded_data = []
        record_button.config(text="Stop Recording", bg="red", fg="white")
    else:
        save_data_to_csv(output_folder + csv_filename, recorded_data)
        final_csv_filename = clean_and_rename_csv(output_folder + csv_filename)
        plot_data(final_csv_filename, heel_times)
        heel_times = []
        os.remove(output_folder + csv_filename)
        record_button.config(text="Start Recording", bg="green", fg="white")


def plot_data(csv_filename, heel_times=None):
    # Lee el archivo CSV

    accSetColors = ["red", "blue", "green"]
    gyrSetColors = ["purple", "orange", "pink"]

    acc_y_lims = (-25, 25)
    gyr_y_lims = (-5, 5)

    try:
        df = pd.read_csv(output_folder + csv_filename, sep=",")
    except FileNotFoundError:
        print("Error: Archivo no encontrado.")
        return

    fig, axs = plt.subplots(2, 2, figsize=(12, 8), sharex="col", sharey="row")

    sensor_titles = [
        "Sensor 1 - Muslo Izquierdo",
        "Sensor 2 - Muslo Derecho",
    ]

    # Plot para acc_data
    axs[0, 0].plot(df["timestamp_1"], df["acc_x_1"], label="x", color=accSetColors[0])
    axs[0, 0].plot(df["timestamp_1"], df["acc_y_1"], label="y", color=accSetColors[1])
    axs[0, 0].plot(df["timestamp_1"], df["acc_z_1"], label="z", color=accSetColors[2])
    axs[0, 0].set_title(f"{sensor_titles[0]}")
    axs[0, 0].set_ylabel("Aceleración")
    axs[0, 0].legend(loc="lower left")
    axs[0, 0].set_ylim(acc_y_lims)
    if heel_times:
        for time_point in heel_times:
            axs[0, 0].axvline(x=time_point, color="black", linestyle="--", linewidth=1)
    axs[1, 0].set_ylim(acc_y_lims)

    axs[0, 1].plot(df["timestamp_1"], df["acc_x_2"], label="x", color=accSetColors[0])
    axs[0, 1].plot(df["timestamp_1"], df["acc_y_2"], label="y", color=accSetColors[1])
    axs[0, 1].plot(df["timestamp_1"], df["acc_z_2"], label="z", color=accSetColors[2])
    axs[0, 1].set_title(f"{sensor_titles[1]}")
    axs[0, 1].set_ylabel("Aceleración")
    axs[0, 1].legend(loc="lower left")
    axs[0, 1].set_ylim(acc_y_lims)
    if heel_times:
        for time_point in heel_times:
            axs[0, 1].axvline(x=time_point, color="black", linestyle="--", linewidth=1)
    axs[1, 0].set_ylim(acc_y_lims)

    # Plot para gyr_data
    axs[1, 0].plot(df["timestamp_1"], df["gyr_x_1"], label="x", color=gyrSetColors[0])
    axs[1, 0].plot(df["timestamp_1"], df["gyr_y_1"], label="y", color=gyrSetColors[1])
    axs[1, 0].plot(df["timestamp_1"], df["gyr_z_1"], label="z", color=gyrSetColors[2])
    axs[1, 0].set_title(f"{sensor_titles[0]}")
    axs[1, 0].set_ylabel("Giroscopio")
    axs[1, 0].legend(loc="lower left")
    axs[1, 0].set_ylim(gyr_y_lims)

    axs[1, 1].plot(df["timestamp_1"], df["gyr_x_2"], label="x", color=gyrSetColors[0])
    axs[1, 1].plot(df["timestamp_1"], df["gyr_y_2"], label="y", color=gyrSetColors[1])
    axs[1, 1].plot(df["timestamp_1"], df["gyr_z_2"], label="z", color=gyrSetColors[2])
    axs[1, 1].set_title(f"{sensor_titles[1]}")
    axs[1, 1].set_ylabel("Giroscopio")
    axs[1, 1].legend(loc="lower left")
    axs[1, 1].set_ylim(gyr_y_lims)

    fig.supxlabel("Tiempo [s]")

    # Ajustar el diseño
    suptitle = csv_filename.split(".")[0]

    plt.suptitle(suptitle)
    plt.tight_layout()
    plt.savefig(
        output_folder + suptitle + ".png"
    )  # Guardar el gráfico como una imagen PNG
    plt.show()


def get_first_and_last_timestamp(csv_filename):
    df = pd.read_csv(csv_filename)
    first_timestamp = df["timestamp_1"].iloc[0]
    last_timestamp = df["timestamp_1"].iloc[-1]
    return first_timestamp, last_timestamp


def clean_and_rename_csv(csv_filename):
    df = pd.read_csv(csv_filename, delimiter=",")
    for column in ["timestamp_1", "timestamp_2"]:
        df = df.drop_duplicates(subset=[column])
    df.insert(0, "index", range(len(df)))
    first_timestamp, last_timestamp = get_first_and_last_timestamp(csv_filename)
    filename = f"{first_timestamp}_{last_timestamp}.csv"
    df.to_csv(output_folder + filename, index=False)
    return filename


def get_acc_state(data):
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


def save_data_to_csv(csv_filename, recorded_data):
    with open(csv_filename, "w", newline="") as csvfile:
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
