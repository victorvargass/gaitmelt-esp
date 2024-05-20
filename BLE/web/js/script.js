import { isWebBluetoothEnabled, getDateTime } from './utils.js';

//Define BLE Device Specs
var deviceName = 'GaitMelt Device ';

const bleServices = [
    '6e7f9ca5-5177-4f24-964a-e28e7859ce7e',
    '32cd0b16-9fca-463e-a57c-a14eedb29221',
    '54095b1e-941e-4d7c-8465-e29a70b84f5a',
    '394b9eb5-53e6-4a6c-8207-1cac1784d622'
];

const sensorCharacteristics = [
    '894f1b23-1f24-4faf-8e58-04c26db94813',
    '3d89ca41-83f2-485a-9a08-bcd001b47c7a',
    '4ce979b1-4717-4b37-af73-f83605649e2c',
    '4a7a8178-c2ac-40e2-85c8-c13b7aabe0ca'
];

const motorCharacteristics = [
    'fd2d07fa-0fc2-4ef9-bafc-4cbaf99413c5',
    'a7fae1af-7f5f-47be-aad8-ca4f2c4926fb',
    '6688009e-3db8-4fa9-8027-af5bdc0fcf4d',
    '60d025dd-417c-4ee6-8ffb-2993d99fb501'
];

// DOM Elements
const connectButtons = [];
const motorButtons = [];
const last_values = [];
const timestamp_ps = [];
const bleStateContainers = [];
const timestampContainers = [];
const lastAccContainers = [];
const lastGyrContainers = [];

var buttonStates = {
    "motorButton1": false,
    "motorButton2": false,
    "motorButton3": false,
    "motorButton4": false,
};

for (let i = 1; i <= 4; i++) {
    connectButtons.push(document.getElementById(`connectBleButton${i}`));
    last_values.push(document.getElementById(`last_sensor_values_p${i}`));
    timestamp_ps.push(document.getElementById(`timestamp_p${i}`));
    motorButtons.push(document.getElementById(`motorButton${i}`));
    bleStateContainers.push(document.getElementById(`bleState${i}`));
    timestampContainers.push(document.getElementById(`timestamp${i}`));
    lastAccContainers.push(document.getElementById(`last_acc_values_${i}`));
    lastGyrContainers.push(document.getElementById(`last_gyr_values_${i}`));
}

var bleServer = []
var bleServiceFound = [];
var sensorCharacteristicFound = [];


var init_timestamp = Date.now();
console.log("INIT TIME", init_timestamp);

for (let i = 0; i < connectButtons.length; i++) {
    connectButtons[i].addEventListener('click', () => {
        var button = connectButtons[i]
        if (button.classList.contains("disconnected") && isWebBluetoothEnabled(bleStateContainers[i])) {
            connectToDevice(
                bleServices[i], bleStateContainers[i], sensorCharacteristics[i],
                timestampContainers[i], lastAccContainers[i], lastGyrContainers[i], i)
        }
        else if (button.classList.contains("connected")) {
            disconnectDevice(bleStateContainers[i], bleServer[i], sensorCharacteristicFound[i], i);
        }
    });
}

function onDisconnected(event, bleService, bleStateContainer, sensorCharacteristic, timestampContainer, lastAccContainer, lastGyrContainer, index) {
    console.log('Device Disconnected:', event.target.device.name);
    bleStateContainer.innerHTML = "Dispositivo desconectado";
    bleStateContainer.style.color = "#d13a30";

    connectToDevice(
        bleService, bleStateContainer, sensorCharacteristic, timestampContainer, lastAccContainer, lastGyrContainer, index)
}

async function handleCharacteristicChange(event, timestampContainer, lastAccContainer, lastGyrContainer) {
    const receivedDataBuffer = event.target.value
    const dataView = new DataView(receivedDataBuffer.buffer);
    const structSize = 32;
    
    // Variables para acumular los datos
    const accDataArray = [];
    const gyrDataArray = [];
    
    // Calcular la cantidad máxima de estructuras que podemos enviar antes de alcanzar el límite de 514 bytes
    const maxStructures = Math.min(14, Math.floor(514 / structSize));

    // Iterar sobre el buffer recibido
    for (let i = 0; i < maxStructures; i++) {
        const offset = i * structSize;
        // Asegurarse de que el offset no exceda la longitud del buffer
        if (offset + structSize <= receivedDataBuffer.byteLength) {
            // Extraer los datos de la estructura
            const board_id = dataView.getInt32(offset, true);
            const accData = [
                dataView.getFloat32(offset + 4, true),
                dataView.getFloat32(offset + 8, true),
                dataView.getFloat32(offset + 12, true)
            ];
            const gyrData = [
                dataView.getFloat32(offset + 16, true),
                dataView.getFloat32(offset + 20, true),
                dataView.getFloat32(offset + 24, true)
            ];
            const timestamp = dataView.getFloat32(offset + 28, true); // Usar getBigUint64 para leer un valor de 64 bits (8 bytes) como un número entero grande sin signo

            // Almacenar los datos en los arreglos correspondientes
            accDataArray.push(accData);
            gyrDataArray.push(gyrData);
            console.log('tamaño del paquete: ', receivedDataBuffer.byteLength);
            console.log(`Datos recibidos para el board ${board_id}:`);
            console.log('Timestamp:', Number(timestamp));
        }
    }

    // Actualizar el contenido del contenedor de datos una vez fuera del bucle
    let accHTML = "";
    let gyrHTML = "";
    
    accHTML += `x:${accDataArray[0][0].toFixed(3)} y:${accDataArray[0][1].toFixed(3)} z:${accDataArray[0][2].toFixed(3)} `;
    gyrHTML += `x:${gyrDataArray[0][0].toFixed(3)} y:${gyrDataArray[0][1].toFixed(3)} z:${gyrDataArray[0][2].toFixed(3)} `;
    lastAccContainer.innerHTML = accHTML;
    lastGyrContainer.innerHTML = gyrHTML;

    // Actualizar el contenedor de la marca de tiempo
    timestampContainer.innerHTML = getDateTime();
}

// Connect to BLE Device and Enable Notifications
function connectToDevice(bleService, bleStateContainer, sensorCharacteristic, timestampContainer, lastAccContainer, lastGyrContainer, index) {
    var connectButton = connectButtons[index]
    var motorButton = motorButtons[index]
    var lastValues = last_values[index]
    var timestamp_p = timestamp_ps[index]
    console.log('Initializing Bluetooth...');
    navigator.bluetooth.requestDevice({
        //acceptAllDevices: true,
        filters: [{ name: deviceName + (index + 1).toString() }],
        optionalServices: [bleService]
    })
        .then(device => {
            connectButton.innerText = "Conectando..."
            connectButton.classList.add("connecting");
            bleStateContainer.innerHTML = 'Conectando...';
            bleStateContainer.style.color = "#FFEA00";
            console.log('Device Selected:', device.name);
            device.addEventListener('gattservicedisconnected', function () {
                onDisconnected(
                    device.name, bleService, bleStateContainer,
                    sensorCharacteristic, timestampContainer, lastAccContainer, lastGyrContainer, index
                )
            });
            return device.gatt.connect();
        })
        .then(gattServer => {
            bleServer[index] = gattServer;
            console.log("Connected to GATT Server");
            return gattServer.getPrimaryService(bleService);
        })
        .then(service => {
            bleServiceFound[index] = service;
            console.log("Service discovered:", service.uuid);
            return service.getCharacteristic(sensorCharacteristic);
        })
        .then(characteristic => {
            console.log("Characteristic discovered:", characteristic.uuid);
            sensorCharacteristicFound[index] = characteristic;
            
            characteristic.addEventListener('characteristicvaluechanged', async function (event) {
                await handleCharacteristicChange(event, timestampContainer, lastAccContainer, lastGyrContainer);
                var current_timestamp = Date.now();
                console.log("TIME AFTER", current_timestamp)
                const timeDifference = current_timestamp - init_timestamp;
                console.log('Diferencia de tiempo:', timeDifference, 'milisegundos');
                
                
                init_timestamp = current_timestamp;
                console.log("TIME BEFORE", init_timestamp)
            });
            characteristic.startNotifications();
            console.log("Notifications Started.");

            bleStateContainer.innerHTML = 'Conectado a ' + deviceName + (index + 1).toString();
            bleStateContainer.style.color = "#24af37";
            connectButton.innerText = "Desconectar"
            connectButton.classList.remove("disconnected");
            connectButton.classList.remove("connecting");
            connectButton.classList.add("connected");
            motorButton.classList.remove("disconnected");
            motorButton.classList.add("connected");
            lastValues.classList.remove("disconnected");
            lastValues.classList.add("connected");
            timestamp_p.classList.remove("disconnected");
            timestamp_p.classList.add("connected");
            return characteristic.readValue();
        })
        .then(value => {
            //console.log("Read value: ", value);
            //const decodedValue = parseBytesToStruct(value.buffer)
            //console.log("Decoded value: ", decodedValue);
        })
        .catch(error => {
            console.log('Error: ', error);
            connectButton.innerText = "Conectar"
            connectButton.classList.remove("connected");
            connectButton.classList.remove("connecting");
            connectButton.classList.add("disconnected");
            motorButton.classList.remove("connected");
            motorButton.classList.add("disconnected");
            lastValues.classList.remove("connected");
            lastValues.classList.add("disconnected");
            timestamp_p.classList.remove("connected");
            timestamp_p.classList.add("disconnected");

            bleStateContainer.innerHTML = "Error de conexión. Vuelve a intentarlo";
            bleStateContainer.style.color = "#d13a30";
        })
}

function disconnectDevice(bleStateContainer, bleServer, sensorCharacteristicFound, index) {
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
                        var motorButton = document.getElementById(`motorButton${index + 1}`)
                        var last_values = document.getElementById(`last_sensor_values_p${index + 1}`)
                        var timestamp_p = document.getElementById(`timestamp_p${index + 1}`)
                        connectButton.innerText = "Conectar"
                        connectButton.classList.remove("connected");
                        connectButton.classList.add("disconnected");
                        motorButton.classList.remove("connected");
                        motorButton.classList.add("disconnected");
                        last_values.classList.remove("connected");
                        last_values.classList.add("disconnected");
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

function writeOnCharacteristic(bleServer, bleServiceFound, c) {
    if (bleServer && bleServer.connected) {
        bleServiceFound.getCharacteristic(c)
            .then(characteristic => {
                console.log("Found the motor characteristic: ", characteristic.uuid);
                const data = new Uint8Array([1]);
                return characteristic.writeValue(data);
            })
            .catch(error => {
                console.error("Error writing to the motor characteristic: ", error);
            });
    } else {
        console.error("Bluetooth is not connected. Cannot write to characteristic.")
        window.alert("Bluetooth is not connected. Cannot write to characteristic. \n Connect to BLE first!")
    }
}

function toggleMotorButton(buttonId, bleServer, bleServiceFound, motorCharacteristic) {
    var button = document.getElementById(buttonId);
    if (button) {
        if (button.classList.contains("on")) {
            button.innerText = "Activar motor";
            button.classList.remove("on");
            button.classList.add("off");
            buttonStates[buttonId] = false;
        } else {
            writeOnCharacteristic(bleServer, bleServiceFound, motorCharacteristic)
            button.innerText = "Vibrando...";
            button.classList.remove("off");
            button.classList.add("on");
            buttonStates[buttonId] = true;
            button.disabled = true;
            console.log(buttonId, "Vibrando...")
            setTimeout(() => {
                button.disabled = false;
                button.innerText = "Activar motor";
                button.classList.remove("on");
                button.classList.add("off");
                buttonStates[buttonId] = false;
                console.log("Motor apagado")
            }, 1000);
        }
    }
}

for (var i = 1; i <= 4; i++) {
    (function (i) {
        document.getElementById("motorButton" + i).addEventListener("click", function () {
            toggleMotorButton("motorButton" + i, bleServer[i - 1], bleServiceFound[i - 1], motorCharacteristics[i - 1]);
        });
    })(i);
}