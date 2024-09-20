import struct
import concurrent.futures
import time
import socket

class GaitMelt:
    def __init__(
        self,
        local_udp_ip,
        shared_port,
        num_esps,
        esp_indexes,
        esp_ips,
        struct_format,
        time_between_vibrations,
        time_between_heel_detection,
        vd,
        motor_power,
        vibration_offset,
    ):
        self.local_udp_ip = local_udp_ip
        self.shared_port = shared_port
        self.num_esps = num_esps
        self.esp_indexes = esp_indexes
        self.esp_ips = esp_ips
        self.struct_format = struct_format
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.vd = vd
        self.motor_power = motor_power
        self.max_time_sync_diff = 8  # Máxima diferencia de tiempo permitida (8 ms)
        self.time_between_vibrations = time_between_vibrations
        self.time_between_heel_detection = time_between_heel_detection

        # Estado de grabación
        #self.sock = self.setup_socket(local_udp_ip, shared_port)

        # Diferencia de tiempo entre ultimos talones
        self.last_vibration_ts = [
            0 for _ in range(num_esps)
        ]

        self.vibrating = [False for _ in range(num_esps)]
        self.last_vibration_esp = 0
        self.vibration_offset = vibration_offset

    def setup_socket(self, local_ip, shared_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((local_ip, shared_port))
        return sock

    def analyze_event(self, esp_id, data, root):
        palpador = data[1]
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


        if (
            esp_id == 3
            and palpador == 1
            and current_ts - self.last_vibration_ts
            > self.time_between_vibrations
        ):
            print("Talón 3")
            self.activate_selected_motors([1, 4])
        elif (
            esp_id == 4
            and palpador == 1
            and current_ts - self.last_vibration_ts
            > self.time_between_vibrations
        ):
            print("Talón 4")
            self.activate_selected_motors([2, 3])
        self.last_vibration_ts = current_ts

        
    def update_vd(self, new_vd):
        self.vd = int(new_vd)
        self.set_selected_motors_vibration_time()

    def update_motor_power(self, new_motor_power):
        self.motor_power = int(new_motor_power)
        self.set_selected_motors_motor_power()

    def update_data(self, data, label_texts, root):
        for esp_id in self.esp_indexes:
            if data[esp_id - 1] is not None:
                self.analyze_event(esp_id, data[esp_id - 1], root)
                board_id = data[esp_id - 1][0]
                label_texts[esp_id - 1].set(
                    f"Board ID: {board_id}\n"
                    f"Palpador: {data[esp_id - 1][1]}\n"
                    f"Timestamp: {data[esp_id - 1][2]}"
                )
            else:
                label_texts[esp_id - 1].set(f"Board {esp_id} no conectada")

    def receive_data(self, data_queue, esp_data):
        while True:
            data, _ = self.sock.recvfrom(1024)
            if len(data) == struct.calcsize(self.struct_format):
                palpador_readings = struct.unpack(self.struct_format, data)
                esp_id = palpador_readings[0]
                esp_data[esp_id - 1] = palpador_readings
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