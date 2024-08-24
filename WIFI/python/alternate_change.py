import tkinter as tk
import queue
import threading
from utils import AlternateChange  # Asegúrate de que esta importación sea correcta

# Configuración de los ESPs
ESP_IPS = {
    1: "192.168.50.11",
    2: "192.168.50.12",
    3: "192.168.50.13",
    4: "192.168.50.14",
}

STRUCT_FORMAT = "i fff fff i"
LOCAL_UDP_IP = "192.168.50.82"
SHARED_UDP_PORT = 4210
OUTPUT_FILENAME = "PGMLT_001"
OUTPUT_FOLDER = "output_data/"

READING_MODE = True

VIBRATION_CADENCE = 2000
MOTOR_POWER = 250 # 70

ESP_INDEXES = [1, 2, 3, 4]

SCREEN_SIZE = "850x1100"

# Crear una instancia de GaitMelt
alternate_change = AlternateChange(
    local_udp_ip=LOCAL_UDP_IP,
    shared_port=SHARED_UDP_PORT,
    esp_indexes=ESP_INDEXES,
    esp_ips=ESP_IPS,
    struct_format=STRUCT_FORMAT,
    output_filename=OUTPUT_FILENAME,
    output_folder=OUTPUT_FOLDER,
    motor_power=MOTOR_POWER,
    vibration_cadence=VIBRATION_CADENCE
)

# Configurar la interfaz gráfica
root = tk.Tk()
root.geometry(SCREEN_SIZE)
root.configure(bg="white")
root.option_add("*Font", "Helvetica 20")

# Configurar el layout de la cuadrícula
for i in range(4):
    root.grid_columnconfigure(i, weight=1)
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=1)

# Crear y ubicar los paneles
label_texts = [tk.StringVar() for _ in range(4)]
for i, text in enumerate(label_texts):
    text.set(f"Board {i+1} no conectada")

root.panels = {
    f"panel_{i}": tk.Label(
        root,
        textvariable=text,
        padx=10,
        bg="white",
        pady=10,
        borderwidth=5,
        relief="solid",
        width=50,
        height=20,
    )
    for i, text in enumerate(label_texts)
}

# Organizar los paneles en una cuadrícula
for i, panel in enumerate(root.panels.values()):
    row = i // 2
    col = i % 2
    panel.grid(row=row, column=col, padx=10, pady=10)

label_output_filename = tk.Label(root, text="Nombre del archivo", bg="white")
label_output_filename.grid(row=2, column=0, columnspan=2, pady=(20, 0))
input_output_filename = tk.Entry(root)
input_output_filename.grid(row=3, column=0, columnspan=2, pady=(20, 0))
input_output_filename.insert(0, OUTPUT_FILENAME)  # Establecer el valor por defecto
input_output_filename.bind('<KeyRelease>', alternate_change.update_output_filename)


init_button = tk.Button(
    root,
    text="Iniciar",
    command=lambda: alternate_change.toggle_alternative_vibration(init_button),
    bg="green",
    fg="white",
)
init_button.grid(row=2, column=1, columnspan=2, pady=(20, 0))

vc_slider_label = tk.Label(root, text="Cadencia vibración [ms]", bg="white")
vc_slider_label.grid(row=4, column=1, columnspan=4, pady=(20, 0))

vc_slider = tk.Scale(
    root,
    from_=500,
    resolution=500,
    to=2000,
    orient="horizontal",
    length=200,
    bg="white",
    command=lambda value: alternate_change.update_vc(vc_slider.get()),
)
vc_slider.set(alternate_change.vibration_cadence)
vc_slider.grid(row=5, column=1, columnspan=2)

# Slider para acc_y_threshold (ThY)
motor_power_slider_label = tk.Label(root, text="Potencia motor", bg="white")
motor_power_slider_label.grid(row=8, column=1, columnspan=4, pady=(20, 0))

motor_power_slider = tk.Scale(
    root,
    from_=10,
    resolution=10,
    to=250,
    orient="horizontal",
    length=200,
    bg="white",
    command=lambda value: alternate_change.update_motor_power(motor_power_slider.get()),
)
motor_power_slider.set(alternate_change.motor_power)
motor_power_slider.grid(row=9, column=1, columnspan=2)

# Configurar threads para la recepción de datos y actualización de la GUI
esp_data = [None] * 4
data_queue = queue.Queue()

receive_thread = threading.Thread(
    target=alternate_change.receive_data, args=(data_queue, esp_data)
)
receive_thread.daemon = True
receive_thread.start()

update_thread = threading.Thread(
    target=alternate_change.update_gui,
    args=(data_queue, label_texts, root),
)
update_thread.daemon = True
update_thread.start()

root.mainloop()
