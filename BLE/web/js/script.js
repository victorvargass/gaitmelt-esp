import { isWebBluetoothEnabled, getDateTime, getFullDateTime, getTimeDiff } from './utils.js';

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

var connectedDevices = 0;
var initTimestamp = 0;
var endTimestamp = 0;

const trialContainer = document.getElementById('trialContainer')
const timerDisplay = document.getElementById('timerDisplay')

var motorActivated = [0, 0]

var acc_data = {
    1: [[], [], []],
    2: [[], [], []],
    3: [[], [], []],
    4: [[], [], []],
};

var gyr_data = {
    1: [[], [], []],
    2: [[], [], []],
    3: [[], [], []],
    4: [[], [], []],
};

var data_counters = [0, 0, 0, 0]

var buttonStates = {
    1: false,
    2: false,
    3: false,
    4: false,
};

var export_data = false;


let timerInterval; // Variable para almacenar el intervalo del temporizador
let startTime; // Variable para almacenar el tiempo de inicio del contador

const minutesDisplay = document.getElementById('minutes');
const secondsDisplay = document.getElementById('seconds');

//var init_times = [];
//var end_times = [];
//var c = 0;

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

function getACCState(acc_sensor_data){
    const xz_margin_degrees = 7;
    const yz_margin_degrees = 20;
    var sensor_state = ""
    var x = acc_sensor_data[acc_sensor_data.length - 1][0]
    var y = acc_sensor_data[acc_sensor_data.length - 1][1]
    var z = acc_sensor_data[acc_sensor_data.length - 1][2]

    var xz_orientation_degrees = Math.atan2(x, z) * (180.0 / Math.PI);
    var yz_orientation_degrees = Math.atan2(y, z) * (180.0 / Math.PI);

    // Mostrar la orientación estimada
    //console.log("Orientación XZ: " + xz_orientation_degrees + " grados");
    //console.log("Orientación YZ: " + yz_orientation_degrees + " grados");
    if (
        (xz_orientation_degrees >= -85 - xz_margin_degrees && xz_orientation_degrees <= -85 + xz_margin_degrees)
    ){
        //console.log("Orientación XZ: " + xz_orientation_degrees + " grados");
        //console.log("Orientación YZ: " + yz_orientation_degrees + " grados");
        var sensor_state = "Base"
    }
    else if (
        (yz_orientation_degrees >= 90 - yz_margin_degrees && yz_orientation_degrees <= 90 + yz_margin_degrees)
    ){
        var sensor_state = "Boton hacia abajo"
    }
    else{
        var sensor_state = "En movimiento o no definida"
    }

    //EVITAR CUANDO ESTEN ESTATICOS (VER VALORES INICIALES)
    //CALIBRAR??
    return sensor_state
}

async function handleCharacteristicChange(event, timestampContainer, lastAccContainer, lastGyrContainer) {
    const dataView = new DataView(event.target.value.buffer);

    // Calcular el offset una vez fuera del bucle
    const offsetMultiplier = 32;

    // Variables para acumular los datos
    const accDataArray = [];
    const gyrDataArray = [];
    let board_id; // Declarar board_id fuera del bucle

    for (let i = 0; i < 16; i++) {
        const offset = i * offsetMultiplier;

        // Extraer los datos de la estructura
        board_id = dataView.getInt32(offset, true); // Asignar valor a board_id dentro del bucle
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

        // Almacenar los datos en matrices temporales
        accDataArray.push(accData);
        gyrDataArray.push(gyrData);
    }
    /*
    if (
        board_id == 2 && buttonStates[1] == false &&
        accDataArray[accDataArray.length - 1][1] < 8 && getACCState(accDataArray) != "Base"
    ){  
        console.log(gyrDataArray[gyrDataArray.length - 1])
        console.log("3 Gemelo Izquierdo Y: ", accDataArray[accDataArray.length - 1][1])
        toggleMotorButton("motorButton1", bleServer[0], bleServiceFound[0], motorCharacteristics[0])
        console.log("Activate 1 Muslo Izquierdo", accDataArray[accDataArray.length - 1][1] < 8)
    }
    else{
        console.log(
            "gyrDataArray", gyrDataArray[gyrDataArray.length - 1],
            "acc_data Y", accDataArray[accDataArray.length - 1][1],
            "ESTADO", getACCState(accDataArray)
        )
    }
    */
    
    // Si es necesario, almacenar los datos para exportación
    if (export_data) {
        for (let i = 0; i < accDataArray.length; i++) {
            acc_data[board_id].push(accDataArray[i]);
            gyr_data[board_id].push(gyrDataArray[i]);
        }
        data_counters[board_id-1]++;
        //console.log(data_counters)
        //1 Muslo Izquierdo
        //2 Muslo Derecho
        //3 Gemelo Izquierdo
        //4 Gemelo Derecho
        if (
            board_id == 3 && buttonStates[1] == false &&
            acc_data[3][acc_data[3].length - 1][1] < 9 && getACCState(acc_data[3]) != "Base"
        ){
            //console.log("3 Gemelo Izquierdo Y: ", acc_data[3][acc_data[3].length - 1][1])
            toggleMotorButton("motorButton1", bleServer[0], bleServiceFound[0], motorCharacteristics[0])
            //console.log("Activate 1 Muslo Izquierdo", acc_data[3][acc_data[3].length - 1][1] < 8)
        }
        if (
            board_id == 4 && buttonStates[2] == false &&
            acc_data[4][acc_data[4].length - 1][1] < 9 && getACCState(acc_data[4]) != "Base"
        ){
            //console.log("4 Gemelo Derecho Y: ", acc_data[4][acc_data[4].length - 1][1])
            toggleMotorButton("motorButton2", bleServer[1], bleServiceFound[1], motorCharacteristics[1])
            //console.log("Activate 2 Muslo Derecho", acc_data[4][acc_data[4].length - 1][1] < 7)
        }
        /*
        else{
            console.log(
                "buttonStates[1]", buttonStates[1],
                "acc_data Y", acc_data[3][acc_data[3].length - 1][1],
                "ESTADO", getACCState(acc_data[3])
            )
        }
        */
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
                //var t = new Date().getTime()
                //init_times.push(t)
                await handleCharacteristicChange(event, timestampContainer, lastAccContainer, lastGyrContainer);
                //t = new Date().getTime()
                //end_times.push(t)
                //console.log("timestamps", init_times[c], end_times[c-1])
                //console.log("diff ms", init_times[c] - end_times[c-1])
                //console.log("freq", 1000 / (init_times[c] - end_times[c-1]) )
                //c++;
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
            connectedDevices++;
            console.log("Number of connected devices: ", connectedDevices)
            //if (connectedDevices == 4){
            if ((connectedDevices == 4) && (trialContainer.classList.contains('nodata'))){
                trialContainer.classList.remove("nodata");
            };
            return characteristic.readValue();
        })
        .then(value => {
            //console.log("Read value: ", value);
            //const decodedValue = parseBytesToStruct(value.buffer)
            //console.log("Decoded value: ", decodedValue);
        })
        .catch(error => {
            console.log('Error: ', error);
            /*
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
            */
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

                        connectedDevices--;
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

// Función para actualizar el tiempo transcurrido
function updateTimer() {
    const currentTime = new Date().getTime();
    const elapsedTime = currentTime - startTime;

    // Calcular minutos y segundos
    const minutes = Math.floor(elapsedTime / (1000 * 60));
    const seconds = Math.floor((elapsedTime % (1000 * 60)) / 1000);

    // Mostrar tiempo en el HTML
    minutesDisplay.textContent = padZero(minutes);
    secondsDisplay.textContent = padZero(seconds);
}

// Función auxiliar para agregar ceros a la izquierda si es necesario
function padZero(num) {
    return num < 10 ? '0' + num : num;
}

function toggleTrialButton(buttonId) {
    var button = document.getElementById(buttonId);
    if (button) {
        if (button.classList.contains("on")) {
            let confirmacion = confirm("¿Estás seguro de que deseas detener el ensayo?");
            if (confirmacion) {
                var trialName = document.getElementById("trialName");
                button.innerText = "Iniciar ensayo";
                button.classList.remove("on");
                button.classList.add("off");
                buttonStates[buttonId] = false;
                downloadCSV(trialName.value)
                timerDisplay.classList.add("stop")
                trialName.value = "";
                clearInterval(timerInterval);
            }
        } else {
            initTimestamp = new Date().getTime();

            button.innerText = "Detener ensayo";
            button.classList.remove("off");
            button.classList.add("on");
            buttonStates[buttonId] = true;
            export_data = true
            timerDisplay.classList.remove("stop")
            minutesDisplay.textContent = "00";
            secondsDisplay.textContent = "00";
            startTime = new Date().getTime();
            timerInterval = setInterval(updateTimer, 1000);
        }
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
    writeOnCharacteristic(bleServer, bleServiceFound, motorCharacteristic)
    if (button) {
        if (button.classList.contains("on")) {
            button.innerText = "Activar motor";
            button.classList.remove("on");
            button.classList.add("off");
            buttonStates[buttonId] = false;
        } else {
            button.innerText = "Vibrando...";
            button.classList.remove("off");
            button.classList.add("on");
            buttonStates[buttonId] = true;
            console.log("BOTON PRENDIDO MOTOR", buttonId, buttonStates[buttonId])
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

document.getElementById("trialButton").addEventListener("click", function () {
    toggleTrialButton("trialButton");
});


for (var i = 1; i <= 4; i++) {
    (function (i) {
        document.getElementById("motorButton" + i).addEventListener("click", function () {
            toggleMotorButton("motorButton" + i, bleServer[i - 1], bleServiceFound[i - 1], motorCharacteristics[i - 1]);
        });
    })(i);
}

function deleteChartData(data) {
    for (let key in data) {
        if (data.hasOwnProperty(key)) {
            data[key] = data[key].slice(3);
        }
    }
    return data;
}


function getMinDataLength(data) {
    let length1 = data[1].length;
    let length2 = data[2].length;
    let length3 = data[3].length;
    let length4 = data[4].length;
    //let minLength = Math.min(length1, length2, length3, length4);
    let minLength = Math.min(length1, length2, length3, length4);
    console.log(length1, length2, length3, length4)
    return minLength
}

function downloadCSV(trialName) {
    console.log("BEFORE BEFORE", getMinDataLength(acc_data), acc_data)
    acc_data = deleteChartData(acc_data);
    gyr_data = deleteChartData(gyr_data);
    var data_number = getMinDataLength(acc_data);

    endTimestamp = new Date().getTime();
    var trialDuration = endTimestamp - initTimestamp;
    var frequency  = (data_number - 1)/trialDuration
    const timeBetweenPointsMs = 1 / frequency;
    const timeBetweenPointsSec = timeBetweenPointsMs / 1000;

    var time_data = Array.from({ length: data_number }, (_, index) => (index * timeBetweenPointsSec).toFixed(3));
    console.log("BEFORE", getMinDataLength(acc_data), acc_data)
    for (let i = 1; i <= 4; i++) {
        acc_data[i].slice(-data_number);
        gyr_data[i].slice(-data_number);
    }
    console.log("AFTER", getMinDataLength(acc_data), acc_data)
    var combined_data = time_data.map(function (t, index) {
        if (acc_data[1][index].length === 3) {
            return [
                index,
                t,
                acc_data[1][index][0], acc_data[1][index][1], acc_data[1][index][2],
                gyr_data[1][index][0], gyr_data[1][index][1], gyr_data[1][index][2],
                acc_data[2][index][0], acc_data[2][index][1], acc_data[2][index][2],
                gyr_data[2][index][0], gyr_data[2][index][1], gyr_data[2][index][2],
                acc_data[3][index][0], acc_data[3][index][1], acc_data[3][index][2],
                gyr_data[3][index][0], gyr_data[3][index][1], gyr_data[3][index][2],
                acc_data[4][index][0], acc_data[4][index][1], acc_data[4][index][2],
                gyr_data[4][index][0], gyr_data[4][index][1], gyr_data[4][index][2],
            ];
        } else {
            return undefined;
        }
    });

    combined_data = combined_data.filter(function (element) {
        return element !== undefined;
    });

    export_data = false

    var headers = [
        "index",
        "time",
        "acc_data_x_1", "acc_data_y_1", "acc_data_z_1", "gyr_data_x_1", "gyr_data_y_1", "gyr_data_z_1",
        "acc_data_x_2", "acc_data_y_2", "acc_data_z_2", "gyr_data_x_2", "gyr_data_y_2", "gyr_data_z_2",
        "acc_data_x_3", "acc_data_y_3", "acc_data_z_3", "gyr_data_x_3", "gyr_data_y_3", "gyr_data_z_3",
        "acc_data_x_4", "acc_data_y_4", "acc_data_z_4", "gyr_data_x_4", "gyr_data_y_4", "gyr_data_z_4",
    ];
    combined_data.unshift(headers);

    // Datos adicionales
    var additionalData = [
        "TrialName:,"+trialName+",,,,,,,,,,,,,,,,,",
        "StartTime:,"+getFullDateTime(initTimestamp)+",,,,,,,,,,,,,,,,,",
        "EndTime:,"+getFullDateTime(endTimestamp)+",,,,,,,,,,,,,,,,,",
        "TrialDuration:,"+getTimeDiff(trialDuration)+",,,,,,,,,,,,,,,,,",
        "",
    ];

    // Combinar los datos de la cabecera y los datos adicionales
    var headersAndData = additionalData.concat(combined_data);
    var csvContent = "data:text/csv;charset=utf-8," + headersAndData.join("\n");

    var encodedUri = encodeURI(csvContent);
    var link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "gaitmelt_trial_" + trialName+ ".csv");
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    acc_data = {
        1: [[], [], []],
        2: [[], [], []],
        3: [[], [], []],
        4: [[], [], []],
    };

    gyr_data = {
        1: [[], [], []],
        2: [[], [], []],
        3: [[], [], []],
        4: [[], [], []],
    };
}