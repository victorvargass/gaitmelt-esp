import { disconnectDevice, isWebBluetoothEnabled, parseBytesToStruct, getDateTime } from './utils.js';

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
const timestamp_ps = [];
const bleStateContainers = [];
const timestampContainers = [];

var connectedDevices = 0;
var initTimestamp = 0;


const trialButton = document.getElementById('trialButton')
const timerDisplay = document.getElementById('timerDisplay')

for (let i = 1; i <= 4; i++) {
    connectButtons.push(document.getElementById(`connectBleButton${i}`));
    timestamp_ps.push(document.getElementById(`timestamp_p${i}`));
    motorButtons.push(document.getElementById(`motorButton${i}`));
    bleStateContainers.push(document.getElementById(`bleState${i}`));
    timestampContainers.push(document.getElementById(`timestamp${i}`));
}

var bleServer = []
var bleServiceFound = [];
var sensorCharacteristicFound = [];


for (let i = 0; i < connectButtons.length; i++) {
    connectButtons[i].addEventListener('click', () => {
        var button = connectButtons[i]
        if (button.classList.contains("disconnected") && isWebBluetoothEnabled(bleStateContainers[i])) {
            connectToDevice(
                bleServices[i], bleStateContainers[i], sensorCharacteristics[i], timestampContainers[i], i)
        }
        else if (button.classList.contains("connected")) {
            disconnectDevice(bleStateContainers[i], bleServer[i], sensorCharacteristicFound[i], i);
        }
    });
}

function onDisconnected(event, bleService, bleStateContainer, sensorCharacteristic, timestampContainer, index) {
    console.log('Device Disconnected:', event.target.device.name);
    bleStateContainer.innerHTML = "Dispositivo desconectado";
    bleStateContainer.style.color = "#d13a30";

    connectToDevice(
        bleService, bleStateContainer, sensorCharacteristic, timestampContainer, index)
}

function handleCharacteristicChange(event, timestampContainer) {
    const newValueReceived = parseBytesToStruct(event.target.value.buffer);
    var board_id = newValueReceived.id;
    var time = script_time[board_id - 1];
    var accData = [newValueReceived.acc_x, newValueReceived.acc_y, newValueReceived.acc_z];
    var gyrData = [newValueReceived.gyr_x, newValueReceived.gyr_y, newValueReceived.gyr_z];
    addData(acc_chart[board_id], time, accData);
    addData(gyr_chart[board_id], time, gyrData);
    if (export_data) {
        acc_data[board_id].push(accData);
        gyr_data[board_id].push(gyrData);
    }
    script_time[board_id - 1] = script_time[board_id - 1] + 1;
    timestampContainer.innerHTML = getDateTime();
}

// Connect to BLE Device and Enable Notifications
function connectToDevice(bleService, bleStateContainer, sensorCharacteristic, timestampContainer, index) {
    var connectButton = connectButtons[index]
    var motorButton = motorButtons[index]
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
                    sensorCharacteristic, timestampContainer, index
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
            characteristic.addEventListener('characteristicvaluechanged', function (event) {
                handleCharacteristicChange(event, timestampContainer);
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
            timestamp_p.classList.remove("disconnected");
            timestamp_p.classList.add("connected");
            connectedDevices++;
            console.log("Number of connected devices: ", connectedDevices)
            if (connectedDevices == 4){
                trialButton.classList.remove("nodata");
            };
            return characteristic.readValue();
        })
        .then(value => {
            //console.log("Read value: ", value);
            const decodedValue = parseBytesToStruct(value.buffer)
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
            timestamp_p.classList.remove("connected");
            timestamp_p.classList.add("disconnected");

            bleStateContainer.innerHTML = "Error de conexión. Vuelve a intentarlo";
            bleStateContainer.style.color = "#d13a30";
        })
}

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
var script_time = [0, 0, 0, 0];

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
                button.innerText = "Iniciar ensayo";
                button.classList.remove("on");
                button.classList.add("off");
                buttonStates[buttonId] = false;
                downloadCSV()
                timerDisplay.classList.add("stop")
                clearInterval(timerInterval);
            }
        } else {
            const currentDate = new Date();
            const timestamp = currentDate.getTime();
            initTimestamp = timestamp.toString();

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
            button.disabled = true;
            console.log("Vibrando...")
            setTimeout(() => {
                button.disabled = false;
                button.innerText = "Activar motor";
                button.classList.remove("on");
                button.classList.add("off");
                buttonStates[buttonId] = false;
                console.log("Motor apagado")
            }, 2000);
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
    let minLength = Math.min(length1, length2, length3, length4);
    return minLength
}

function downloadCSV() {
    acc_data = deleteChartData(acc_data);
    gyr_data = deleteChartData(gyr_data);
    var data_number = getMinDataLength(acc_data);
    var time_data = Array.from({ length: data_number }, (_, index) => (index * 0.1).toFixed(1));
    var combined_data = time_data.map(function (t, index) {
        if (acc_data[1][index].length === 3) {
            return [
                index,
                t,
                acc_data[1][index][0], acc_data[1][index][1], acc_data[1][index][2], gyr_data[1][index][0], gyr_data[1][index][1], gyr_data[1][index][2],
                acc_data[2][index][0], acc_data[2][index][1], acc_data[2][index][2], gyr_data[2][index][0], gyr_data[2][index][1], gyr_data[2][index][2],
                acc_data[3][index][0], acc_data[3][index][1], acc_data[3][index][2], gyr_data[3][index][0], gyr_data[3][index][1], gyr_data[3][index][2],
                acc_data[4][index][0], acc_data[4][index][1], acc_data[4][index][2], gyr_data[4][index][0], gyr_data[4][index][1], gyr_data[4][index][2],
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

    var csvContent = "data:text/csv;charset=utf-8," + combined_data.map(function (row) {
        return row.join(",");
    }).join("\n");

    var encodedUri = encodeURI(csvContent);
    var link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "gaitmelt_trial_" + initTimestamp + ".csv");
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


function createChart(chartId, mpu_data, label, title, yAxisLabel, dataSetColors, minValue, maxValue) {
    var ctx = document.getElementById(chartId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: mpu_data.map(function (dataSet, index) {
                return {
                    label: label[index],
                    data: dataSet,
                    borderColor: dataSetColors[index],
                    backgroundColor: 'transparent',
                    pointRadius: 1,
                    pointBackgroundColor: dataSetColors[index],
                    fill: false
                };
            })
        },
        options: {
            responsive: true,
            plugins: {
                title: {
                    display: true,
                    text: title
                }
            },
            scales: {
                x: {
                    type: 'category',
                    position: 'bottom',
                    title: {
                        display: true,
                        text: 'Tiempo (s)'
                    },
                    ticks: {
                        maxTicksLimit: 6
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: yAxisLabel
                    },
                    suggestedMin: minValue,
                    suggestedMax: maxValue
                }
            }
        }
    });
}

var acc_chart = {};
var gyr_chart = {};
var accSetColors = ['red', 'blue', 'green'];
var gyrSetColors = ['purple', 'orange', 'pink'];


for (var i = 1; i <= 4; i++) {
    acc_chart[i] = createChart('acc_chart_' + i, acc_data[i], ['x', 'y', 'z'], "Acelerómetro", 'Acceleración (m/s^2)', accSetColors, -20, 20);
    gyr_chart[i] = createChart('gyr_chart_' + i, gyr_data[i], ['x', 'y', 'z'], "Giroscopio", 'Radianes', gyrSetColors, -6, 6);
}

function addData(chart, time, newData) {
    var timeInSeconds = Math.floor(time / 10); // Convertir a segundos
    chart.data.labels.push(timeInSeconds.toString());

    newData.forEach(function (data, index) {
        chart.data.datasets[index].data.push({ x: timeInSeconds, y: data });
    });

    var maxDataPoints = 50;
    if (chart.data.labels.length > maxDataPoints) {
        chart.data.labels.shift();
        chart.data.datasets.forEach(function (dataset) {
            dataset.data.shift();
        });
    }
    chart.update('none');
}