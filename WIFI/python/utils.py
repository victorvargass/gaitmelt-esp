import pandas as pd
import matplotlib.pyplot as plt
import csv
import struct
import concurrent.futures
import time
import os
import socket
import json
import queue


class VibracionContinua:
    def __init__(
        self,
        local_udp_ip,
        shared_port,
        esp_ips,
        struct_format,
        output_folder,
        output_filename,
        motor_power,
    ):
        self.local_udp_ip = local_udp_ip
        self.shared_port = shared_port
        self.num_esps = 4
        self.esp_indexes = [1, 2, 3, 4]
        self.esp_ips = esp_ips
        self.struct_format = struct_format
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.output_folder = output_folder
        self.output_filename = output_filename
        self.motor_power = motor_power
        self.max_time_sync_diff = 8  # Máxima diferencia de tiempo permitida (8 ms)
        self.vibration_duration = 3600000 # tiempo maximo de vibracion

        # Estado de grabación
        self.recording = False
        self.recorded_data = []
        self.start_time = None
        self.buffers = [[] for _ in range(self.num_esps)]
        self.sock = self.setup_socket(local_udp_ip, shared_port)

        self.data_queue = queue.Queue()
        self.esp_data = [None] * self.num_esps

    def clear_data_queue(self):
        self.data_queue = queue.Queue()

    def setup_socket(self, local_ip, shared_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((local_ip, shared_port))
        return sock

    def save_data_to_csv(self):
        with open(self.output_folder + "recorded_data.csv", "w", newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            header = ["elapsed_time"]
            for i in self.esp_indexes:
                header.extend(
                    [
                        f"ts_{i}",
                        f"acc_x_{i}",
                        f"acc_y_{i}",
                        f"acc_z_{i}",
                        f"gyr_x_{i}",
                        f"gyr_y_{i}",
                        f"gyr_z_{i}",
                    ]
                )
            csvwriter.writerow(header)
            csvwriter.writerows(self.recorded_data)

    def clean_and_rename_csv(self):
        df = pd.read_csv(self.output_folder + "recorded_data.csv", delimiter=",")
        ts_columns = [
            "ts_1",
            "ts_2",
            "ts_3",
            "ts_4",
        ]
        for column in ts_columns:
            df = df.drop_duplicates(subset=[column])
        
        df.insert(0, "index", range(len(df)))

        min_values = {}
        df_cortado = df.copy()
        
        for columna in ts_columns:
            indice_minimo = df_cortado[columna].idxmin()
            df_cortado = df.loc[indice_minimo:]

        for columna in ts_columns:
            valor_minimo = df_cortado[columna].min()
            min_values[columna] = valor_minimo

        diferencia = 5
        dataframes_filtrados = []
        maximo_total = max(min_values.values())

        for n in range(1, 5):
            umbral = maximo_total - diferencia
            columnas_sensor = [
                f"ts_{n}", 
                f"acc_x_{n}", 
                f"acc_y_{n}", 
                f"acc_z_{n}", 
                f"gyr_x_{n}", 
                f"gyr_y_{n}", 
                f"gyr_z_{n}"
            ]
            df_filtrado = df_cortado[df_cortado[f"ts_{n}"] >= umbral][columnas_sensor]
            dataframes_filtrados.append(df_filtrado)

        min_length = min(len(df) for df in dataframes_filtrados)
        dataframes_recortados = [df.iloc[:min_length].reset_index(drop=True) for df in dataframes_filtrados]

        resultado_final = pd.concat(dataframes_recortados, axis=1)

        filename = f"{self.output_filename}.csv"
        resultado_final.to_csv(self.output_folder + "/" + filename, index=False)
        
        return filename

    def update_data(self, data, label_texts):
        if self.recording:
            if self.start_time is None:
                self.start_time = time.time()
                self.clear_data_queue()
                self.buffers = [[] for _ in range(self.num_esps)]
            elapsed_time = time.time() - self.start_time

            for esp_id in self.esp_indexes:
                if data[esp_id - 1] is not None:
                    self.buffers[esp_id - 1].append(data[esp_id - 1])

            while all(self.buffers):
                tss = [self.buffers[esp_id - 1][-1][9] for esp_id in self.esp_indexes]
                min_ts = min(tss)
                max_ts = max(tss)
                if max_ts - min_ts <= self.max_time_sync_diff:
                    record_entry = [elapsed_time]
                    for esp_id in self.esp_indexes:
                        synchronized_data = self.buffers[esp_id - 1].pop(0)
                        record_entry.extend(
                            [
                                synchronized_data[9],
                                synchronized_data[1],
                                synchronized_data[2],
                                synchronized_data[3],
                                synchronized_data[4],
                                synchronized_data[5],
                                synchronized_data[6],
                                synchronized_data[7],
                                synchronized_data[8],
                            ]
                        )
                        self.analyze_event(esp_id, synchronized_data)
                    self.recorded_data.append(record_entry)
                else:
                    oldest_index = tss.index(min_ts)
                    self.buffers[oldest_index].pop(0)

        for esp_id in self.esp_indexes:
            if data[esp_id - 1] is not None:
                board_id = data[esp_id - 1][0]
                label_texts[esp_id - 1].set(
                    f"Board ID: {board_id}\n"
                    f"  Acc      Gyr\n"
                    f"X  {round(data[esp_id - 1][1], 2):<7}   {round(data[esp_id - 1][4], 2):<7}\n"
                    f"Y  {round(data[esp_id - 1][2], 2):<7}   {round(data[esp_id - 1][5], 2):<7}\n"
                    f"Z  {round(data[esp_id - 1][3], 2):<7}   {round(data[esp_id - 1][6], 2):<7}\n"
                    f"Timestamp: {data[esp_id - 1][7]}"
                )
            else:
                label_texts[esp_id - 1].set(f"Board {esp_id} no conectada")

    def receive_data(self):
        while True:
            data, _ = self.sock.recvfrom(1024)
            if len(data) == struct.calcsize(self.struct_format):
                readings = struct.unpack(self.struct_format, data)
                esp_id = readings[0]
                self.esp_data[esp_id - 1] = readings
                self.data_queue.put(self.esp_data.copy())

    def update_gui(self, label_texts, root):
        while True:
            if not self.data_queue.empty():
                data = self.data_queue.get()
                root.after(
                    0,
                    self.update_data,
                    data,
                    label_texts,
                )

    def stop_recording(self, record_button, vibration):
        self.save_data_to_csv()
        final_csv_filename = self.clean_and_rename_csv()
        self.plot_acc_data(final_csv_filename)
        os.remove(self.output_folder + "recorded_data.csv")
        if vibration:
            button_text = "Iniciar registro con vibración"
        else:
            button_text = "Iniciar registro sin vibración"
        record_button.config(text=button_text, bg="green", fg="white")

    def init_recording(self, record_button):
        record_button.config(text="Detener registro", bg="red", fg="white")

    def toggle_recording(self, record_button, vibration):
        self.sync_devices()
        if self.recording:
            if vibration:
                self.stop_selected_motors(self.esp_indexes)
            self.recording = False
            self.stop_recording(record_button, vibration)
        else:
            self.recording = True
            self.init_recording(record_button)
            if vibration:
                self.activate_selected_motors(self.esp_indexes)
        self.start_time = None
        self.recorded_data = []

    def send_esp_message(self, IP, message):
        try:
            self.sock.sendto(message.encode(), (IP, self.shared_port))
        except Exception as e:
            print(f"Error sending message {message} to {IP}: {e}")

    def sync_devices(self):
        self.set_selected_motors_motor_power()
        self.set_selected_motors_vibration_time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.send_esp_message, self.esp_ips[esp], "reset")
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def set_selected_motors_vibration_time(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "duration" + str(self.vibration_duration),
                )
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def activate_selected_motors(self, selected_esp_indexes):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "motor0",
                )
                for esp in selected_esp_indexes
            ]
            concurrent.futures.wait(futures)

    def stop_selected_motors(self, selected_esp_indexes):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "stop",
                )
                for esp in selected_esp_indexes
            ]
            concurrent.futures.wait(futures)

    def set_selected_motors_motor_power(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "power" + str(int(self.motor_power)),
                )
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def update_output_filename(self, event):
        new_output_filename = event.widget.get()
        self.output_filename = new_output_filename


    def plot_acc_data(self, csv_filename):
        # Lee el archivo CSV
        accSetColors = ["red", "blue", "green"]
        gyrSetColors = ["purple", "orange", "pink"]

        acc_y_lims = (-25, 25)
        gyr_y_lims = (-10, 10)

        try:
            df = pd.read_csv(self.output_folder + "/" + csv_filename, sep=",")
        except FileNotFoundError:
            print("Error: Archivo no encontrado.")
            return

        fig, axs = plt.subplots(
            2, 2, figsize=(12, 8), sharex="col", sharey="row"
        )

        sensor_titles = [
            "Sensor 1 - Muslo Izquierdo",
            "Sensor 2 - Muslo Derecho",
            "Sensor 3 - Gemelo Izquierdo",
            "Sensor 4 - Gemelo Derecho",
        ]

        # Plot para acc_data
        axs[0, 0].plot(df["ts_1"], df["acc_x_1"], label="x", color=accSetColors[0])
        axs[0, 0].plot(df["ts_1"], df["acc_y_1"], label="y", color=accSetColors[1])
        axs[0, 0].plot(df["ts_1"], df["acc_z_1"], label="z", color=accSetColors[2])
        axs[0, 0].set_title(f"{sensor_titles[0]}")
        axs[0, 0].set_ylabel("Aceleración")
        axs[0, 0].legend(loc="lower left")
        axs[0, 0].set_ylim(acc_y_lims)

        axs[0, 1].plot(df["ts_1"], df["acc_x_2"], label="x", color=accSetColors[0])
        axs[0, 1].plot(df["ts_1"], df["acc_y_2"], label="y", color=accSetColors[1])
        axs[0, 1].plot(df["ts_1"], df["acc_z_2"], label="z", color=accSetColors[2])
        axs[0, 1].set_title(f"{sensor_titles[1]}")
        axs[0, 1].set_ylabel("Aceleración")
        axs[0, 1].legend(loc="lower left")
        axs[0, 1].set_ylim(acc_y_lims)

        axs[1, 0].plot(df["ts_1"], df["acc_x_3"], label="x", color=accSetColors[0])
        axs[1, 0].plot(df["ts_1"], df["acc_y_3"], label="y", color=accSetColors[1])
        axs[1, 0].plot(df["ts_1"], df["acc_z_3"], label="z", color=accSetColors[2])
        axs[1, 0].set_title(f"{sensor_titles[2]}")
        axs[1, 0].set_ylabel("Aceleración")
        axs[1, 0].legend(loc="lower left")
        axs[1, 0].set_ylim(acc_y_lims)

        axs[1, 1].plot(df["ts_1"], df["acc_x_4"], label="x", color=accSetColors[0])
        axs[1, 1].plot(df["ts_1"], df["acc_y_4"], label="y", color=accSetColors[1])
        axs[1, 1].plot(df["ts_1"], df["acc_z_4"], label="z", color=accSetColors[2])
        axs[1, 1].set_title(f"{sensor_titles[3]}")
        axs[1, 1].set_ylabel("Aceleración")
        axs[1, 1].legend(loc="lower left")
        axs[1, 1].set_ylim(acc_y_lims)

        fig.supxlabel("Tiempo [s]")

        # Ajustar el diseño
        suptitle = csv_filename.split(".")[0]

        plt.suptitle(suptitle)
        plt.tight_layout()
        plt.savefig(
            self.output_folder + "/" + suptitle + ".png"
        )  # Guardar el gráfico como una imagen PNG
        plt.show()

    def plot_data(self, csv_filename):
        # Lee el archivo CSV
        accSetColors = ["red", "blue", "green"]
        gyrSetColors = ["purple", "orange", "pink"]

        acc_y_lims = (-25, 25)
        gyr_y_lims = (-10, 10)

        try:
            df = pd.read_csv(self.output_folder + "/" + csv_filename, sep=",")
        except FileNotFoundError:
            print("Error: Archivo no encontrado.")
            return

        fig, axs = plt.subplots(
            self.num_esps, 2, figsize=(12, 8), sharex="col", sharey="row"
        )

        sensor_titles = [
            "Sensor 1 - Muslo Izquierdo",
            "Sensor 2 - Muslo Derecho",
            "Sensor 3 - Gemelo Izquierdo",
            "Sensor 4 - Gemelo Derecho",
        ]

        # Plot para acc_data
        axs[0, 0].plot(df["ts_1"], df["acc_x_1"], label="x", color=accSetColors[0])
        axs[0, 0].plot(df["ts_1"], df["acc_y_1"], label="y", color=accSetColors[1])
        axs[0, 0].plot(df["ts_1"], df["acc_z_1"], label="z", color=accSetColors[2])
        axs[0, 0].set_title(f"{sensor_titles[0]}")
        axs[0, 0].set_ylabel("Aceleración")
        axs[0, 0].legend(loc="lower left")
        axs[0, 0].set_ylim(acc_y_lims)

        axs[0, 1].plot(df["ts_1"], df["acc_x_2"], label="x", color=accSetColors[0])
        axs[0, 1].plot(df["ts_1"], df["acc_y_2"], label="y", color=accSetColors[1])
        axs[0, 1].plot(df["ts_1"], df["acc_z_2"], label="z", color=accSetColors[2])
        axs[0, 1].set_title(f"{sensor_titles[1]}")
        axs[0, 1].set_ylabel("Aceleración")
        axs[0, 1].legend(loc="lower left")
        axs[0, 1].set_ylim(acc_y_lims)

        axs[1, 0].plot(df["ts_1"], df["acc_x_3"], label="x", color=accSetColors[0])
        axs[1, 0].plot(df["ts_1"], df["acc_y_3"], label="y", color=accSetColors[1])
        axs[1, 0].plot(df["ts_1"], df["acc_z_3"], label="z", color=accSetColors[2])
        axs[1, 0].set_title(f"{sensor_titles[2]}")
        axs[1, 0].set_ylabel("Aceleración")
        axs[1, 0].legend(loc="lower left")
        axs[1, 0].set_ylim(acc_y_lims)

        axs[1, 1].plot(df["ts_1"], df["acc_x_4"], label="x", color=accSetColors[0])
        axs[1, 1].plot(df["ts_1"], df["acc_y_4"], label="y", color=accSetColors[1])
        axs[1, 1].plot(df["ts_1"], df["acc_z_4"], label="z", color=accSetColors[2])
        axs[1, 1].set_title(f"{sensor_titles[3]}")
        axs[1, 1].set_ylabel("Aceleración")
        axs[1, 1].legend(loc="lower left")
        axs[1, 1].set_ylim(acc_y_lims)

        # Plot para gyr_data
        axs[2, 0].plot(df["ts_1"], df["gyr_x_1"], label="x", color=gyrSetColors[0])
        axs[2, 0].plot(df["ts_1"], df["gyr_y_1"], label="y", color=gyrSetColors[1])
        axs[2, 0].plot(df["ts_1"], df["gyr_z_1"], label="z", color=gyrSetColors[2])
        axs[2, 0].set_title(f"{sensor_titles[0]}")
        axs[2, 0].set_ylabel("Giroscopio")
        axs[2, 0].legend(loc="lower left")
        axs[2, 0].set_ylim(gyr_y_lims)

        axs[2, 1].plot(df["ts_1"], df["gyr_x_2"], label="x", color=gyrSetColors[0])
        axs[2, 1].plot(df["ts_1"], df["gyr_y_2"], label="y", color=gyrSetColors[1])
        axs[2, 1].plot(df["ts_1"], df["gyr_z_2"], label="z", color=gyrSetColors[2])
        axs[2, 1].set_title(f"{sensor_titles[1]}")
        axs[2, 1].set_ylabel("Giroscopio")
        axs[2, 1].legend(loc="lower left")
        axs[2, 1].set_ylim(gyr_y_lims)

        axs[3, 0].plot(df["ts_1"], df["gyr_x_3"], label="x", color=gyrSetColors[0])
        axs[3, 0].plot(df["ts_1"], df["gyr_y_3"], label="y", color=gyrSetColors[1])
        axs[3, 0].plot(df["ts_1"], df["gyr_z_3"], label="z", color=gyrSetColors[2])
        axs[3, 0].set_title(f"{sensor_titles[2]}")
        axs[3, 0].set_ylabel("Giroscopio")
        axs[3, 0].legend(loc="lower left")
        axs[3, 0].set_ylim(gyr_y_lims)

        axs[3, 1].plot(df["ts_1"], df["gyr_x_4"], label="x", color=gyrSetColors[0])
        axs[3, 1].plot(df["ts_1"], df["gyr_y_4"], label="y", color=gyrSetColors[1])
        axs[3, 1].plot(df["ts_1"], df["gyr_z_4"], label="z", color=gyrSetColors[2])
        axs[3, 1].set_title(f"{sensor_titles[3]}")
        axs[3, 1].set_ylabel("Giroscopio")
        axs[3, 1].legend(loc="lower left")
        axs[3, 1].set_ylim(gyr_y_lims)

        fig.supxlabel("Tiempo [s]")

        # Ajustar el diseño
        suptitle = csv_filename.split(".")[0]

        plt.suptitle(suptitle)
        plt.tight_layout()
        plt.savefig(
            self.output_folder + "/" + suptitle + ".png"
        )  # Guardar el gráfico como una imagen PNG
        plt.show()



class FSR:
    def __init__(
        self,
        local_udp_ip,
        shared_port,
        esp_ips,
        struct_format,
        output_folder,
        output_filename,
        time_between_vibrations,
        time_between_heel_detection,
        thy,
        vd,
        motor_power,
        min_duration_between_heels,
        vibration_offset,
        reading_mode,
    ):
        self.local_udp_ip = local_udp_ip
        self.shared_port = shared_port
        self.num_esps = 4
        self.esp_indexes = [1, 2, 3, 4]
        self.esp_ips = esp_ips
        self.struct_format = struct_format
        self.output_folder = output_folder
        self.output_filename = output_filename
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.thy = thy
        self.vd = vd
        self.motor_power = motor_power
        self.max_time_sync_diff = 8  # Máxima diferencia de tiempo permitida (8 ms)
        self.time_between_vibrations = time_between_vibrations
        self.time_between_heel_detection = time_between_heel_detection
        self.reading_mode = reading_mode

        # Estado de grabación
        self.recording = False
        self.recorded_data = []
        self.start_time = None
        self.mark_times_1 = []
        self.mark_times_2 = []
        self.vibration_times = [[] for _ in range(self.num_esps)]
        self.buffers = [[] for _ in range(self.num_esps)]
        self.sock = self.setup_socket(local_udp_ip, shared_port)

        # Variables caminata
        self.esp_steps = []  # Lista de indices para saber que esp tocó talon
        self.last_heel_ts = [0 for _ in range(self.num_esps)]  # TS del ultimo talon
        self.diff_heel_time = [
            0 for _ in range(self.num_esps)
        ]  # Diferencia de tiempo entre ultimos talones
        self.last_vibration_ts = [
            0 for _ in range(self.num_esps)
        ]  # TS de la última vibración
        self.min_duration_between_heels = (
            min_duration_between_heels  # Duracion minima entre talones
        )
        self.vibrating = [False for _ in range(self.num_esps)]
        self.last_vibration_esp = 0
        self.vibration_offset = vibration_offset
        self.esp_len_vibration = 0
        self.data_queue = queue.Queue()
        self.esp_data = [None] * self.num_esps
    
    def clear_data_queue(self):
        self.data_queue = queue.Queue()

    def setup_socket(self, local_ip, shared_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((local_ip, shared_port))
        return sock

    def analyze_event(self, esp_id, data):
        fsr_frontal = data[7]
        fsr_trasero = data[8]
        current_ts = time.time()
        #print(esp_id, fsr_frontal, fsr_trasero)
        if (
            esp_id == 1
            and (current_ts - self.last_vibration_ts[0]) * 1000 <= self.vd
            and not self.vibrating[0]
        ):
            self.vibrating[0] = True
            # print("Vibrando...", esp_id)
        if (
            esp_id == 2
            and (current_ts - self.last_vibration_ts[1]) * 1000 <= self.vd
            and not self.vibrating[1]
        ):
            self.vibrating[1] = True
            # print("Vibrando...", esp_id)

        if (
            esp_id == 1
            and (current_ts - self.last_vibration_ts[0]) * 1000 <= self.vd
            and self.vibrating[0]
        ):
            self.vibrating[0] = False
            # print("Dejó de vibrar", esp_id)
        if (
            esp_id == 2
            and (current_ts - self.last_vibration_ts[1]) * 1000 <= self.vd
            and self.vibrating[1]
        ):
            self.vibrating[1] = False
            # print("Dejó de vibrar", esp_id)
        if (
            esp_id in [2, 4] and fsr_frontal > self.thy
        ): 
            if (
                esp_id == 2
                and current_ts - self.last_vibration_ts[1]
                > self.time_between_vibrations
            ):
                print("activar vibracion 2 y 3", fsr_frontal, current_ts - self.last_vibration_ts[1])
                self.last_vibration_ts[1] = current_ts
                #self.mark_times_1.append(data[9])
                #self.activate_selected_motors([2, 3])
            elif (
                esp_id == 4
                and current_ts - self.last_vibration_ts[3]
                > self.time_between_vibrations
            ):
                print("activar vibracion 1 y 4", esp_id, fsr_frontal, current_ts - self.last_vibration_ts[3])
                self.last_vibration_ts[3] = current_ts
                #self.mark_times_2.append(data[9])
                #self.activate_selected_motors([1, 4])

    def update_output_filename(self, event):
        new_output_filename = event.widget.get()
        self.output_filename = new_output_filename

    def update_thy(self, new_thy):
        self.thy = float(new_thy)

    def update_vd(self, new_vd):
        self.vd = int(new_vd)
        self.set_selected_motors_vibration_time()

    def save_data_to_csv(self):
        with open(self.output_folder + "recorded_data.csv", "w", newline="") as csvfile:
            csvwriter = csv.writer(csvfile)
            header = ["elapsed_time"]
            for i in self.esp_indexes:
                header.extend(
                    [
                        f"ts_{i}",
                        f"acc_x_{i}",
                        f"acc_y_{i}",
                        f"acc_z_{i}",
                        f"gyr_x_{i}",
                        f"gyr_y_{i}",
                        f"gyr_z_{i}",
                        f"fsr_frontal_{i}",
                        f"fsr_trasero_{i}",
                    ]
                )
            csvwriter.writerow(header)
            csvwriter.writerows(self.recorded_data)

    def save_plot_marks(self, csv_filename, mark_times_1=None, mark_times_2=None):
        prename = self.output_folder + csv_filename.split(".")[0]
        data = {"mark_times_1": mark_times_1, "mark_times_2": mark_times_2}
        with open(prename + "_mark_times.json", "w") as archivo:
            json.dump(data, archivo)

    def clean_and_rename_csv(self):
        df = pd.read_csv(self.output_folder + "recorded_data.csv", delimiter=",")
        ts_columns = ["ts_1", "ts_2"]
        if self.num_esps == 4:
            ts_columns = [
                "ts_1",
                "ts_2",
                "ts_3",
                "ts_4",
            ]
        for column in ts_columns:
            df = df.drop_duplicates(subset=[column])
        df.insert(0, "index", range(len(df)))
        filename = f"{self.output_filename}.csv"
        df.to_csv(self.output_folder + "/" + filename, index=False)
        return filename

    def update_data(self, data, label_texts):
        if self.recording:
            if self.start_time is None:
                self.start_time = time.time()
                self.clear_data_queue()
                self.buffers = [[] for _ in range(self.num_esps)]
            elapsed_time = time.time() - self.start_time

            for esp_id in self.esp_indexes:
                if data[esp_id - 1] is not None:
                    self.buffers[esp_id - 1].append(data[esp_id - 1])

            while all(self.buffers):
                tss = [self.buffers[esp_id - 1][-1][9] for esp_id in self.esp_indexes]
                min_ts = min(tss)
                max_ts = max(tss)
                if max_ts - min_ts <= self.max_time_sync_diff:
                    record_entry = [elapsed_time]
                    for esp_id in self.esp_indexes:
                        synchronized_data = self.buffers[esp_id - 1].pop(0)
                        record_entry.extend(
                            [
                                synchronized_data[9],
                                synchronized_data[1],
                                synchronized_data[2],
                                synchronized_data[3],
                                synchronized_data[4],
                                synchronized_data[5],
                                synchronized_data[6],
                                synchronized_data[7],
                                synchronized_data[8],
                            ]
                        )
                        self.analyze_event(esp_id, synchronized_data)
                    self.recorded_data.append(record_entry)
                else:
                    oldest_index = tss.index(min_ts)
                    self.buffers[oldest_index].pop(0)

        for esp_id in self.esp_indexes:
            if data[esp_id - 1] is not None:
                board_id = data[esp_id - 1][0]
                if board_id == 1 or board_id == 3:
                    label_texts[esp_id - 1].set(
                        f"Board ID: {board_id}\n"
                        f"  Acc      Gyr\n"
                        f"X  {round(data[esp_id - 1][1], 2):<7}   {round(data[esp_id - 1][4], 2):<7}\n"
                        f"Y  {round(data[esp_id - 1][2], 2):<7}   {round(data[esp_id - 1][5], 2):<7}\n"
                        f"Z  {round(data[esp_id - 1][3], 2):<7}   {round(data[esp_id - 1][6], 2):<7}\n"
                        f"Timestamp: {data[esp_id - 1][9]}"
                    )
                else:
                    label_texts[esp_id - 1].set(
                        f"Board ID: {board_id}\n"
                        f"  Acc      Gyr\n"
                        f"X  {round(data[esp_id - 1][1], 2):<7}   {round(data[esp_id - 1][4], 2):<7}\n"
                        f"Y  {round(data[esp_id - 1][2], 2):<7}   {round(data[esp_id - 1][5], 2):<7}\n"
                        f"Z  {round(data[esp_id - 1][3], 2):<7}   {round(data[esp_id - 1][6], 2):<7}\n"
                        f"FSR Frontal  {round(data[esp_id - 1][7], 2):<7}\n"
                        f"FSR Trasero  {round(data[esp_id - 1][8], 2):<7}\n"
                        f"Timestamp: {data[esp_id - 1][9]}"
                    )
            else:
                label_texts[esp_id - 1].set(f"Board {esp_id} no conectada")
                
    def receive_data(self):
        while True:
            data, _ = self.sock.recvfrom(1024)
            if len(data) == struct.calcsize(self.struct_format):
                readings = struct.unpack(self.struct_format, data)
                esp_id = readings[0]
                self.esp_data[esp_id - 1] = readings
                self.data_queue.put(self.esp_data.copy())

    def update_gui(self, label_texts, root):
        while True:
            if not self.data_queue.empty():
                data = self.data_queue.get()
                root.after(
                    0,
                    self.update_data,
                    data,
                    label_texts,
                )
                
    def reinitialize_gaitmelt_variables(self):
        self.recording = False
        self.recorded_data = []
        self.start_time = None
        self.mark_times_1 = []
        self.mark_times_2 = []
        self.buffers = [[] for _ in range(self.num_esps)]
        self.esp_steps = []
        self.last_heel_ts = [0 for _ in range(self.num_esps)]
        self.diff_heel_time = [0 for _ in range(self.num_esps)]
        self.last_vibration_ts = [0 for _ in range(self.num_esps)]
        self.vibration_times = [[] for _ in range(self.num_esps)]

    def stop_recording(self, record_button):
        self.save_data_to_csv()
        final_csv_filename = self.clean_and_rename_csv()
        self.plot_data(final_csv_filename)
        os.remove(self.output_folder + "recorded_data.csv")
        button_text = "Iniciar registro"
        record_button.config(text=button_text, bg="green", fg="white")

    def init_recording(self, record_button):
        record_button.config(text="Detener registro", bg="red", fg="white")

    def toggle_recording(self, record_button):
        self.sync_devices()
        if self.recording:
            self.stop_selected_motors(self.esp_indexes)
            self.recording = False
            self.stop_recording(record_button)
        else:
            self.recording = True
            self.init_recording(record_button)
        self.start_time = None
        self.recorded_data = []

    def send_esp_message(self, IP, message):
        try:
            self.sock.sendto(message.encode(), (IP, self.shared_port))
        except Exception as e:
            print(f"Error sending message {message} to {IP}: {e}")

    def sync_devices(self):
        self.set_selected_motors_motor_power()
        self.set_selected_motors_vibration_time()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.send_esp_message, self.esp_ips[esp], "reset")
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def activate_selected_motors(self, selected_esp_indexes):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "motor" + str(self.vibration_offset),
                )
                for esp in selected_esp_indexes
            ]
            concurrent.futures.wait(futures)

    def stop_selected_motors(self, selected_esp_indexes):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "stop",
                )
                for esp in selected_esp_indexes
            ]
            concurrent.futures.wait(futures)

    def set_selected_motors_vibration_time(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "duration" + str(self.vd),
                )
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def set_selected_motors_motor_power(self):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    self.send_esp_message,
                    self.esp_ips[esp],
                    "power" + str(int(self.motor_power)),
                )
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def plot_data(self, csv_filename, mark_times_1=None, mark_times_2=None):
        # Lee el archivo CSV
        accSetColors = ["red", "blue", "green"]
        gyrSetColors = ["purple", "orange", "pink"]

        acc_y_lims = (-25, 25)
        gyr_y_lims = (-5, 5)

        try:
            df = pd.read_csv(self.output_folder + "/" + csv_filename, sep=",")
        except FileNotFoundError:
            print("Error: Archivo no encontrado.")
            return

        fig, axs = plt.subplots(
            self.num_esps, 2, figsize=(12, 8), sharex="col", sharey="row"
        )

        if self.num_esps == 4:

            sensor_titles = [
                "Sensor 1 - Muslo Izquierdo",
                "Sensor 2 - Muslo Derecho",
                "Sensor 3 - Gemelo Izquierdo",
                "Sensor 4 - Gemelo Derecho",
            ]

            # Plot para acc_data
            axs[0, 0].plot(df["ts_1"], df["acc_x_1"], label="x", color=accSetColors[0])
            axs[0, 0].plot(df["ts_1"], df["acc_y_1"], label="y", color=accSetColors[1])
            axs[0, 0].plot(df["ts_1"], df["acc_z_1"], label="z", color=accSetColors[2])
            axs[0, 0].set_title(f"{sensor_titles[0]}")
            axs[0, 0].set_ylabel("Aceleración")
            axs[0, 0].legend(loc="lower left")
            axs[0, 0].set_ylim(acc_y_lims)

            axs[0, 1].plot(df["ts_1"], df["acc_x_2"], label="x", color=accSetColors[0])
            axs[0, 1].plot(df["ts_1"], df["acc_y_2"], label="y", color=accSetColors[1])
            axs[0, 1].plot(df["ts_1"], df["acc_z_2"], label="z", color=accSetColors[2])
            axs[0, 1].set_title(f"{sensor_titles[1]}")
            axs[0, 1].set_ylabel("Aceleración")
            axs[0, 1].legend(loc="lower left")
            axs[0, 1].set_ylim(acc_y_lims)

            axs[1, 0].plot(df["ts_1"], df["acc_x_3"], label="x", color=accSetColors[0])
            axs[1, 0].plot(df["ts_1"], df["acc_y_3"], label="y", color=accSetColors[1])
            axs[1, 0].plot(df["ts_1"], df["acc_z_3"], label="z", color=accSetColors[2])
            axs[1, 0].set_title(f"{sensor_titles[2]}")
            axs[1, 0].set_ylabel("Aceleración")
            axs[1, 0].legend(loc="lower left")
            if mark_times_1:
                for time_point in mark_times_1:
                    axs[1, 0].axvline(
                        x=time_point, color="black", linestyle="--", linewidth=1
                    )
            axs[1, 0].set_ylim(acc_y_lims)

            axs[1, 1].plot(df["ts_1"], df["acc_x_4"], label="x", color=accSetColors[0])
            axs[1, 1].plot(df["ts_1"], df["acc_y_4"], label="y", color=accSetColors[1])
            axs[1, 1].plot(df["ts_1"], df["acc_z_4"], label="z", color=accSetColors[2])
            axs[1, 1].set_title(f"{sensor_titles[3]}")
            axs[1, 1].set_ylabel("Aceleración")
            axs[1, 1].legend(loc="lower left")
            if mark_times_2:
                for time_point in mark_times_2:
                    axs[1, 1].axvline(
                        x=time_point, color="black", linestyle="--", linewidth=1
                    )
            axs[1, 1].set_ylim(acc_y_lims)

            # Plot para gyr_data
            axs[2, 0].plot(df["ts_1"], df["gyr_x_1"], label="x", color=gyrSetColors[0])
            axs[2, 0].plot(df["ts_1"], df["gyr_y_1"], label="y", color=gyrSetColors[1])
            axs[2, 0].plot(df["ts_1"], df["gyr_z_1"], label="z", color=gyrSetColors[2])
            axs[2, 0].set_title(f"{sensor_titles[0]}")
            axs[2, 0].set_ylabel("Giroscopio")
            axs[2, 0].legend(loc="lower left")
            axs[2, 0].set_ylim(gyr_y_lims)

            axs[2, 1].plot(df["ts_1"], df["gyr_x_2"], label="x", color=gyrSetColors[0])
            axs[2, 1].plot(df["ts_1"], df["gyr_y_2"], label="y", color=gyrSetColors[1])
            axs[2, 1].plot(df["ts_1"], df["gyr_z_2"], label="z", color=gyrSetColors[2])
            axs[2, 1].set_title(f"{sensor_titles[1]}")
            axs[2, 1].set_ylabel("Giroscopio")
            axs[2, 1].legend(loc="lower left")
            axs[2, 1].set_ylim(gyr_y_lims)

            axs[3, 0].plot(df["ts_1"], df["gyr_x_3"], label="x", color=gyrSetColors[0])
            axs[3, 0].plot(df["ts_1"], df["gyr_y_3"], label="y", color=gyrSetColors[1])
            axs[3, 0].plot(df["ts_1"], df["gyr_z_3"], label="z", color=gyrSetColors[2])
            axs[3, 0].set_title(f"{sensor_titles[2]}")
            axs[3, 0].set_ylabel("Giroscopio")
            axs[3, 0].legend(loc="lower left")
            if mark_times_1:
                for time_point in mark_times_1:
                    axs[3, 0].axvline(
                        x=time_point, color="black", linestyle="--", linewidth=1
                    )
            axs[3, 0].set_ylim(gyr_y_lims)

            axs[3, 1].plot(df["ts_1"], df["gyr_x_4"], label="x", color=gyrSetColors[0])
            axs[3, 1].plot(df["ts_1"], df["gyr_y_4"], label="y", color=gyrSetColors[1])
            axs[3, 1].plot(df["ts_1"], df["gyr_z_4"], label="z", color=gyrSetColors[2])
            axs[3, 1].set_title(f"{sensor_titles[3]}")
            axs[3, 1].set_ylabel("Giroscopio")
            axs[3, 1].legend(loc="lower left")
            if mark_times_2:
                for time_point in mark_times_2:
                    axs[3, 1].axvline(
                        x=time_point, color="black", linestyle="--", linewidth=1
                    )
            axs[3, 1].set_ylim(gyr_y_lims)

        else:
            sensor_titles = [
                "Sensor 1 - Muslo Izquierdo",
                "Sensor 2 - Muslo Derecho",
            ]

            # Plot para acc_data
            axs[0, 0].plot(df["ts_1"], df["acc_x_1"], label="x", color=accSetColors[0])
            axs[0, 0].plot(df["ts_1"], df["acc_y_1"], label="y", color=accSetColors[1])
            axs[0, 0].plot(df["ts_1"], df["acc_z_1"], label="z", color=accSetColors[2])
            axs[0, 0].set_title(f"{sensor_titles[0]}")
            axs[0, 0].set_ylabel("Aceleración")
            axs[0, 0].legend(loc="lower left")
            axs[0, 0].set_ylim(acc_y_lims)
            axs[0, 0].axhline(y=self.thy, color="green", linestyle="--", linewidth=1)
            if mark_times_1:
                for time_point in mark_times_1:
                    axs[0, 0].axvline(
                        x=time_point, color="black", linestyle="--", linewidth=1
                    )
            axs[1, 0].set_ylim(acc_y_lims)

            axs[0, 1].plot(df["ts_1"], df["acc_x_2"], label="x", color=accSetColors[0])
            axs[0, 1].plot(df["ts_1"], df["acc_y_2"], label="y", color=accSetColors[1])
            axs[0, 1].plot(df["ts_1"], df["acc_z_2"], label="z", color=accSetColors[2])
            axs[0, 1].set_title(f"{sensor_titles[1]}")
            axs[0, 1].set_ylabel("Aceleración")
            axs[0, 1].legend(loc="lower left")
            axs[0, 1].set_ylim(acc_y_lims)
            axs[0, 1].axhline(y=self.thy, color="green", linestyle="--", linewidth=1)
            if mark_times_2:
                for time_point in mark_times_2:
                    axs[0, 1].axvline(
                        x=time_point, color="black", linestyle="--", linewidth=1
                    )
            axs[1, 0].set_ylim(acc_y_lims)

            # Plot para gyr_data
            axs[1, 0].plot(df["ts_1"], df["gyr_x_1"], label="x", color=gyrSetColors[0])
            axs[1, 0].plot(df["ts_1"], df["gyr_y_1"], label="y", color=gyrSetColors[1])
            axs[1, 0].plot(df["ts_1"], df["gyr_z_1"], label="z", color=gyrSetColors[2])
            axs[1, 0].set_title(f"{sensor_titles[0]}")
            axs[1, 0].set_ylabel("Giroscopio")
            axs[1, 0].legend(loc="lower left")
            axs[1, 0].set_ylim(gyr_y_lims)

            axs[1, 1].plot(df["ts_1"], df["gyr_x_2"], label="x", color=gyrSetColors[0])
            axs[1, 1].plot(df["ts_1"], df["gyr_y_2"], label="y", color=gyrSetColors[1])
            axs[1, 1].plot(df["ts_1"], df["gyr_z_2"], label="z", color=gyrSetColors[2])
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
            self.output_folder + "/" + suptitle + ".png"
        )  # Guardar el gráfico como una imagen PNG
        plt.show()

    def plot_data_x(self, csv_filename, mark_times_1=None, mark_times_2=None):
        # Lee el archivo CSV
        accSetColors = ["blue"]

        acc_y_lims = (-25, 25)

        try:
            df = pd.read_csv(self.output_folder + "/" + csv_filename, sep=",")
        except FileNotFoundError:
            print("Error: Archivo no encontrado.")
            return

        fig, axs = plt.subplots(
            self.num_esps, 1, figsize=(12, 8), sharex="col", sharey="row"
        )
        sensor_titles = [
            "Sensor 1 - Gemelo Izquierdo",
            "Sensor 2 - Gemelo Derecho",
        ]

        # Plot para acc_data
        axs[0].plot(df["ts_1"], df["acc_x_1"], label="x", color=accSetColors[0])
        axs[0].set_title(f"{sensor_titles[0]}")
        axs[0].set_ylabel("Aceleración")
        axs[0].legend(loc="lower left")
        axs[0].set_ylim(acc_y_lims)
        axs[0].axhline(y=self.thy, color="green", linestyle="--", linewidth=1)
        if mark_times_1:
            for time_point in mark_times_1:
                axs[0].axvline(x=time_point, color="black", linestyle="--", linewidth=1)
        if self.vibration_times[0]:
            for time_point in self.vibration_times[0]:
                axs[0].axvline(x=time_point, color="red", linestyle="-", linewidth=1)

        axs[1].plot(df["ts_1"], df["acc_x_2"], label="x", color=accSetColors[0])
        axs[1].set_title(f"{sensor_titles[1]}")
        axs[1].set_ylabel("Aceleración")
        axs[1].legend(loc="lower left")
        axs[1].set_ylim(acc_y_lims)
        axs[1].axhline(y=self.thy, color="green", linestyle="--", linewidth=1)
        if mark_times_2:
            for time_point in mark_times_2:
                axs[1].axvline(x=time_point, color="black", linestyle="--", linewidth=1)
        if self.vibration_times[1]:
            for time_point in self.vibration_times[1]:
                axs[1].axvline(x=time_point, color="red", linestyle="-", linewidth=1)

        # Plot para gy
        fig.supxlabel("Tiempo [s]")

        # Ajustar el diseño
        suptitle = csv_filename.split(".")[0]

        plt.suptitle(suptitle)
        plt.tight_layout()
        plt.savefig(
            self.output_folder + "/" + suptitle + "_x.png"
        )  # Guardar el gráfico como una imagen PNG
        plt.show()