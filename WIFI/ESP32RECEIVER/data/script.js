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

function toggleTrialButton(buttonId) {
    var button = document.getElementById(buttonId);

    if (button) {
        if (button.classList.contains("on")) {
            button.innerText = "Iniciar ensayo";
            button.classList.remove("on");
            button.classList.add("off");
            buttonStates[buttonId] = false;
            downloadCSV()
        } else {
            button.innerText = "Detener ensayo";
            button.classList.remove("off");
            button.classList.add("on");
            buttonStates[buttonId] = true;
            export_data = true
        }
    }
}


function toggleMotorButton(buttonId, buttonNumber) {
    var button = document.getElementById(buttonId);

    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/motor" + String(buttonNumber), true);
    xhr.send();
    if (button) {
        if (button.classList.contains("on")) {
            button.innerText = "Motor apagado";
            button.classList.remove("on");
            button.classList.add("off");
            buttonStates[buttonId] = false;
        } else {
            button.innerText = "Motor encendido";
            button.classList.remove("off");
            button.classList.add("on");
            buttonStates[buttonId] = true;
            button.disabled = true;
            console.log("Vibrando...")
            setTimeout(() => {
                button.disabled = false;
                button.innerText = "Motor apagado";
                button.classList.remove("on");
                button.classList.add("off");
                buttonStates[buttonId] = false;
                console.log("Motor apagado")
              }, 2000);
        }
    }
}

document.getElementById("trial_button").addEventListener("click", function () {
    toggleTrialButton("trial_button");
});

for (var i = 1; i <= 4; i++) {
    (function (i) {
        document.getElementById("motor_button" + i).addEventListener("click", function () {
            toggleMotorButton("motor_button" + i, i);
        });
    })(i);
}

function deleteChartData(data){
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

    var combined_data = time_data.map(function(t, index) {
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
    
    combined_data = combined_data.filter(function(element) {
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
    
    var csvContent = "data:text/csv;charset=utf-8," + combined_data.map(function(row) {
        return row.join(",");
    }).join("\n");
    
    var encodedUri = encodeURI(csvContent);
    var link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "datos.csv");
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

if (!!window.EventSource) {
    var source = new EventSource('/events');
    source.addEventListener('open', function (e) {
        console.log("Events Connected");
    }, false);
    source.addEventListener('error', function (e) {
        if (e.target.readyState != EventSource.OPEN) {
            console.log("Events Disconnected");
        }
    }, false);

    source.addEventListener('message', function (e) {
        console.log("message", e.data);
    }, false);

    source.addEventListener('mpu_readings', function (e) {
        var obj = JSON.parse(e.data);
        var board_id = obj.board_id;
        var time = script_time[board_id - 1];
        var accData = [obj.acc_x, obj.acc_y, obj.acc_z];
        var gyrData = [obj.gyr_x, obj.gyr_y, obj.gyr_z];
        addData(acc_chart[board_id], time, accData);
        addData(gyr_chart[board_id], time, gyrData);
        if (export_data){
            acc_data[board_id].push(accData);
            gyr_data[board_id].push(gyrData);
        }
        script_time[board_id - 1] = script_time[board_id - 1] + 1;
    }, false);
}
