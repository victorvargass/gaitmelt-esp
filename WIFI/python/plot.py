import pandas as pd
import matplotlib.pyplot as plt

NUM_ESPS = 4
def plot_data(csv_filename, vibration_times_3=None, vibration_times_4=None):
    # Lee el archivo CSV

    accSetColors = ["red", "blue", "green"]
    gyrSetColors = ["purple", "orange", "pink"]

    acc_y_lims = (-25, 25)
    gyr_y_lims = (-5, 5)

    try:
        df = pd.read_csv(csv_filename, sep=",")
    except FileNotFoundError:
        print("Error: Archivo no encontrado.")
        return

    fig, axs = plt.subplots(4, 2, figsize=(12, 8), sharex='col', sharey='row')

    sensor_titles = [
        "Sensor 1 - Muslo Izquierdo",
        "Sensor 2 - Muslo Derecho",
        "Sensor 3 - Gemelo Izquierdo",
        "Sensor 4 - Gemelo Derecho",
    ]

    # Plot para acc_data
    axs[0, 0].plot(
        df["timestamp_1"], df["acc_x_1"], label="x", color=accSetColors[0]
    )
    axs[0, 0].plot(
        df["timestamp_1"], df["acc_y_1"], label="y", color=accSetColors[1]
    )
    axs[0, 0].plot(
        df["timestamp_1"], df["acc_z_1"], label="z", color=accSetColors[2]
    )
    axs[0, 0].set_title(f"{sensor_titles[0]}")
    axs[0, 0].set_ylabel("Aceleración")
    axs[0, 0].legend(loc="lower left")
    if vibration_times_3:
        for time_point in vibration_times_3:
            axs[0, 0].axvline(
                x=time_point, color="black", linestyle="--", linewidth=1
            )
    axs[0, 0].set_ylim(acc_y_lims)

    axs[0, 1].plot(
        df["timestamp_1"], df["acc_x_2"], label="x", color=accSetColors[0]
    )
    axs[0, 1].plot(
        df["timestamp_1"], df["acc_y_2"], label="y", color=accSetColors[1]
    )
    axs[0, 1].plot(
        df["timestamp_1"], df["acc_z_2"], label="z", color=accSetColors[2]
    )
    axs[0, 1].set_title(f"{sensor_titles[1]}")
    axs[0, 1].set_ylabel("Aceleración")
    axs[0, 1].legend(loc="lower left")
    if vibration_times_3:
        for time_point in vibration_times_3:
            axs[0, 1].axvline(
                x=time_point, color="black", linestyle="--", linewidth=1
            )
    axs[0, 1].set_ylim(acc_y_lims)

    axs[1, 0].plot(
        df["timestamp_1"], df["acc_x_3"], label="x", color=accSetColors[0]
    )
    axs[1, 0].plot(
        df["timestamp_1"], df["acc_y_3"], label="y", color=accSetColors[1]
    )
    axs[1, 0].plot(
        df["timestamp_1"], df["acc_z_3"], label="z", color=accSetColors[2]
    )
    axs[1, 0].set_title(f"{sensor_titles[2]}")
    axs[1, 0].set_ylabel("Aceleración")
    axs[1, 0].legend(loc="lower left")
    if vibration_times_3:
        for time_point in vibration_times_3:
            axs[1, 0].axvline(
                x=time_point, color="black", linestyle="--", linewidth=1
            )
    axs[1, 0].set_ylim(acc_y_lims)

    axs[1, 1].plot(
        df["timestamp_1"], df["acc_x_4"], label="x", color=accSetColors[0]
    )
    axs[1, 1].plot(
        df["timestamp_1"], df["acc_y_4"], label="y", color=accSetColors[1]
    )
    axs[1, 1].plot(
        df["timestamp_1"], df["acc_z_4"], label="z", color=accSetColors[2]
    )
    axs[1, 1].set_title(f"{sensor_titles[3]}")
    axs[1, 1].set_ylabel("Aceleración")
    axs[1, 1].legend(loc="lower left")
    if vibration_times_3:
        for time_point in vibration_times_3:
            axs[1, 1].axvline(
                x=time_point, color="black", linestyle="--", linewidth=1
            )
    axs[1, 1].set_ylim(acc_y_lims)

    # Plot para gyr_data
    axs[2, 0].plot(
        df["timestamp_1"], df["gyr_x_1"], label="x", color=gyrSetColors[0]
    )
    axs[2, 0].plot(
        df["timestamp_1"], df["gyr_y_1"], label="y", color=gyrSetColors[1]
    )
    axs[2, 0].plot(
        df["timestamp_1"], df["gyr_z_1"], label="z", color=gyrSetColors[2]
    )
    axs[2, 0].set_title(f"{sensor_titles[0]}")
    axs[2, 0].set_ylabel("Giroscopio")
    axs[2, 0].legend(loc="lower left")
    if vibration_times_3:
        for time_point in vibration_times_3:
            axs[2, 0].axvline(
                x=time_point, color="black", linestyle="--", linewidth=1
            )
    axs[2, 0].set_ylim(gyr_y_lims)


    axs[2, 1].plot(
        df["timestamp_1"], df["gyr_x_2"], label="x", color=gyrSetColors[0]
    )
    axs[2, 1].plot(
        df["timestamp_1"], df["gyr_y_2"], label="y", color=gyrSetColors[1]
    )
    axs[2, 1].plot(
        df["timestamp_1"], df["gyr_z_2"], label="z", color=gyrSetColors[2]
    )
    axs[2, 1].set_title(f"{sensor_titles[1]}")
    axs[2, 1].set_ylabel("Giroscopio")
    axs[2, 1].legend(loc="lower left")
    if vibration_times_3:
        for time_point in vibration_times_3:
            axs[2, 1].axvline(
                x=time_point, color="black", linestyle="--", linewidth=1
            )
    axs[2, 1].set_ylim(gyr_y_lims)


    axs[3, 0].plot(
        df["timestamp_1"], df["gyr_x_3"], label="x", color=gyrSetColors[0]
    )
    axs[3, 0].plot(
        df["timestamp_1"], df["gyr_y_3"], label="y", color=gyrSetColors[1]
    )
    axs[3, 0].plot(
        df["timestamp_1"], df["gyr_z_3"], label="z", color=gyrSetColors[2]
    )
    axs[3, 0].set_title(f"{sensor_titles[2]}")
    axs[3, 0].set_ylabel("Giroscopio")
    axs[3, 0].legend(loc="lower left")
    if vibration_times_3:
        for time_point in vibration_times_3:
            axs[3, 0].axvline(
                x=time_point, color="black", linestyle="--", linewidth=1
            )
    axs[3, 0].set_ylim(gyr_y_lims)

    axs[3, 1].plot(
        df["timestamp_1"], df["gyr_x_4"], label="x", color=gyrSetColors[0]
    )
    axs[3, 1].plot(
        df["timestamp_1"], df["gyr_y_4"], label="y", color=gyrSetColors[1]
    )
    axs[3, 1].plot(
        df["timestamp_1"], df["gyr_z_4"], label="z", color=gyrSetColors[2]
    )
    axs[3, 1].set_title(f"{sensor_titles[3]}")
    axs[3, 1].set_ylabel("Giroscopio")
    axs[3, 1].legend(loc="lower left")
    if vibration_times_3:
        for time_point in vibration_times_3:
            axs[3, 1].axvline(
                x=time_point, color="black", linestyle="--", linewidth=1
            )
    axs[3, 1].set_ylim(gyr_y_lims)

    fig.supxlabel("Tiempo [s]")

    # Ajustar el diseño
    suptitle = csv_filename.split(".")[0]

    plt.suptitle(suptitle)
    plt.tight_layout()
    plt.savefig(suptitle + ".png")  # Guardar el gráfico como una imagen PNG
    plt.show()

plot_data("1716943001464_1716943004042.csv")