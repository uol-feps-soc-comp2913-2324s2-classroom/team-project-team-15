// var routingControl;
// var map;


// document.addEventListener('DOMContentLoaded', function () {
//     map = L.map('map').setView([51.505, -0.09], 13); // Default view

//     // Function to set map view to user's current location
//     function setLocation() {
//         map.locate({ setView: true, maxZoom: 16 });
//         L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
//             attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
//         }).addTo(map);
//     }
//     map.on('locationfound', onLocationFound);
//     map.on('locationerror', onLocationError);

//     // Initialize location
//     setLocation();

//     // Initialize the geocoder
//     var geocoder = L.Control.geocoder({
//         geocoder: L.Control.Geocoder.nominatim,
//         defaultMarkGeocode: false,
//     }).addTo(map);

//     // Rest of your functions (searchLocation, displaySuggestions, etc.)
//     // Initialize routing control
//     routingControl = L.Routing.control({
//         waypoints: [],
//         routeWhileDragging: true,
//         geocoder: L.Control.Geocoder.nominatim,
//         lineOptions: {
//             styles: [{ color: '#007bff', opacity: 1, weight: 5 }]
//         }
//     }).addTo(map);

// });





// function onLocationFound(e) {
//     var radius = e.accuracy / 2;
//     L.marker(e.latlng).addTo(map)
//         .bindPopup("You are within " + radius + " meters from this point").openPopup();
//     L.circle(e.latlng, radius).addTo(map);
// }

// function onLocationError(e) {
//     alert(e.message);
// }

// // // Initialize location
// // setLocation();

// function searchLocation(query, inputId) {
//     if (query.length < 3) {
//         document.getElementById(inputId + 'Suggestions').style.display = 'none';
//         return; // Avoid too many requests for short queries
//     }
//     fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`)
//         .then(response => response.json())
//         .then(data => {
//             displaySuggestions(data, inputId);
//         })
//         .catch(error => console.error('Error:', error));
// }

// function displaySuggestions(data, inputId) {
//     let suggestionsBox = document.getElementById(inputId + 'Suggestions');
//     suggestionsBox.innerHTML = ''; // Clear previous suggestions
//     if (data.length > 0) {
//         data.forEach(item => {
//             let div = document.createElement('div');
//             div.innerHTML = item.display_name;
//             div.className = 'suggestion-item';
//             div.onclick = function () {
//                 if (inputId === 'waypoints') {
//                     addWaypoint(item.display_name);
//                     document.getElementById(inputId).value = ''; // Clear input for next waypoint
//                 } else {
//                     document.getElementById(inputId).value = item.display_name;
//                 }
//                 suggestionsBox.style.display = 'none';
//             };
//             suggestionsBox.appendChild(div);
//         });
//         suggestionsBox.style.display = 'block';
//     } else {
//         suggestionsBox.style.display = 'none';
//     }
// }

// function addWaypoint(waypoint) {
//     let list = document.getElementById('waypointsList');
//     let listItem = document.createElement('li');
//     listItem.textContent = waypoint;
//     list.appendChild(listItem);
// }

// function submitJourney() {
//     const origin = document.getElementById('origin').value;
//     const destination = document.getElementById('destination').value;
//     const waypointsInput = document.getElementById('waypoints').value;
//     const waypoints = waypointsInput ? waypointsInput.split(',').map(wp => wp.trim()) : [];
//     const time_taken = parseInt(document.getElementById('time_taken').value, 10);

//     // Construct journey data
//     const journeyData = {
//         origin: origin,
//         destination: destination,
//         waypoints: waypoints.join(','),
//         time_taken: time_taken,
//     };

//     // Send journey data to server
//     const csrfToken = document.querySelector('input[name="csrf_token"]').value;
//     fetch('/add-journey', {
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',
//             'X-CSRFToken': csrfToken,
//         },
//         body: JSON.stringify(journeyData),
//     })
//         .then(response => response.json())
//         .then(data => {
//             // Handle the server response if needed

//             // Geocode the origin, destination, and waypoints
//             const geocodePromises = [ // Create the list of promises
//                 geocodeAddress(origin),
//                 geocodeAddress(destination),
//                 ...waypoints.map(geocodeAddress)
//             ];

//             Promise.all(geocodePromises) // Return the Promise.all call
//                 .then(([originLatLng, destinationLatLng, ...waypointLatLngs]) => {
//                     // Calculate route and display on map
//                     var routingOptions = {
//                         waypoints: [
//                             L.latLng(...originLatLng),
//                             ...waypointLatLngs.map(latlng => L.latLng(...latlng)),
//                             destinationLatLng
//                         ],
//                         routeWhileDragging: true,
//                         geocoder: L.Control.Geocoder.nominatim(),
//                         lineOptions: {
//                             styles: [{ color: '#007bff', opacity: 1, weight: 5 }]
//                         }
//                     };
//                     if (routingControl) { // Check if routingControl is initialized
//                         map.removeControl(routingControl); // Remove existing routing control
//                     }
//                     routingControl = L.Routing.control(routingOptions).addTo(map);
//                 })
//                 .catch(error => console.error('Error:', error));
//         })
//         .catch(error => console.error('Error:', error));
// }



// async function geocodeAddress(address) {
//     const apiUrl = 'https://nominatim.openstreetmap.org/search';
//     const params = {
//         format: 'json',
//         q: address,
//         addressdetails: 1,
//         polygon: 0,
//         limit: 1
//     };

//     try {
//         const response = await fetch(`${apiUrl}?${new URLSearchParams(params)}`);
//         const data = await response.json();

//         if (data.length > 0) {
//             const latlng = data[0].lat + ',' + data[0].lon;
//             return [parseFloat(data[0].lat), parseFloat(data[0].lon)];
//         } else {
//             throw new Error('Address not found');
//         }
//     } catch (error) {
//         console.error('Error geocoding address:', error);
//         return null;
//     }
// }
function SubBox() {
    const form1 = document.getElementById("popupForm1");
    const form2 = document.getElementById("popupForm2");
    const overlay1 = document.getElementById("overlay1");
    const closeFormButton2 = document.getElementById("closeForm2");
    form1.style.display = "none";
    form2.style.display = "block";


    // If close button is clicked, the form, overlay should disappear
    closeFormButton2.addEventListener("click", function () {
        form2.style.display = "none";
        overlay1.style.display = "none";
    });
}

function SignUp() {
    const form1 = document.getElementById("popupForm1");
    const overlay1 = document.getElementById("overlay1");
    const closeFormButton1 = document.getElementById("closeForm1");

    form1.style.display = "block";
    overlay1.style.display = "block";

    // If close button is clicked, the form, overlay should disappear
    closeFormButton1.addEventListener("click", function () {
        form1.style.display = "none";
        overlay1.style.display = "none";
    });
}


function formatDuration(seconds) {
    var hours = Math.floor(seconds / 3600);
    var minutes = Math.floor((seconds % 3600) / 60);
    var remainingSeconds = seconds % 60;
    var formattedDuration = hours + " hour(s) " + minutes + " minute(s) " + remainingSeconds + " second(s)";
    return formattedDuration;
}

const revenueData = JSON.parse('{{ revenue_data | tojson | safe }}');
const labels = revenueData.map(item => item[0]);
const data = revenueData.map(item => item[1]);
// Create the chart
const ctx = document.getElementById('lineChart').getContext('2d');
const chart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: labels,
        datasets: [{
            label: 'Weekly Revenue Projection',
            data: data,
            borderColor: 'orange',
            backgroundColor: 'rgba(0, 0, 255, 0.1)',
        }]
    },
    options: {
        scales: {
            xAxes: [{
                scaleLabel: {
                    display: true,
                    labelString: 'Weeks'
                }
            }],
            yAxes: [{
                scaleLabel: {
                    display: true,
                    labelString: 'Revenue'
                }
            }]
        }
    }
});


function editRow2() {
    const form = document.getElementById("popupForm4");
    const overlay = document.getElementById("overlay4");
    const closeFormButton = document.getElementById("closeForm");



    // Displaying the form, overlay
    form.style.display = "block";
    overlay.style.display = "block";

    // If close button is clicked, the form, overlay should disappear
    closeFormButton.addEventListener("click", function () {
        form.style.display = "none";
        overlay.style.display = "none";
    });
}

// function uploadGPX() {
//     const fileInput = document.getElementById('gpxFile');
//     if (fileInput.files.length > 0) {
//         const file = fileInput.files[0];
//         const reader = new FileReader();

//         reader.onload = function (event) {
//             // Parse the GPX file content
//             const parser = new DOMParser();
//             const xmlDoc = parser.parseFromString(event.target.result, "text/xml");

//             // Extract waypoints or track points from the GPX
//             const trkpts = xmlDoc.getElementsByTagName("trkpt");
//             const wpts = xmlDoc.getElementsByTagName("wpt"); // Use this if your GPX uses <wpt> elements
//             const points = trkpts.length > 0 ? trkpts : wpts; // Choose track points or waypoints based on your GPX structure

//             if (points.length > 0) {
//                 // Set origin to the first point
//                 const originLat = points[0].getAttribute("lat");
//                 const originLon = points[0].getAttribute("lon");
//                 document.getElementById("origin").value = `${originLat}, ${originLon}`;

//                 // Set destination to the last point
//                 const destLat = points[points.length - 1].getAttribute("lat");
//                 const destLon = points[points.length - 1].getAttribute("lon");
//                 document.getElementById("destination").value = `${destLat}, ${destLon}`;

//                 // Handle waypoints (if any) - concatenate intermediate points
//                 let waypointsValue = "";
//                 for (let i = 1; i < points.length - 1; i++) {
//                     const lat = points[i].getAttribute("lat");
//                     const lon = points[i].getAttribute("lon");
//                     waypointsValue += `${lat}, ${lon}; `;
//                 }
//                 document.getElementById("waypoints").value = waypointsValue.trim();
//             } else {
//                 alert("No route data found in the GPX file.");
//             }
//         };

//         reader.readAsText(file);
//     } else {
//         alert("Please select a GPX file to upload.");
//     }
// }
