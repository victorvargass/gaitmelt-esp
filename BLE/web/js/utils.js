export function parseBytesToStruct(buffer) {
    const view = new DataView(buffer);
    return {
        id: view.getInt32(0, true),
        acc_x: view.getFloat32(4, true),
        acc_y: view.getFloat32(8, true),
        acc_z: view.getFloat32(12, true),
        gyr_x: view.getFloat32(16, true),
        gyr_y: view.getFloat32(20, true),
        gyr_z: view.getFloat32(24, true),
        readingId: view.getFloat32(28, true),
    }
}

export function isWebBluetoothEnabled(bleStateContainer) {
    if (!navigator.bluetooth) {
        console.log('Web Bluetooth API is not available in this browser!');
        bleStateContainer.innerHTML = "Web Bluetooth API is not available in this browser/device!";
        return false
    }
    console.log('Web Bluetooth API supported in this browser.');
    return true
}
export function disconnectDevice(bleStateContainer, bleServer, sensorCharacteristicFound, index) {
    console.log("Disconnect Device.");
    if (bleServer && bleServer.connected) {
        let confirmacion = confirm("¿Estás seguro de que deseas desconectar el dispositivo?");
        if (confirmacion) {
            if (sensorCharacteristicFound) {
                sensorCharacteristicFound.stopNotifications()
                    .then(() => {
                        console.log("Notifications Stopped");
                        return bleServer.disconnect();
                    })
                    .then(() => {
                        console.log("Device Disconnected");

                        var connectButton = document.getElementById(`connectBleButton${index + 1}`)
                        var motorButton = document.getElementById(`timestamp_p${index + 1}`)
                        var timestamp_p = document.getElementById(`motorButton${index + 1}`)
                        connectButton.innerText = "Conectar"
                        connectButton.classList.remove("connected");
                        connectButton.classList.add("disconnected");
                        motorButton.classList.remove("connected");
                        motorButton.classList.add("disconnected");
                        timestamp_p.classList.remove("connected");
                        timestamp_p.classList.add("disconnected");

                        bleStateContainer.innerHTML = "Desconectado";
                        bleStateContainer.style.color = "#d13a30";
                    })
                    .catch(error => {
                        console.log("An error occurred:", error);
                    });
            } else {
                console.log("No characteristic found to disconnect.");
            }
        } else {
            console.log("El usuario ha cancelado.");
        }
    } else {
        // Throw an error if Bluetooth is not connected
        console.error("Bluetooth is not connected.");
        window.alert("Bluetooth is not connected.")
    }
}

export function getDateTime() {
    var currentdate = new Date();
    var day = ("00" + currentdate.getDate()).slice(-2); // Convert day to string and slice
    var month = ("00" + (currentdate.getMonth() + 1)).slice(-2);
    var year = currentdate.getFullYear();
    var hours = ("00" + currentdate.getHours()).slice(-2);
    var minutes = ("00" + currentdate.getMinutes()).slice(-2);
    var seconds = ("00" + currentdate.getSeconds()).slice(-2);

    var datetime = day + "/" + month + "/" + year + " at " + hours + ":" + minutes + ":" + seconds;
    return datetime;
}