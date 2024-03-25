var map;
document.addEventListener('DOMContentLoaded', function () {
    var map = L.map('map').setView([51.505, -0.09], 13); // Default view

    // Function to set map view to user's current location
    function setLocation() {
        map.locate({ setView: true, maxZoom: 16 });
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);
    }
    map.on('locationfound', onLocationFound);
    map.on('locationerror', onLocationError);

    // Add event listener to the Draw button
    document.getElementById('drawRoute').addEventListener('click', function () {
        drawJourneyRoute();
    });
    setLocation();
});

function onLocationFound(e) {
    var radius = e.accuracy / 2;
    L.marker(e.latlng).addTo(map)
        .bindPopup("You are within " + radius + " meters from this point").openPopup();
    L.circle(e.latlng, radius).addTo(map);
}

function onLocationError(e) {
    alert(e.message);
}


function searchLocation(query, inputId) {
    if (query.length < 3) {
        document.getElementById(inputId + 'Suggestions').style.display = 'none';
        return; // Avoid too many requests for short queries
    }
    fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${query}`)
        .then(response => response.json())
        .then(data => {
            displaySuggestions(data, inputId);
        })
        .catch(error => console.error('Error:', error));
}

function displaySuggestions(data, inputId) {
    let suggestionsBox = document.getElementById(inputId + 'Suggestions');
    suggestionsBox.innerHTML = ''; // Clear previous suggestions
    if (data.length > 0) {
        data.forEach(item => {
            let div = document.createElement('div');
            div.innerHTML = item.display_name;
            div.className = 'suggestion-item';
            div.onclick = function () {
                if (inputId === 'waypoints') {
                    addWaypoint(item.display_name);
                    document.getElementById(inputId).value = ''; // Clear input for next waypoint
                } else {
                    document.getElementById(inputId).value = item.display_name;
                }
                suggestionsBox.style.display = 'none';
            };
            suggestionsBox.appendChild(div);
        });
        suggestionsBox.style.display = 'block';
    } else {
        suggestionsBox.style.display = 'none';
    }
}

function addWaypoint(waypoint) {
    let list = document.getElementById('waypointsList');
    let listItem = document.createElement('li');
    listItem.textContent = waypoint;
    list.appendChild(listItem);
}



function submitJourney() {
    const csrfToken = document.querySelector('input[name="csrf_token"]').value;
    const journeyData = {
        origin: document.getElementById('origin').value,
        destination: document.getElementById('destination').value,
        waypoints: document.getElementById('waypoints').value,
        time_taken: parseInt(document.getElementById('time_taken').value, 10),
    };


    fetch('/add-journey', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken,
        },
        body: JSON.stringify(journeyData),
    })
        .then(response => response.json())
        .then(data => {
            console.log(data);
            // Handle the response, e.g., showing a success message
        })
        .catch(error => console.error('Error:', error));

    // Draw the route on the map
    drawRoute(waypoints);
}

function drawJourneyRoute() {
    const waypointsInput = document.getElementById('waypoints').value;
    // Parse waypoints input into a format suitable for Leaflet (assuming semicolon-separated lat,lng pairs)
    const waypoints = waypointsInput.split(';').map(wp => {
        const [lat, lng] = wp.split(',').map(Number);
        return [lat, lng];
    });

    drawRoute(waypoints);
}

function drawRoute(waypoints) {
    // Check if a route already exists on the map; if so, remove it
    if (window.currentRoute) {
        map.removeLayer(window.currentRoute);
    }

    // Draw the new route
    window.currentRoute = L.polyline(waypoints, {
        color: 'blue',
        weight: 4,
        opacity: 0.7,
    }).addTo(map);

    // Zoom the map to fit the route
    map.fitBounds(window.currentRoute.getBounds());
}


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



function uploadGPX() {
    const fileInput = document.getElementById('gpxFile');
    if (fileInput.files.length > 0) {
        const file = fileInput.files[0];
        const reader = new FileReader();

        reader.onload = function (event) {
            // Parse the GPX file content
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(event.target.result, "text/xml");

            // Extract waypoints or track points from the GPX
            const trkpts = xmlDoc.getElementsByTagName("trkpt");
            const wpts = xmlDoc.getElementsByTagName("wpt"); // Use this if your GPX uses <wpt> elements
            const points = trkpts.length > 0 ? trkpts : wpts; // Choose track points or waypoints based on your GPX structure

            if (points.length > 0) {
                // Set origin to the first point
                const originLat = points[0].getAttribute("lat");
                const originLon = points[0].getAttribute("lon");
                document.getElementById("origin").value = `${originLat}, ${originLon}`;

                // Set destination to the last point
                const destLat = points[points.length - 1].getAttribute("lat");
                const destLon = points[points.length - 1].getAttribute("lon");
                document.getElementById("destination").value = `${destLat}, ${destLon}`;

                // Handle waypoints (if any) - concatenate intermediate points
                let waypointsValue = "";
                for (let i = 1; i < points.length - 1; i++) {
                    const lat = points[i].getAttribute("lat");
                    const lon = points[i].getAttribute("lon");
                    waypointsValue += `${lat}, ${lon}; `;
                }
                document.getElementById("waypoints").value = waypointsValue.trim();
            } else {
                alert("No route data found in the GPX file.");
            }
        };

        reader.readAsText(file);
    } else {
        alert("Please select a GPX file to upload.");
    }
}
