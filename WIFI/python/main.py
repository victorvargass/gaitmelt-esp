import tkinter as tk
import subprocess
import os

LOCAL_UDP_IP = "192.168.50.82"
SHARED_UDP_PORT = 4210

cmd = f"lsof -i :{SHARED_UDP_PORT} | grep -v 'PID' | awk '{{print $2}}'"
try:
    pid = subprocess.check_output(cmd, shell=True).decode().strip()
    if pid:
        print(f"Terminando proceso con PID {pid} que está usando el puerto {SHARED_UDP_PORT}")
        os.system(f"kill -9 {pid}")
    else:
        print("No hay proceso corriendo...")
except subprocess.CalledProcessError:
    print("No se pudo obtener el PID o no hay proceso asociado al puerto.")

# Variable global para el proceso en ejecución
current_process = None

# Función para ejecutar un script y cerrar el actual
def run_script(script_name):
    global current_process
    stop_script()  # Detener cualquier script actual
    current_process = subprocess.Popen(['python', script_name])  # Ejecutar nuevo script
    root.after(100, root.quit)  # Cerrar la ventana de main después de iniciar el script

# Función para detener el proceso en ejecución
def stop_script():
    global current_process
    if current_process is not None:
        current_process.terminate()  # Terminar el proceso actual
        current_process = None

# Función para cerrar la aplicación
def exit_app():
    stop_script()  # Asegurarse de detener cualquier script en ejecución
    root.quit()  # Cerrar la aplicación

# Configuración de la ventana principal
root = tk.Tk()
root.overrideredirect(True)  # Elimina los bordes y botones estándar
root.title("Selecciona una opción")
root.configure(bg="white")
window_width, window_height = 1200, 600

# Calcular posición para centrar la ventana en la pantalla
screen_width = root.winfo_screenwidth()
screen_height = root.winfo_screenheight()
position_x = (screen_width - window_width) // 2
position_y = (screen_height - window_height) // 2
root.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")  # Centrar ventana

# Cargar la imagen (asegurarse de tener la imagen en el directorio correcto)
image = tk.PhotoImage(file="leufulab.png")  # Cambiar a la ruta de tu imagen
image = image.subsample(10, 10)  # Reducir tamaño a 40x40 (ajustar factor según tamaño original)

# Crear un Frame para el texto y los botones
main_frame = tk.Frame(root, bg="white")
main_frame.pack(expand=True)

# Colocar la imagen arriba de todo
image_label = tk.Label(main_frame, image=image, bg="white")
image_label.pack(pady=20)

# Crear un Label para el texto "Seleccionar tarea"
label_tarea = tk.Label(main_frame, text="Seleccionar tarea", font=("Helvetica", 24), bg="white")
label_tarea.pack(pady=20)

# Crear un Frame para los botones en horizontal
button_frame = tk.Frame(main_frame, bg="white")
button_frame.pack(pady=20)

# Crear los botones con funciones lambda para ejecutar los scripts solo al hacer clic
button_vibracion_continua = tk.Button(
    button_frame, 
    text="Vibración manual", 
    font=("Helvetica", 20),
    bg="#4CAF50", 
    fg="white", 
    width=20, 
    height=2,
    command=lambda: run_script("vibracion_continua.py")  # Usar lambda para evitar ejecución inmediata
)

button_fsr = tk.Button(
    button_frame, 
    text="Vibración con detección", 
    font=("Helvetica", 20),
    bg="#008CBA", 
    fg="white", 
    width=20, 
    height=2,
    command=lambda: run_script("fsr.py")  # Usar lambda para evitar ejecución inmediata
)

button_fsr_avanzado = tk.Button(
    button_frame, 
    text="Vibración con detección avanzada", 
    font=("Helvetica", 20),
    bg="#008CBA", 
    fg="white", 
    width=20, 
    height=2,
    command=lambda: run_script("fsr_avanzada.py")  # Usar lambda para evitar ejecución inmediata
)

# Colocar los botones horizontalmente
button_vibracion_continua.pack(side="left", padx=20)
button_fsr.pack(side="left", padx=20)
button_fsr_avanzado.pack(side="left", padx=20)
button_fsr_avanzado.config(state="disabled")

# Crear y posicionar el botón "Exit" en un frame inferior
exit_button_frame = tk.Frame(root, bg="white")
exit_button_frame.pack(side="bottom", pady=20)

button_exit = tk.Button(
    exit_button_frame, 
    text="Salir", 
    font=("Helvetica", 24),
    bg="red", 
    fg="white", 
    width=20, 
    height=2,
    command=exit_app  # Llamar a la función exit_app al hacer clic en "Exit"
)
button_exit.pack()

# Ejecutar la interfaz
root.mainloop()
