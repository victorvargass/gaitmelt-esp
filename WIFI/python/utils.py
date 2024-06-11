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
        task_name,
        local_udp_ip,
        shared_port,
        num_esps,
        esp_indexes,
        esp_ips,
        struct_format,
        output_folder,
        csv_filename,
        time_between_vibrations,
        thy,
        vd,
        motor_power,
        min_duration_between_heels,
    ):
        self.task_name = task_name
        self.local_udp_ip = local_udp_ip
        self.shared_port = shared_port
        self.num_esps = num_esps
        self.esp_indexes = esp_indexes
        self.esp_ips = esp_ips
        self.struct_format = struct_format
        self.output_folder = output_folder
        self.csv_filename = csv_filename
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.thy = thy
        self.vd = vd
        self.motor_power = motor_power
        self.max_time_sync_diff = 8  # Máxima diferencia de tiempo permitida (8 ms)
        self.time_between_vibrations = time_between_vibrations

        # Estado de grabación
        self.recording = False
        self.recorded_data = []
        self.start_time = None
        self.mark_times_1 = []
        self.mark_times_2 = []
        self.buffers = [[] for _ in range(num_esps)]
        self.sock = self.setup_socket(local_udp_ip, shared_port)

        # Variables caminata
        self.esp_steps = []  # Lista de indices para saber que esp tocó talon
        self.last_heel_ts = 0  # TS del ultimo talon
        self.diff_heel_time = 0  # Diferencia de tiempo entre ultimos talones
        self.last_vibration_ts = 0  # TS de la última vibración
        self.min_duration_between_heels = (
            min_duration_between_heels  # Duracion minima entre talones
        )

    def setup_socket(self, local_ip, shared_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((local_ip, shared_port))
        return sock

    def analyze_event(self, esp_id, data):
        accState = self.get_acc_state(data)
        acc_y = data[2]
        current_ts = time.time()

        if self.task_name == "salto":
            if (
                accState == "Boton hacia abajo"
                and ((acc_y - 9.8) > self.thy)
                and current_ts - self.last_vibration_ts > self.time_between_vibrations
            ):
                print(
                    f"Salto {len(self.mark_times_1)}",
                    "time diff",
                    current_ts - self.last_vibration_ts,
                    "acc_y",
                    (acc_y - 9.8),
                )
                print("------------------------------------------")
                self.mark_times_1.append(data[7])
                self.activate_selected_motors([1, 2])
                self.last_vibration_ts = current_ts

        elif self.task_name == "caminata":
            # Activacion vibracion
            if (
                self.diff_heel_time >= self.min_duration_between_heels
                and self.last_heel_ts != 0
                and current_ts - self.last_vibration_ts > self.time_between_vibrations
                and len(self.esp_steps) >= 1
            ):
                print(
                    "Demoró mucho, activar motor",
                    "diff_heel_time",
                    self.diff_heel_time,
                    "diff vibration",
                    current_ts - self.last_vibration_ts,
                )
                self.last_vibration_ts = current_ts
                if self.esp_steps[-1] == 1:
                    self.activate_selected_motors([2])
                if self.esp_steps[-1] == 2:
                    self.activate_selected_motors([1])
            # Detección talon
            if (
                accState == "Boton hacia abajo"
                and (acc_y - 9.8) > self.thy
                and current_ts - self.last_heel_ts > self.time_between_vibrations
            ):
                print("Talón ", esp_id)
                # Primer paso
                if len(self.esp_steps) == 0:
                    self.esp_steps.append(esp_id)
                    if self.esp_steps[0] == 1:
                        print("First step izq")
                    else:
                        print("First step der")
                    self.last_heel_ts = current_ts
                # Segundo paso en adelante
                else:
                    # Si el pie es distinto al que ya detectó
                    if self.esp_steps[-1] != esp_id:
                        print("Pie distinto")
                        self.esp_steps.append(esp_id)
                        self.last_heel_ts = current_ts
                    # Si el pie es el mismo (error deteccion)
                    else:
                        print("Mismo pie seguido, reiniciando")
                        print(accState, (acc_y - 9.8) > self.thy, self.diff_heel_time)
                        print("------------------------------------------")
                        self.esp_steps = []
                        self.diff_heel_time = 0
                print("diff_heel_time", self.diff_heel_time)
                print("acc_y", (acc_y - 9.8))
                print("------------------------------------------")
            self.diff_heel_time = current_ts - self.last_heel_ts

        elif self.task_name == "parkinson":
            if (
                esp_id in [3, 4]  # Sensores 3 y 4
                and accState == "Boton hacia abajo"
                and ((acc_y - 9.8) > self.thy)
                # and current_ts - self.last_vibration_esp_ts[esp_id]
                and current_ts - self.last_vibration_ts > self.time_between_vibrations
            ):
                print(
                    "time diff",
                    # current_ts - self.last_vibration_esp_ts[esp_id],
                    current_ts - self.last_vibration_ts,
                    "acc_y",
                    (acc_y - 9.8),
                )
                print("------------------------------------------")
                if (
                    esp_id == 3
                    # and current_ts - self.last_vibration_esp_ts[4]
                    and current_ts - self.last_vibration_ts
                    > self.time_between_vibrations
                ):
                    self.mark_times_1.append(data[7])
                    self.activate_selected_motors([1, 4])
                elif (
                    esp_id == 4
                    # and current_ts - self.last_vibration_esp_ts[3]
                    and current_ts - self.last_vibration_ts
                    > self.time_between_vibrations
                ):
                    self.mark_times_2.append(data[7])
                    self.activate_selected_motors([2, 3])
                self.last_vibration_ts = current_ts
                # self.last_vibration_esp_ts[esp_id] = current_ts
                print(
                    f"ESP3: {len(self.mark_times_1)} - ESP4: {len(self.mark_times_2)} - Talon ESP: {esp_id}"
                )
        else:
            print(self.task_name)
            print("Tarea desconocida")

    def update_thy(self, new_thy):
        self.thy = float(new_thy)

    def update_vd(self, new_vd):
        self.vd = int(new_vd)
        self.set_selected_motors_vibration_time()

    def update_motor_power(self, new_motor_power):
        self.motor_power = int(new_motor_power)
        self.set_selected_motors_motor_power()

    def save_data_to_csv(self):
        with open(self.output_folder + self.csv_filename, "w", newline="") as csvfile:
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

    def save_plot_marks(self, csv_filename, mark_times_1=None, mark_times_2=None):
        prename = self.output_folder + csv_filename.split(".")[0]
        data = {"mark_times_1": mark_times_1, "mark_times_2": mark_times_2}
        with open(prename + "_mark_times.json", "w") as archivo:
            json.dump(data, archivo)

    def get_acc_state(self, data):
        xz_margin_degrees = 50
        yz_margin_degrees = 50
        sensor_state = ""

        x = data[1]
        y = data[2]
        z = data[3]

        xz_orientation_degrees = math.atan(y / math.sqrt(x * x + z * z)) * (
            180.0 / math.pi
        )
        yz_orientation_degrees = math.atan(x / math.sqrt(y * y + z * z)) * (
            180.0 / math.pi
        )

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

    def get_first_and_last_ts(self, csv_filename):
        df = pd.read_csv(self.output_folder + csv_filename)
        first_ts = df["ts_1"].iloc[0]
        last_ts = df["ts_1"].iloc[-1]
        return first_ts, last_ts

    def clean_and_rename_csv(self):
        df = pd.read_csv(self.output_folder + self.csv_filename, delimiter=",")
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
        first_ts, last_ts = self.get_first_and_last_ts(self.csv_filename)
        filename = f"{self.task_name}_{first_ts}_{last_ts}.csv"
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
                    f"Acc X: {round(data[esp_id - 1][1], 3)}\n"
                    f"Acc Y: {round(data[esp_id - 1][2], 3)}\n"
                    f"Acc Z: {round(data[esp_id - 1][3], 3)}\n"
                    f"Gyr X: {round(data[esp_id - 1][4], 3)}\n"
                    f"Gyr Y: {round(data[esp_id - 1][5], 3)}\n"
                    f"Gyr Z: {round(data[esp_id - 1][6], 3)}\n"
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
        self.mark_times_1 = []
        self.mark_times_2 = []
        self.buffers = [[] for _ in range(self.num_esps)]
        self.esp_steps = []
        self.last_heel_ts = 0
        self.diff_heel_time = 0
        self.last_vibration_ts = 0

    def init_recording(self, record_button):
        self.save_data_to_csv()
        final_csv_filename = self.clean_and_rename_csv()
        self.plot_data(final_csv_filename, self.mark_times_1, self.mark_times_2)
        self.save_plot_marks(final_csv_filename, self.mark_times_1, self.mark_times_2)
        self.reinitialize_gaitmelt_variables()
        os.remove(self.output_folder + self.csv_filename)
        record_button.config(text="Start Recording", bg="green", fg="white")

    def stop_recording(self, record_button):
        self.start_time = None
        self.recorded_data = []
        record_button.config(text="Parar grabación", bg="red", fg="white")

    def toggle_recording(self, record_button):
        self.recording = not self.recording
        if self.recording:
            self.stop_recording(record_button)
        else:
            self.init_recording(record_button)

    def send_esp_message(self, IP, message):
        try:
            self.sock.sendto(message.encode(), (IP, self.shared_port))
        except Exception as e:
            print(f"Error sending message {message} to {IP}: {e}")

    def sync_devices(self):
        self.set_selected_motors_vibration_time()
        self.set_selected_motors_motor_power()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.send_esp_message, self.esp_ips[esp], "reset")
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)

    def activate_selected_motors(self, selected_esp_indexes):
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.send_esp_message, self.esp_ips[esp], "motor")
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
            if mark_times_1:
                for time_point in mark_times_1:
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
