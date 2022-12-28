# Spotify Playlist Organizer

## Spotify API Setup

To access the Spotify API, you first need to create a developer application through their [dashboard](https://developer.spotify.com/dashboard/applications). Once you create an application you need to get the `client_id` and `client_secret` and set them as environment variable. To do this, run:

```
export SPOTIPY_CLIENT_ID=<CLIENT_ID>
export SPOTIPY_CLIENT_SECRET=<SPOTIPY_CLIENT_SECRET>
```

Additionally, you need to set a re-direct URI to listen for the response from the Spotify API. You can choose any localhost address you like (ex. `http://localhost:4444/callback`). First, you have to set the redirect URI on the Spotify Dashboard. To do this, navigate to the [dashboard](https://developer.spotify.com/dashboard/applications) and select on your application. Click on "Edit Settings" and add your redirect URI. Additionally, you need to set this as an environment variable too. To do this, run:

```
export SPOTIPY_REDIRECT_URI=<SPOTIPY_REDIRECT_URI>
```

## Python Setup

To access the Spotify API, this application uses the `spotipy` python package. To install this run 

```
pip3 install spotipy
```

## Running the application

To sort a playlist, you must own the playlist and provide the playlist url to the application:

```
python3 run.py ${playlist_url}
```

