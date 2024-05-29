import tkinter as tk
import queue
import threading
from utils import (
    update_thresholds,
    receive_data,
    update_gui,
    toggle_recording,
    acc_y_threshold_value,
)

NUM_ESPS = 4

# Configurar la interfaz gráfica
root = tk.Tk()
root.geometry("1600x900")
root.option_add("*Font", "Helvetica 20")

# Configurar el layout de la cuadrícula
for i in range(4):
    root.grid_columnconfigure(i, weight=1)
root.grid_rowconfigure(0, weight=1)
root.grid_rowconfigure(1, weight=1)
root.grid_rowconfigure(2, weight=1)
root.grid_rowconfigure(3, weight=1)
root.grid_rowconfigure(4, weight=1)

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
        width=75,
        height=20,
    )
    for text in label_texts
]

for i, panel in enumerate(panels):
    row = i // 2
    col = i % 2
    panel.grid(row=row, column=col, padx=10, pady=10, sticky="nsew")

# Slider para acc_y_threshold
acc_y_slider_label = tk.Label(root, text="acc_y threshold:")
acc_y_slider_label.grid(row=4, column=0, columnspan=4, pady=(20, 0))

acc_y_slider = tk.Scale(
    root,
    from_=0,
    to=10,
    orient="horizontal",
    length=400,
    command=lambda value: update_thresholds((acc_y_slider.get())),
)
acc_y_slider.set(acc_y_threshold_value)
acc_y_slider.grid(row=5, column=1, columnspan=2)

# Configurar botones y elementos adicionales
record_button = tk.Button(
    root,
    text="Start Recording",
    command=lambda: toggle_recording(record_button, label_texts),
    bg="green",
    fg="white",
)
record_button.grid(row=7, column=1, columnspan=2, pady=(20, 0))

# Configurando para centrar el slider y el botón horizontalmente
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_columnconfigure(2, weight=1)
root.grid_columnconfigure(3, weight=1)

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
