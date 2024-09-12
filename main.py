from flask import Flask, redirect, request, session, url_for, render_template_string
import requests
import base64
import json

app = Flask(__name__)
app.secret_key = 'secret key'

# Spotify API credentials
CLIENT_ID = 'id'
CLIENT_SECRET = 'secret key'
REDIRECT_URI = 'http://127.0.0.1:5000/callback'
SCOPE = ('user-read-private user-read-playback-state user-modify-playback-state user-read-currently-playing '
         'app-remote-control streaming playlist-read-private playlist-read-collaborative')

AUTH_URL = 'https://accounts.spotify.com/authorize'
TOKEN_URL = 'https://accounts.spotify.com/api/token'


@app.route('/')
def home():
    return render_template_string('''
    <html>
    <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:400,700">
        <style>
            body {
                font-family: 'Roboto', sans-serif;
                background-color: #121212;
                color: white;
                text-align: center;
            }
            a {
                color: #1DB954;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
            h1, h2 {
                margin: 20px 0;
            }
        </style>
    </head>
    <body>
        <h1>Welcome to Spotify Authorization!</h1>
        <a href="/login">Login with Spotify</a>
    </body>
    </html>
    ''')


@app.route('/login')
def login():
    auth_query_parameters = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': SCOPE
    }
    auth_url = f"{AUTH_URL}?response_type=code&client_id={CLIENT_ID}&redirect_uri={REDIRECT_URI}&scope={SCOPE}"
    return redirect(auth_url)


@app.route('/callback')
def callback():
    auth_code = request.args.get('code')

    auth_header = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode('utf-8')
    headers = {'Authorization': f'Basic {auth_header}'}
    payload = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI
    }

    response = requests.post(TOKEN_URL, headers=headers, data=payload)
    response_data = response.json()

    session['access_token'] = response_data['access_token']
    session['refresh_token'] = response_data['refresh_token']

    return redirect(url_for('profile'))


@app.route('/profile')
def profile():
    access_token = session.get('access_token')

    if not access_token:
        return redirect(url_for('login'))

    headers = {'Authorization': f'Bearer {access_token}'}

    profile_response = requests.get('https://api.spotify.com/v1/me', headers=headers)
    profile_data = profile_response.json()

    playlist_url = 'https://api.spotify.com/v1/me/playlists'
    playlists = []
    while playlist_url:
        playlist_response = requests.get(playlist_url, headers=headers)
        playlist_data = playlist_response.json()
        playlists.extend(playlist_data['items'])
        playlist_url = playlist_data.get('next')

    html = f'''
    <html>
    <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:400,700">
        <style>
            body {{
                font-family: 'Roboto', sans-serif;
                background-color: #121212;
                color: white;
                text-align: left;
                padding: 20px;
            }}
            h1, h2 {{
                margin: 20px 0;
            }}
            ul {{
                list-style-type: none;
                padding: 0;
            }}
            li {{
                margin: 10px 0;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 5px 10px;
                border-radius: 4px;
                cursor: pointer;
                transition: background 0.3s;
            }}
            li:hover {{
                background-color: #282828;
            }}
            img {{
                border-radius: 4px;
                width: 50px;
                height: 50px;
                margin-right: 10px;
            }}
            .playlist-info {{
                display: flex;
                align-items: center;
                flex: 1;
                text-decoration: none; /* Remove underline from links */
                color: white; /* Ensure text color is white */
            }}
            .playlist-details {{
                flex: 1;
                display: flex;
                flex-direction: column;
            }}
            .playlist-name {{
                font-size: 16px;
                margin: 0;
                color: white; /* Set playlist name color to white */
            }}
            .track-count {{
                font-size: 14px;
                color: lightgray; /* Set track count color to light gray */
                margin: 0;
            }}
            button {{
                background-color: #1DB954;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
            }}
            button:hover {{
                background-color: #1ed760;
            }}
        </style>
    </head>
    <body>
        <h1>Welcome, {profile_data["display_name"]}</h1>
        <img src="{profile_data["images"][0]["url"]}" alt="Profile Picture">
        <h2>Your Playlists:</h2>
        <ul>
    '''
    if playlists:
        for playlist in playlists:
            playlist_id = playlist['id']
            playlist_image = playlist['images'][0]['url'] if playlist['images'] else ''
            html += f'''
            <li>
                <a href="{url_for("playlist_tracks", playlist_id=playlist_id)}" class="playlist-info">
                    <img src="{playlist_image}" alt="Playlist Image">
                    <div class="playlist-details">
                        <p class="playlist-name">{playlist["name"]}</p>
                        <p class="track-count">{playlist["tracks"]["total"]} tracks</p>
                    </div>
                </a>
            </li>
            '''
        html += '</ul>'
    else:
        html += '<p>You have no playlists in your library.</p>'

    html += '<a href="/logout"><button>Logout</button></a>'
    html += '</body></html>'

    return html


@app.route('/playlist/<playlist_id>', methods=['GET', 'POST'])
def playlist_tracks(playlist_id):
    access_token = session.get('access_token')

    if not access_token:
        return redirect(url_for('login'))

    headers = {'Authorization': f'Bearer {access_token}'}

    # Fetch playlist details
    playlist_url = f'https://api.spotify.com/v1/playlists/{playlist_id}'
    playlist_response = requests.get(playlist_url, headers=headers)
    playlist_data = playlist_response.json()

    # Fetch all tracks from the playlist
    tracks_url = f'https://api.spotify.com/v1/playlists/{playlist_id}/tracks'
    tracks = []

    while tracks_url:
        tracks_response = requests.get(tracks_url, headers=headers)
        tracks_data = tracks_response.json()
        tracks.extend(tracks_data['items'])
        tracks_url = tracks_data.get('next')

    if request.method == 'POST':
        start_index = int(request.form['start_song'])
        end_index = int(request.form['end_song'])

        # Validate the indexes
        if start_index >= 0 and end_index < len(tracks) and start_index < end_index:
            selected_songs = [tracks[i]['track']['uri'] for i in range(start_index, end_index + 1)]
            session['selected_songs'] = selected_songs
            session['start_song'] = start_index
            session['end_song'] = end_index

            # Start playback
            start_playback(selected_songs, access_token)

            return redirect(url_for('success'))

    # Calculate total duration and other details
    total_duration_ms = sum(item['track']['duration_ms'] for item in tracks)
    total_duration = f"{total_duration_ms // 60000}:{(total_duration_ms // 1000) % 60:02}"
    total_tracks = len(tracks)
    playlist_name = playlist_data['name']
    playlist_author = playlist_data['owner']['display_name']
    playlist_image = playlist_data['images'][0]['url'] if playlist_data['images'] else ''
    playlist_description = playlist_data['description']

    # HTML structure for the playlist header and tracks
    html = f'''
    <html>
    <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:400,700">
        <style>
            body {{
                font-family: 'Roboto', sans-serif;
                background-color: #121212;
                color: white;
                text-align: left;
                padding: 20px;
            }}
            .header {{
                display: flex;
                align-items: center;
                margin-bottom: 20px;
            }}
            .cover {{
                width: 150px; /* Set width for the playlist cover */
                height: auto; /* Maintain aspect ratio */
                margin-right: 10px;
            }}
            .playlist-name {{
                font-size: 36px;
                margin: 0;
            }}
            .playlist-author, .playlist-meta, .playlist-description {{
                font-size: 14px;
                margin: 0;
                color: lightgray;
            }}
            .moving-header {{
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                background-color: rgba(18, 18, 18, 0.9);
                display: flex;
                align-items: center;
                padding: 10px;
                transition: opacity 0.3s ease;
                z-index: 1000;
                opacity: 0; /* Start hidden */
                visibility: hidden; /* Start hidden */
            }}
            .moving-header.visible {{
                opacity: 1; /* Fade in */
                visibility: visible; /* Make it visible */
            }}
            ul {{
                list-style-type: none;
                padding: 0;
            }}
            li {{
                margin: 10px 0;
                display: flex;
                align-items: center;
                justify-content: space-between;
                padding: 5px 10px;
                cursor: pointer;
                border-radius: 4px;
            }}
            li:hover {{
                background-color: #282828;
            }}
            img {{
                border-radius: 4px;
                width: 50px;
                height: 50px;
                margin-right: 10px;
            }}
            .track-info {{
                flex: 1;
                display: flex;
                align-items: center;
            }}
            .track-details {{
                display: flex;
                flex-direction: column;
            }}
            .track-name {{
                font-size: 16px;
                margin: 0;
            }}
            .track-artist {{
                font-size: 14px;
                color: lightgray;
                margin: 0;
            }}
            .track-meta {{
                display: flex;
                justify-content: space-between;
                width: 200px;
                font-size: 14px;
                color: lightgray;
            }}
            button {{
                background-color: #1DB954;
                color: white;
                border: none;
                padding: 10px 20px;
                font-size: 16px;
                cursor: pointer;
                margin-top: 20px;
            }}
            button:hover {{
                background-color: #1ed760;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <img src="{playlist_image}" alt="Playlist Cover" class="cover">
            <div class="playlist-details">
                <h1 class="playlist-name">{playlist_name}</h1>
                <p class="playlist-author">By {playlist_author}</p>
                <p class="playlist-meta">{total_tracks} tracks | Total Runtime: {total_duration}</p>
                <p class="playlist-description">{playlist_description}</p>
            </div>
        </div>
        <div class="moving-header" id="moving-header">
            <img src="{playlist_image}" alt="Playlist Cover" class="img">
            <h1 class="playlist-name">{playlist_name}</h1>
        </div>
        <form method="POST">
            <ul id="track-list">
    '''
    for i, item in enumerate(tracks):
        track = item['track']
        track_name = track['name']
        artist_name = ', '.join(artist['name'] for artist in track['artists'] if artist['name'])
        album_name = track['album']['name']
        duration_ms = track['duration_ms']
        duration = f"{duration_ms // 60000}:{(duration_ms // 1000) % 60:02}"
        track_uri = track['uri']
        track_image = track['album']['images'][0]['url'] if track['album']['images'] else ''

        html += f'''
           <li onclick="selectSong({i})">
               <div class="track-info">
                   <img src="{track_image}" alt="Track Image">
                   <div class="track-details">
                       <p class="track-name">{track_name}</p>
                       <p class="track-artist">{artist_name}</p>
                   </div>
               </div>
               <div class="track-meta">
                   <span>{album_name}</span>
                   <span>{duration}</span>
               </div>
           </li>
           '''

    html += '''
                </ul>
                <input type="hidden" id="start_song" name="start_song">
                <input type="hidden" id="end_song" name="end_song">
                <button type="submit">Start Playback</button>
            </form>
            <script>
                let startSong = null;
                let endSong = null;
                const trackList = document.querySelectorAll("#track-list li");

                function selectSong(index) {
                    if (startSong === null) {
                        startSong = index;
                        trackList[index].style.backgroundColor = 'lightgreen'; // Highlight start song
                    } else if (endSong === null) {
                        endSong = index;
                        trackList[index].style.backgroundColor = 'lightcoral'; // Highlight end song
                        // Reset start and end if start is greater than end
                        if (startSong > endSong) {
                            startSong = index;
                            endSong = null;
                            trackList[index].style.backgroundColor = 'lightgreen'; // Highlight new start song
                        }
                    } else {
                        // Reset selection
                        for (let i = 0; i < trackList.length; i++) {
                            trackList[i].style.backgroundColor = '';
                        }
                        startSong = index;
                        endSong = null;
                        trackList[index].style.backgroundColor = 'lightgreen'; // Highlight start song
                    }

                    document.getElementById("start_song").value = startSong;
                    document.getElementById("end_song").value = endSong;
                }

                const movingHeader = document.getElementById('moving-header');
                const headerHeight = document.querySelector('.header').offsetHeight;

                window.addEventListener('scroll', () => {
                    const scrollPos = window.scrollY;
                    if (scrollPos > headerHeight) {
                        movingHeader.classList.add('visible');
                    } else {
                        movingHeader.classList.remove('visible');
                    }
                });
            </script>
        </body>
    </html>
    '''

    return html


def start_playback(selected_songs, access_token):
    headers = {'Authorization': f'Bearer {access_token}'}
    requests.put('https://api.spotify.com/v1/me/player/repeat?state=context', headers=headers)

    payload = {
        'uris': selected_songs,
        'position_ms': 0
    }
    playback_url = 'https://api.spotify.com/v1/me/player/play'
    requests.put(playback_url, headers=headers, json=payload)
@app.route('/success')
def success():
    return render_template_string('''
    <html>
    <head>
        <link rel="stylesheet" href="https://fonts.googleapis.com/css?family=Roboto:400,700">
        <style>
            body {
                font-family: 'Roboto', sans-serif;
                background-color: #121212;
                color: white;
                text-align: center;
                padding: 20px;
            }
            a {
                color: #1DB954;
                text-decoration: none;
            }
            a:hover {
                text-decoration: underline;
            }
        </style>
    </head>
    <body>
        <h1>Success!</h1>
        <p>Your songs have been selected and playback has started.</p>
        <a href="{{ url_for('profile') }}"><button>Back to Profile</button></a>
    </body>
    </html>
    ''')


@app.route('/stop_playback', methods=['POST'])
def stop_playback():
    access_token = session.get('access_token')

    if not access_token:
        return redirect(url_for('login'))

    headers = {'Authorization': f'Bearer {access_token}'}
    stop_playback_url = 'https://api.spotify.com/v1/me/player/pause'

    requests.put(stop_playback_url, headers=headers)

    return redirect(url_for('profile'))


if __name__ == '__main__':
    app.run(debug=True)
