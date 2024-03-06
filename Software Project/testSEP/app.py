from flask import Flask, render_template, request
import googlemaps

app = Flask(__name__)

gmaps = googlemaps.Client(key='AIzaSyC_IDAXXGAVJYlMrrRt6gpBDhumrkQ-CbY')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        origin = request.form['origin']
        destination = request.form['destination']

        directions_result = gmaps.directions(origin, destination)
        distance = directions_result[0]['legs'][0]['distance']['text']
        route = directions_result[0]['legs'][0]['steps']

        return render_template('index.html', distance=distance, route=route)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)