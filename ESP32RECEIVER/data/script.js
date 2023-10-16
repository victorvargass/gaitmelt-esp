// script.js
if (!!window.EventSource) {
    var source = new EventSource('/events');
    console.log(source)
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

    source.addEventListener('new_readings', function (e) {
        console.log("new_readings", e.data);
        var obj = JSON.parse(e.data);
        console.log(obj)
        /*
        obj.acc_x
        obj.acc_y
        obj.acc_z
        obj.gyr_x
        obj.gyr_y
        obj.gyr_z
        */
    }, false);


    // Variables para almacenar los datos de las 4 gráficas (6 variables cada una)
    var data1 = [[], [], [], [], [], []];
    var data2 = [[], [], [], [], [], []];
    var data3 = [[], [], [], [], [], []];
    var data4 = [[], [], [], [], [], []];

    // Variables para almacenar el estado de los botones (apagado o encendido)
    var buttonState1 = false;
    var buttonState2 = false;
    var buttonState3 = false;
    var buttonState4 = false;

    // Función para cambiar el estado del botón y actualizar su estilo
    function toggleButton(buttonId) {
        var button = document.getElementById(buttonId);
        if (button) {
            if (button.classList.contains("on")) {
                button.innerText = "Apagado";
                button.classList.remove("on");
                button.classList.add("off");
                buttonState1 = false;
            } else {
                button.innerText = "Encendido";
                button.classList.remove("off");
                button.classList.add("on");
                buttonState1 = true;
            }
        }
    }

    // Agrega un evento de clic a cada botón para cambiar su estado y estilo
    document.getElementById("button1").addEventListener("click", function () {
        toggleButton("button1");
    });

    document.getElementById("button2").addEventListener("click", function () {
        toggleButton("button2");
    });

    document.getElementById("button3").addEventListener("click", function () {
        toggleButton("button3");
    });

    document.getElementById("button4").addEventListener("click", function () {
        toggleButton("button4");
    });

    function createChart(chartId, data) {
        var ctx = document.getElementById(chartId).getContext('2d');
        return new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'acc_x',
                        data: data[0],
                        borderColor: 'red',
                        backgroundColor: 'transparent', // Fondo transparente para mostrar puntos
                        pointRadius: 3, // Tamaño de los puntos
                        pointBackgroundColor: 'red', // Color de los puntos
                        fill: false
                    },
                    {
                        label: 'acc_y',
                        data: data[1],
                        borderColor: 'blue',
                        backgroundColor: 'transparent',
                        pointRadius: 3,
                        pointBackgroundColor: 'blue',
                        fill: false
                    },
                    {
                        label: 'acc_z',
                        data: data[2],
                        borderColor: 'green',
                        backgroundColor: 'transparent',
                        pointRadius: 3,
                        pointBackgroundColor: 'green',
                        fill: false
                    },
                    {
                        label: 'gyr_x',
                        data: data[3],
                        borderColor: 'purple',
                        backgroundColor: 'transparent',
                        pointRadius: 3,
                        pointBackgroundColor: 'purple',
                        fill: false
                    },
                    {
                        label: 'gyr_y',
                        data: data[4],
                        borderColor: 'orange',
                        backgroundColor: 'transparent',
                        pointRadius: 3,
                        pointBackgroundColor: 'orange',
                        fill: false
                    },
                    {
                        label: 'gyr_z',
                        data: data[5],
                        borderColor: 'pink',
                        backgroundColor: 'transparent',
                        pointRadius: 3,
                        pointBackgroundColor: 'pink',
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: {
                        type: 'linear',
                        position: 'bottom',
                        title: {
                            display: true,
                            text: 'Tiempo' // Etiqueta del eje X
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Valor' // Etiqueta del eje Y
                        }
                    }
                }
            }
        });
    }

    // Crea los 4 gráficos
    var chart1 = createChart('chart1', data1);
    var chart2 = createChart('chart2', data2);
    var chart3 = createChart('chart3', data3);
    var chart4 = createChart('chart4', data4);

    var time = 0;

    function generateRandomMPU6050Data() {
        // Genera valores aleatorios para el acelerómetro (rango típico de valores en m/s^2)
        var accelerometerX = Math.random() * 4 - 2; // Valor entre -2 y 2 m/s^2
        var accelerometerY = Math.random() * 4 - 2;
        var accelerometerZ = Math.random() * 4 - 2;

        // Genera valores aleatorios para el giroscopio (rango típico de valores en radianes por segundo)
        var gyroscopeX = Math.random() * 0.2 - 0.1; // Valor entre -0.1 y 0.1 rad/s
        var gyroscopeY = Math.random() * 0.2 - 0.1;
        var gyroscopeZ = Math.random() * 0.2 - 0.1;

        var newData = [
            accelerometerX,
            accelerometerY,
            accelerometerZ,
            gyroscopeX,
            gyroscopeY,
            gyroscopeZ
        ];

        return newData;
    }

    // Simula la generación de datos en tiempo real para cada gráfica
    setInterval(function () {
        var newData1 = generateRandomMPU6050Data();
        var newData2 = generateRandomMPU6050Data();
        var newData3 = generateRandomMPU6050Data();
        var newData4 = generateRandomMPU6050Data();

        addData(chart1, time, newData1);
        addData(chart2, time, newData2);
        addData(chart3, time, newData3);
        addData(chart4, time, newData4);
        time++;
    }, 1500); // Actualiza cada segundo

    // Función para agregar nuevos datos a un gráfico
    function addData(chart, time, newData) {
        chart.data.labels.push(time.toString()); // Agrega un tiempo como etiqueta
        for (var i = 0; i < 6; i++) {
            chart.data.datasets[i].data.push({ x: time, y: newData[i] });
        }

        // Limita la cantidad de puntos mostrados en el gráfico a 20
        var maxDataPoints = 10;
        if (chart.data.labels.length > maxDataPoints) {
            chart.data.labels.shift();
            for (var i = 0; i < 6; i++) {
                chart.data.datasets[i].data.shift();
            }
        }
        // Actualiza el gráfico
        chart.update();
    }
}