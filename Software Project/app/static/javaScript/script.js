var directionsService;
var directionsRenderer;
var map;
var journeyStarted = false;

function initMap() {
    directionsService = new google.maps.DirectionsService();
    directionsRenderer = new google.maps.DirectionsRenderer();

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function (position) {
            var userLocation = {
                lat: position.coords.latitude,
                lng: position.coords.longitude
            };

            var mapOptions = {
                zoom: 12,
                center: userLocation
            };

            map = new google.maps.Map(document.getElementById('map'), mapOptions);
            directionsRenderer.setMap(map);
        }, function () {
            var defaultLocation = { lat: 53.80815489338595, lng: -1.5439173678765745 };
            var mapOptions = {
                zoom: 7,
                center: defaultLocation
            };

            map = new google.maps.Map(document.getElementById('map'), mapOptions);
            directionsRenderer.setMap(map);
        });
    } else {
        var defaultLocation = { lat: 53.80815489338595, lng: -1.5439173678765745 };
        var mapOptions = {
            zoom: 7,
            center: defaultLocation
        };

        map = new google.maps.Map(document.getElementById('map'), mapOptions);
        directionsRenderer.setMap(map);
    }
}



function SubBox(){
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


function SignUp(){
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

function calculateRoute() {
    var origin = document.getElementById('origin').value;
    var destination = document.getElementById('destination').value;
    var waypoints = []; // Array to store waypoints
    var travelMode = document.getElementById('travel-mode').value;

    // Get all waypoints
    var waypointInputs = document.querySelectorAll('.waypoint-input');
    waypointInputs.forEach(function (input) {
        if (input.value !== '') {
            waypoints.push({
                location: input.value,
                stopover: true // Each waypoint is a stopover
            });
        }
    });

    var request = {
        origin: origin,
        destination: destination,
        waypoints: waypoints,
        optimizeWaypoints: false, // Optimize the order of waypoints for the shortest route
        travelMode: google.maps.TravelMode[travelMode]
    };

    directionsService.route(request, function (result, status) {
        if (status == 'OK') {
            directionsRenderer.setDirections(result);
            var totalDistance = 0;
            var totalDuration = 0;
            var legs = result.routes[0].legs;
            for (var i = 0; i < legs.length; ++i) {
                totalDistance += legs[i].distance.value;
                totalDuration += legs[i].duration.value;
            }
            totalDistance = totalDistance / 1000; // Convert meters to kilometers
            document.getElementById('total-distance').innerHTML = 'Total Distance: ' + totalDistance.toFixed(2) + ' km';
            document.getElementById('total-duration').innerHTML = 'Total Time: ' + formatDuration(totalDuration);
        }
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




function addWaypoint() {
    var waypointsContainer = document.getElementById('waypoints-container');
    var numWaypoints = waypointsContainer.querySelectorAll('.waypoint-input').length;
    var newWaypointInput = document.createElement('input');
    newWaypointInput.type = 'text';
    newWaypointInput.id = 'waypoint' + (numWaypoints + 1);
    newWaypointInput.className = 'waypoint-input';
    newWaypointInput.placeholder = 'Waypoint ' + (numWaypoints + 1);
    waypointsContainer.appendChild(document.createElement('br'));
    waypointsContainer.appendChild(newWaypointInput);
}

document.addEventListener('DOMContentLoaded', function () {
    const startBtn = document.getElementById('start-journey');
    const endBtn = document.getElementById('end-journey');

    startBtn.onclick = function () {
        const startLocation = document.getElementById('start-location').value;
        const userId = 1; // Example user ID, replace with dynamic data from your app

        fetch('/api/journeys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, start_location: startLocation })
        })
            .then(response => response.json())
            .then(data => {
                console.log(data.message);
                sessionStorage.setItem('currentJourneyId', data.journey_id);
                endBtn.disabled = false;
            });
    };

    endBtn.onclick = function () {
        const currentJourneyId = sessionStorage.getItem('currentJourneyId');
        const endLocation = document.getElementById('end-location').value;

        fetch(`/api/journeys/${currentJourneyId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ end_location: endLocation })
        })
            .then(response => response.json())
            .then(data => {
                console.log(data.message);
                sessionStorage.removeItem('currentJourneyId');
                endBtn.disabled = true;
            });
    };
});
