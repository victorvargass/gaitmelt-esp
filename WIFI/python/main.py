import tkinter as tk
import queue
import threading
from utils import GaitMelt  # Asegúrate de que esta importación sea correcta

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
CSV_FILENAME = "recorded_data.csv"

TASK_NAME = "parkinson"  # salto, parkinson, caminata

OUTPUT_FOLDER = "output_data/" + TASK_NAME + "/"

if TASK_NAME == "parkinson":
    NUM_ESPS = 4
    THY = 1.5
    VD = 500  # vibration duration
    TIME_BETWEEN_VIBRATIONS = 0.8  # quiza modificar
    MIN_DURATION_BETWEEN_HEELS = None
    MOTOR_POWER = 70
elif TASK_NAME == "salto":
    NUM_ESPS = 2
    THY = 7.5
    VD = 1000  # vibration duration
    TIME_BETWEEN_VIBRATIONS = 2
    MIN_DURATION_BETWEEN_HEELS = None
    MOTOR_POWER = 70
elif TASK_NAME == "caminata":
    NUM_ESPS = 2
    THY = 3
    VD = 200  # vibration duration
    TIME_BETWEEN_VIBRATIONS = 0.6
    MIN_DURATION_BETWEEN_HEELS = 2
    MOTOR_POWER = 70

ESP_INDEXES = [1, 2] if NUM_ESPS == 2 else [1, 2, 3, 4]

# Crear una instancia de GaitMelt
gaitmelt = GaitMelt(
    task_name=TASK_NAME,
    local_udp_ip=LOCAL_UDP_IP,
    shared_port=SHARED_UDP_PORT,
    num_esps=NUM_ESPS,
    esp_indexes=ESP_INDEXES,
    esp_ips=ESP_IPS,
    struct_format=STRUCT_FORMAT,
    output_folder=OUTPUT_FOLDER,
    csv_filename=CSV_FILENAME,
    time_between_vibrations=TIME_BETWEEN_VIBRATIONS,
    thy=THY,
    vd=VD,
    motor_power=MOTOR_POWER,
    min_duration_between_heels=MIN_DURATION_BETWEEN_HEELS,
)

# Configurar la interfaz gráfica
root = tk.Tk(className=TASK_NAME)
root.geometry("1300x800")
root.option_add("*Font", "Helvetica 20")

# Configurar el layout de la cuadrícula
for i in range(NUM_ESPS):
    root.grid_columnconfigure(i, weight=1)
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=1)

# Crear y ubicar los paneles
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
        width=50,
        height=20,
    )
    for text in label_texts
]

for i, panel in enumerate(panels):
    row = i // 2
    col = i % 2
    panel.grid(row=row, column=col, padx=10, pady=10)

# Configurar botones y elementos adicionales
motor_button_1 = tk.Button(
    root,
    text="Activar vibrador 1",
    command=lambda: gaitmelt.activate_selected_motors([1]),
    bg="red",
    fg="white",
)
motor_button_1.grid(row=2, column=0, columnspan=2, pady=(20, 0))

motor_button_2 = tk.Button(
    root,
    text="Activar vibrador 2",
    command=lambda: gaitmelt.activate_selected_motors([2]),
    bg="red",
    fg="white",
)
motor_button_2.grid(row=3, column=0, columnspan=2, pady=(20, 0))

if NUM_ESPS == 4:
    motor_button_3 = tk.Button(
        root,
        text="Activar vibrador 3",
        command=lambda: gaitmelt.activate_selected_motors([3]),
        bg="red",
        fg="white",
    )
    motor_button_3.grid(row=4, column=0, columnspan=2, pady=(20, 0))
    motor_button_4 = tk.Button(
        root,
        text="Activar vibrador 4",
        command=lambda: gaitmelt.activate_selected_motors([4]),
        bg="red",
        fg="white",
    )
    motor_button_4.grid(row=5, column=0, columnspan=2, pady=(20, 0))

all_motors_button = tk.Button(
    root,
    text="Activar todos",
    command=lambda: gaitmelt.activate_selected_motors(ESP_INDEXES),
    bg="red",
    fg="white",
)
all_motors_button.grid(row=6, column=0, columnspan=2, pady=(20, 0))

record_button = tk.Button(
    root,
    text="Iniciar grabación",
    command=lambda: gaitmelt.toggle_recording(record_button),
    bg="green",
    fg="white",
)
record_button.grid(row=2, column=1, columnspan=2, pady=(20, 0))

sync_button = tk.Button(
    root,
    text="Sincronizar dispositivos",
    command=lambda: gaitmelt.sync_devices(),
    bg="yellow",
    fg="white",
)
sync_button.grid(row=3, column=1, columnspan=2, pady=(20, 0))

# Slider para acc_y_threshold (ThY)
thy_slider_label = tk.Label(root, text="Umbral Eje Y Acelerómetro")
thy_slider_label.grid(row=4, column=1, columnspan=4, pady=(20, 0))

thy_slider = tk.Scale(
    root,
    from_=0,
    resolution=0.1,
    to=10,
    orient="horizontal",
    length=200,
    command=lambda value: gaitmelt.update_thy(thy_slider.get()),
)
thy_slider.set(gaitmelt.thy)
thy_slider.grid(row=5, column=1, columnspan=2)

vd_slider_label = tk.Label(root, text="Duración vibración [ms]")
vd_slider_label.grid(row=6, column=1, columnspan=4, pady=(20, 0))

vd_slider = tk.Scale(
    root,
    from_=10,
    resolution=10,
    to=2000,
    orient="horizontal",
    length=200,
    command=lambda value: gaitmelt.update_vd(vd_slider.get()),
)
vd_slider.set(gaitmelt.vd)
vd_slider.grid(row=7, column=1, columnspan=2)

# Slider para acc_y_threshold (ThY)
motor_power_slider_label = tk.Label(root, text="Potencia motor")
motor_power_slider_label.grid(row=8, column=1, columnspan=4, pady=(20, 0))

motor_power_slider = tk.Scale(
    root,
    from_=10,
    resolution=10,
    to=250,
    orient="horizontal",
    length=200,
    command=lambda value: gaitmelt.update_motor_power(motor_power_slider.get()),
)
motor_power_slider.set(gaitmelt.motor_power)
motor_power_slider.grid(row=9, column=1, columnspan=2)

# Configurar threads para la recepción de datos y actualización de la GUI
esp_data = [None] * NUM_ESPS
data_queue = queue.Queue()

receive_thread = threading.Thread(
    target=gaitmelt.receive_data, args=(data_queue, esp_data)
)
receive_thread.daemon = True
receive_thread.start()

update_thread = threading.Thread(
    target=gaitmelt.update_gui,
    args=(data_queue, label_texts, root),
)
update_thread.daemon = True
update_thread.start()

root.mainloop()
