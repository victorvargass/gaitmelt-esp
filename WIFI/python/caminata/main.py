import tkinter as tk
import queue
import threading
from utils import (
    update_thresholds,
    receive_data,
    update_gui,
    toggle_recording,
    sync_devices,
    all_motors_on,
    motor_on,
    acc_y_threshold_value,
)

NUM_ESPS = 2

# Configurar la interfaz gráfica
root = tk.Tk()
root.geometry("1600x900")
root.option_add("*Font", "Helvetica 20")

# Configurar el layout de la cuadrícula
for i in range(2):
    root.grid_columnconfigure(i, weight=1)

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
    text="Activate motor 1",
    command=lambda: motor_on(0),
    bg="red",
    fg="white",
)
motor_button_1.grid(row=2, column=0, columnspan=2, pady=(20, 0))
motor_button_2 = tk.Button(
    root,
    text="Activate motor 2",
    command=lambda: motor_on(1),
    bg="red",
    fg="white",
)
motor_button_2.grid(row=3, column=0, columnspan=2, pady=(20, 0))

# Configurar botones y elementos adicionales
all_motors_button = tk.Button(
    root,
    text="Activate all motors",
    command=lambda: all_motors_on(),
    bg="red",
    fg="white",
)
all_motors_button.grid(row=5, column=0, columnspan=2, pady=(20, 0))

# Configurar botones y elementos adicionales
record_button = tk.Button(
    root,
    text="Start Recording",
    command=lambda: toggle_recording(record_button),
    bg="green",
    fg="white",
)
record_button.grid(row=2, column=1, columnspan=2, pady=(20, 0))

# Configurar botones y elementos adicionales
sync_button = tk.Button(
    root,
    text="Sync devices",
    command=lambda: sync_devices(),
    bg="yellow",
    fg="white",
)
sync_button.grid(row=3, column=1, columnspan=2, pady=(20, 0))

# Slider para acc_y_threshold
acc_y_slider_label = tk.Label(root, text="acc_y th:")
acc_y_slider_label.grid(row=4, column=1, columnspan=4, pady=(20, 0))

acc_y_slider = tk.Scale(
    root,
    from_=0,
    resolution=0.1,
    to=10,
    orient="horizontal",
    length=200,
    command=lambda value: update_thresholds((acc_y_slider.get())),
)
acc_y_slider.set(acc_y_threshold_value)
acc_y_slider.grid(row=5, column=1, columnspan=2)


# Configurar threads para la recepción de datos y actualización de la GUI
esp_data = [None] * NUM_ESPS
data_queue = queue.Queue()

receive_thread = threading.Thread(target=receive_data, args=(data_queue, esp_data))
receive_thread.daemon = True
receive_thread.start()

update_thread = threading.Thread(
    target=update_gui, args=(data_queue, label_texts, root)
)
update_thread.daemon = True
update_thread.start()

root.mainloop()