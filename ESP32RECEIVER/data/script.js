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

var buttonStates = {
    1: false,
    2: false,
    3: false,
    4: false,
};

function toggleButton(buttonId, buttonNumber) {
    console.log(buttonId);
    var button = document.getElementById(buttonId);

    var xhr = new XMLHttpRequest();
    xhr.open("GET", "/led" + String(buttonNumber), true);
    //xhr.open("GET", "/motor" + String(buttonNumber), true);
    xhr.send();
    if (button) {
        if (button.classList.contains("on")) {
            button.innerText = "Apagado";
            button.classList.remove("on");
            button.classList.add("off");
            buttonStates[buttonId] = false;
        } else {
            button.innerText = "Encendido";
            button.classList.remove("off");
            button.classList.add("on");
            buttonStates[buttonId] = true;
        }
    }
}

for (var i = 1; i <= 4; i++) {
    (function (i) {
        console.log(i, "button" + i);
        document.getElementById("button" + i).addEventListener("click", function () {
            toggleButton("button" + i, i);
        });
    })(i);
}

function createChart(chartId, data, label, title, yAxisLabel, dataSetColors) {
    var ctx = document.getElementById(chartId).getContext('2d');
    return new Chart(ctx, {
        type: 'line',
        data: {
            labels: [],
            datasets: data.map(function (dataSet, index) {
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
                    type: 'linear',
                    position: 'bottom',
                    title: {
                        display: true,
                        text: 'Tiempo'
                    }
                },
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: yAxisLabel
                    }
                }
            }
        }
    });
}

var acc_chart = {};
var gyr_chart = {};
var accSetColors = ['red', 'blue', 'green'];
var gyrSetColors = ['purple', 'orange', 'pink'];

var script_time = 0;


for (var i = 1; i <= 4; i++) {
    acc_chart[i] = createChart('acc_chart_' + i, acc_data[i], ['acc_x', 'acc_y', 'acc_z'], "Acelerómetro", 'Acceleración (m/s^2)', accSetColors);
    gyr_chart[i] = createChart('gyr_chart_' + i, gyr_data[i], ['gyr_x', 'gyr_y', 'gyr_z'], "Giroscopio", 'Radianes', gyrSetColors);
}

function addData(chart, time, newData) {
    chart.data.labels.push(time.toString());
    newData.forEach(function (data, index) {
        chart.data.datasets[index].data.push({ x: time, y: data });
    });

    var maxDataPoints = 20;
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
        var time = script_time;
        var board_id = obj.board_id;
        var accData = [obj.acc_x, obj.acc_y, obj.acc_z];
        var gyrData = [obj.gyr_x, obj.gyr_y, obj.gyr_z];
        addData(acc_chart[board_id], time, accData);
        addData(gyr_chart[board_id], time, gyrData);
    }, false);
}
