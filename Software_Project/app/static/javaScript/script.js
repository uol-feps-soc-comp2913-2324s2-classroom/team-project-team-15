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

    // Initialize location
    setLocation();

    // Rest of your functions (searchLocation, displaySuggestions, etc.)
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

// Initialize location
setLocation();

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
        waypoints: document.getElementById('waypoints').value, // Ensure this is formatted correctly if it's meant to be JSON
        time_taken: parseInt(document.getElementById('time_taken').value, 10),
    };

    fetch('/add-journey', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken, // Include the CSRF token in the request headers
        },
        body: JSON.stringify(journeyData),
    })
        .then(response => response.json())
        .then(data => {
            // Handle the response
        })
        .catch(error => console.error('Error:', error));
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
