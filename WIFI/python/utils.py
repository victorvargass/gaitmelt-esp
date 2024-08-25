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

class AlternateChange:
    def __init__(
        self,
        local_udp_ip,
        shared_port,
        esp_indexes,
        esp_ips,
        struct_format,
        output_folder,
        output_filename,
        motor_power,
        vibration_cadence
    ):
        self.local_udp_ip = local_udp_ip
        self.shared_port = shared_port
        self.esp_indexes = esp_indexes
        self.esp_ips = esp_ips
        self.struct_format = struct_format
        self.output_folder = output_folder
        self.output_filename = output_filename
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.motor_power = motor_power
        self.vibration_cadence = vibration_cadence
        self.max_time_sync_diff = 8  # Máxima diferencia de tiempo permitida (8 ms)

        # Estado de grabación
        self.alternate_vibrating = False
        self.start_time = None
        self.recorded_data = []
        self.buffers = [[] for _ in range(4)]
        self.last_vibration_ts = [0 for _ in range(4)]
        self.vibrating = [False for _ in range(4)]
        self.first_vibration = True
        self.sock = self.setup_socket(local_udp_ip, shared_port)
        self.vibration_offset = 0

        self.vd = 10

    def setup_socket(self, local_ip, shared_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((local_ip, shared_port))
        return sock

    def update_output_filename(self, event):
        new_output_filename = event.widget.get()
        self.output_filename = new_output_filename

    def update_vc(self, new_vc):
        self.vibration_cadence = int(new_vc)
        new_vd = self.vibration_cadence * 0.5
        self.update_vd(new_vd)
        self.first_vibration = True
        self.last_vibration_ts = [0 for _ in range(4)]
        self.vibrating = [False for _ in range(4)]
        print(f"Cadencia cambiada a {self.vibration_cadence} ms y tiempo motor cambiado a {new_vd} ms")
        
    def update_vd(self, new_vd):
        self.vd = int(new_vd)
        self.set_selected_motors_vibration_time()

    def update_motor_power(self, new_motor_power):
        self.motor_power = int(new_motor_power)
        self.set_selected_motors_motor_power()

    def alternate_vibrate(self, esp_id, root):
        current_ts = time.time()
        if (
            esp_id == 1
            and (current_ts - self.last_vibration_ts[0]) * 1000 <= self.vd
            and self.vibrating[0]
        ):
            self.vibrating[0] = True
            
            #print("Vibrando... 1 y 4", current_ts)
        if (
            esp_id == 2
            and (current_ts - self.last_vibration_ts[1]) * 1000 <= self.vd
            and self.vibrating[1]
        ):
            self.vibrating[1] = True
            #print("Vibrando... 2 y 3", current_ts)
        if (
            esp_id == 1
            and (current_ts - self.last_vibration_ts[0]) * 1000 > self.vd
            and self.vibrating[0]
        ):
            self.vibrating[0] = False
            root.panels["panel_0"].config(bg="white")
            root.panels["panel_3"].config(bg="white")
            #print("Dejó de vibrar... 1 y 4", current_ts)
        if (
            esp_id == 2
            and (current_ts - self.last_vibration_ts[1]) * 1000 > self.vd
            and self.vibrating[1]
        ):
            self.vibrating[1] = False
            root.panels["panel_1"].config(bg="white")
            root.panels["panel_2"].config(bg="white")
            #print("Dejó de vibrar... 2 y 3", current_ts)

        if esp_id == 1 and self.last_vibration_ts[0] == 0 and self.first_vibration:  # primera vibracion
            self.last_vibration_ts[0] = current_ts
            self.last_vibration_ts[1] = current_ts - (self.vibration_cadence / 1000)
            print("Primera vibracion 1 y 4", current_ts)
            self.vibrating[0] = True
            self.first_vibration = False
            root.panels["panel_0"].config(bg="green")
            root.panels["panel_3"].config(bg="green")
            #self.activate_selected_motors([1, 4])

        else:
            if (
                esp_id == 1
                and self.last_vibration_ts[0] != 0
                and not self.vibrating[0]
                and not self.first_vibration
                and (current_ts - self.last_vibration_ts[0]) * 1000 > self.vibration_cadence * 2
            ):
                print("Vibracion 1 y 4", current_ts)
                self.last_vibration_ts[0] = current_ts
                self.vibrating[0] = True
                root.panels["panel_0"].config(bg="green")
                root.panels["panel_3"].config(bg="green")
                #self.activate_selected_motors([1, 4])

            if (
                esp_id == 2
                and self.last_vibration_ts[1] != 0
                and not self.vibrating[1]
                and not self.first_vibration
                and (current_ts - self.last_vibration_ts[1]) * 1000 > self.vibration_cadence * 2
            ):
                print("Vibracion 2 y 3", current_ts)
                self.last_vibration_ts[1] = current_ts
                self.vibrating[1] = True
                root.panels["panel_1"].config(bg="green")
                root.panels["panel_2"].config(bg="green")
                #self.activate_selected_motors([2, 3])

    def update_data(self, data, label_texts, root):
        if self.alternate_vibrating:
            if self.start_time is None:
                self.start_time = time.time()
            elapsed_time = time.time() - self.start_time

            for esp_id in self.esp_indexes:
                if data[esp_id - 1] is not None:
                    self.buffers[esp_id - 1].append(data[esp_id - 1])

            while all(self.buffers):
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
                    self.alternate_vibrate(esp_id, root)
                self.recorded_data.append(record_entry)

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
                    root,
                )

    def reinitialize_gaitmelt_variables(self):
        self.start_time = None
        self.recorded_data = []
        self.buffers = [[] for _ in range(4)]
        self.last_vibration_ts = [0 for _ in range(4)]
        self.vibrating = [False for _ in range(4)]
        self.first_vibration = True

    def stop_alternate_vibration(self, init_button):
        #self.save_data_to_csv()
        #final_csv_filename = self.clean_and_rename_csv()
        #self.plot_data(final_csv_filename)
        #self.plot_data_x(final_csv_filename)
        #os.remove(self.output_folder + "recorded_data.csv")
        self.reinitialize_gaitmelt_variables()

        init_button.config(text="Iniciar", bg="green", fg="white")

    def init_alternate_vibration(self, init_button):
        self.reinitialize_gaitmelt_variables()
        init_button.config(text="Detener", bg="red", fg="white")

    def toggle_alternative_vibration(self, init_button):
        if self.alternate_vibrating:
            print("stop")
            self.stop_alternate_vibration(init_button)
            self.alternate_vibrating = False
        else:
            print("sync and init")
            self.sync_devices()
            self.init_alternate_vibration(init_button)
            self.alternate_vibrating = True

    def sync_devices(self):
        self.set_selected_motors_vibration_time()
        self.set_selected_motors_motor_power()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(self.send_esp_message, self.esp_ips[esp], "reset")
                for esp in self.esp_indexes
            ]
            concurrent.futures.wait(futures)
    
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
        filename = f"{self.output_filename}.csv"
        df.to_csv(self.output_folder + "/" + filename, index=False)
        return filename
    
    def send_esp_message(self, IP, message):
        try:
            self.sock.sendto(message.encode(), (IP, self.shared_port))
        except Exception as e:
            print(f"Error sending message {message} to {IP}: {e}")

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
            4, 2, figsize=(12, 8), sharex="col", sharey="row"
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
        self.num_esps = num_esps
        self.esp_indexes = esp_indexes
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
        self.vibration_times = [[] for _ in range(num_esps)]
        self.buffers = [[] for _ in range(num_esps)]
        #self.sock = self.setup_socket(local_udp_ip, shared_port)

        # Variables caminata
        self.esp_steps = []  # Lista de indices para saber que esp tocó talon
        self.last_heel_ts = [0 for _ in range(num_esps)]  # TS del ultimo talon
        self.diff_heel_time = [
            0 for _ in range(num_esps)
        ]  # Diferencia de tiempo entre ultimos talones
        self.last_vibration_ts = [
            0 for _ in range(num_esps)
        ]  # TS de la última vibración
        self.min_duration_between_heels = (
            min_duration_between_heels  # Duracion minima entre talones
        )
        self.vibrating = [False for _ in range(num_esps)]
        self.last_vibration_esp = 0
        self.vibration_offset = vibration_offset
        self.esp_len_vibration = 0

    def setup_socket(self, local_ip, shared_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((local_ip, shared_port))
        return sock

    def analyze_event(self, esp_id, data):
        accState = self.get_acc_state(data, esp_id)
        current_ts = time.time()
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
            esp_id in [3, 4]  # Sensores 3 y 4
            and accState == "Boton hacia abajo"
            # and current_ts - self.last_vibration_esp_ts[esp_id]
            and current_ts - self.last_vibration_ts > self.time_between_vibrations
        ):
            print(
                "time diff",
                # current_ts - self.last_vibration_esp_ts[esp_id],
                current_ts - self.last_vibration_ts,
            )
            print("------------------------------------------")
            if (
                esp_id == 3
                # and current_ts - self.last_vibration_esp_ts[4]
                and current_ts - self.last_vibration_ts
                > self.time_between_vibrations
                and not self.reading_mode
            ):
                self.mark_times_1.append(data[7])
                self.activate_selected_motors([1, 4])
            elif (
                esp_id == 4
                # and current_ts - self.last_vibration_esp_ts[3]
                and current_ts - self.last_vibration_ts
                > self.time_between_vibrations
                and not self.reading_mode
            ):
                self.mark_times_2.append(data[7])
                self.activate_selected_motors([2, 3])
            self.last_vibration_ts = current_ts
            # self.last_vibration_esp_ts[esp_id] = current_ts
            print(
                f"ESP3: {len(self.mark_times_1)} - ESP4: {len(self.mark_times_2)} - Talon ESP: {esp_id}"
            )

    def update_reading_mode(self):
        self.reading_mode = not self.reading_mode
        
    def update_output_filename(self, event):
        new_output_filename = event.widget.get()
        self.output_filename = new_output_filename

    def update_thy(self, new_thy):
        self.thy = float(new_thy)

    def update_vd(self, new_vd):
        self.vd = int(new_vd)
        self.set_selected_motors_vibration_time()

    def update_motor_power(self, new_motor_power):
        self.motor_power = int(new_motor_power)
        self.set_selected_motors_motor_power()

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

    def save_plot_marks(self, csv_filename, mark_times_1=None, mark_times_2=None):
        prename = self.output_folder + csv_filename.split(".")[0]
        data = {"mark_times_1": mark_times_1, "mark_times_2": mark_times_2}
        with open(prename + "_mark_times.json", "w") as archivo:
            json.dump(data, archivo)

    def get_acc_state(self, data, esp_id):
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
        self.last_heel_ts = [0 for _ in range(self.num_esps)]
        self.diff_heel_time = [0 for _ in range(self.num_esps)]
        self.last_vibration_ts = [0 for _ in range(self.num_esps)]
        self.vibration_times = [[] for _ in range(self.num_esps)]

    def init_recording(self, record_button):
        self.save_data_to_csv()
        final_csv_filename = self.clean_and_rename_csv()
        # self.plot_data(final_csv_filename, self.mark_times_1, self.mark_times_2)
        self.plot_data_x(final_csv_filename, self.mark_times_1, self.mark_times_2)
        self.save_plot_marks(final_csv_filename, self.mark_times_1, self.mark_times_2)
        self.reinitialize_gaitmelt_variables()
        os.remove(self.output_folder + "recorded_data.csv")
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
                    "motor" + str(self.vibration_offset),
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
