export function isWebBluetoothEnabled(bleStateContainer) {
    if (!navigator.bluetooth) {
        console.log('Web Bluetooth API is not available in this browser!');
        bleStateContainer.innerHTML = "Web Bluetooth API is not available in this browser/device!";
        return false
    }
    console.log('Web Bluetooth API supported in this browser.');
    return true
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

export function getTimeDiff(timestamp) {
    var time = new Date(timestamp);
    var minutes = ("0" + time.getMinutes()).slice(-2); // Agrega un cero inicial si el minuto es de un solo dígito
    var seconds = ("0" + time.getSeconds()).slice(-2); // Agrega un cero inicial si el segundo es de un solo dígito
    var milliseconds = ("00" + time.getMilliseconds()).slice(-3); // Agrega ceros iniciales si los milisegundos son de menos de 3 dígitos
    var datetime = "00:" + minutes + ":" + seconds + "." + milliseconds;
    return datetime;
}

export function getFullDateTime(timestamp) {
    var date = new Date(timestamp);
    var year = date.getFullYear();
    var month = ("0" + (date.getMonth() + 1)).slice(-2); // Agrega un cero inicial si el mes es de un solo dígito
    var day = ("0" + date.getDate()).slice(-2); // Agrega un cero inicial si el día es de un solo dígito
    var hours = ("0" + date.getHours()).slice(-2); // Agrega un cero inicial si la hora es de un solo dígito
    var minutes = ("0" + date.getMinutes()).slice(-2); // Agrega un cero inicial si el minuto es de un solo dígito
    var seconds = ("0" + date.getSeconds()).slice(-2); // Agrega un cero inicial si el segundo es de un solo dígito
    var milliseconds = ("00" + date.getMilliseconds()).slice(-3); // Agrega ceros iniciales si los milisegundos son de menos de 3 dígitos

    var datetime = day + "/" + month + "/" + year + " at " + hours + ":" + minutes + ":" + seconds + "." + milliseconds;
    return datetime;
}