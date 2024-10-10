import pandas as pd
import matplotlib.pyplot as plt
import csv
import math
import struct
import concurrent.futures
import time
import os
import socket
import json


class GaitMelt:
    def __init__(
        self,
        local_udp_ip,
        shared_port,
        num_esps,
        esp_indexes,
        esp_ips,
        struct_format,
        output_folder,
        output_filename,
        motor_power,
    ):
        self.local_udp_ip = local_udp_ip
        self.shared_port = shared_port
        self.num_esps = num_esps
        self.esp_indexes = esp_indexes
        self.esp_ips = esp_ips
        self.struct_format = struct_format
        self.output_folder = output_folder
        self.output_filename = output_filename
        self.motor_power = motor_power
        self.max_time_sync_diff = 8  # Máxima diferencia de tiempo permitida (8 ms)

        # Estado de grabación
        self.recording = False
        self.recorded_data = []
        self.start_time = None
        self.buffers = [[] for _ in range(num_esps)]
        #self.sock = self.setup_socket(local_udp_ip, shared_port)

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
            elapsed_time = time.time() - self.start_time

            for esp_id in self.esp_indexes:
                if data[esp_id - 1] is not None:
                    self.buffers[esp_id - 1].append(data[esp_id - 1])

            while all(self.buffers):
                tss = [self.buffers[esp_id - 1][0][7] for esp_id in self.esp_indexes]
                min_ts = min(tss)
                max_ts = max(tss)

                if max_ts - min_ts <= self.max_time_sync_diff:
                    record_entry = [elapsed_time]
                    for esp_id in self.esp_indexes:
                        synchronized_data = self.buffers[esp_id - 1].pop(0)
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

    def receive_data(self, data_queue, esp_data):
        while True:
            data, _ = self.sock.recvfrom(1024)
            if len(data) == struct.calcsize(self.struct_format):
                mpu_readings = struct.unpack(self.struct_format, data)
                esp_id = mpu_readings[0]
                esp_data[esp_id - 1] = mpu_readings
                data_queue.put(esp_data.copy())

    def update_gui(self, data_queue, label_texts, root):
        while True:
            if not data_queue.empty():
                data = data_queue.get()
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
        self.buffers = [[] for _ in range(self.num_esps)]

    def init_recording(self, record_button):
        self.save_data_to_csv()
        final_csv_filename = self.clean_and_rename_csv()
        self.plot_data(final_csv_filename)
        self.reinitialize_gaitmelt_variables()
        os.remove(self.output_folder + "recorded_data.csv")
        record_button.config(text="Start Recording", bg="green", fg="white")

    def stop_recording(self, record_button):
        self.start_time = None
        self.recorded_data = []
        record_button.config(text="Detener registro", bg="red", fg="white")

    def toggle_recording(self, record_button, vibration):
        self.sync_devices()
        self.recording = not self.recording
        if self.recording:
            self.stop_recording(record_button)
            if vibration:
                self.stop_selected_motors(self.esp_indexes)
        else:
            self.init_recording(record_button)
            if vibration:
                self.activate_selected_motors(self.esp_indexes)

    def send_esp_message(self, IP, message):
        try:
            self.sock.sendto(message.encode(), (IP, self.shared_port))
        except Exception as e:
            print(f"Error sending message {message} to {IP}: {e}")

    def sync_devices(self):
        self.set_selected_motors_motor_power()
        self.reinitialize_gaitmelt_variables()
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

    def plot_data(self, csv_filename):
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
            axs[1, 0].set_ylim(acc_y_lims)

            axs[0, 1].plot(df["ts_1"], df["acc_x_2"], label="x", color=accSetColors[0])
            axs[0, 1].plot(df["ts_1"], df["acc_y_2"], label="y", color=accSetColors[1])
            axs[0, 1].plot(df["ts_1"], df["acc_z_2"], label="z", color=accSetColors[2])
            axs[0, 1].set_title(f"{sensor_titles[1]}")
            axs[0, 1].set_ylabel("Aceleración")
            axs[0, 1].legend(loc="lower left")
            axs[0, 1].set_ylim(acc_y_lims)
            axs[0, 1].axhline(y=self.thy, color="green", linestyle="--", linewidth=1)
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
