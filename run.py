import spotipy
import json
import math 
import json
from spotipy.oauth2 import SpotifyOAuth

# Make sure to set these path variables to ensure the spotify API works properly
# export SPOTIPY_CLIENT_ID=<CLIENT_ID>
# export SPOTIPY_CLIENT_SECRET=<SPOTIPY_CLIENT_SECRET>
# export SPOTIPY_REDIRECT_URI=<SPOTIPY_REDIRECT_URI>

scope = "playlist-read-private, playlist-read-collaborative, playlist-modify-private, playlist-modify-public"
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope), requests_timeout=15)

feature_list = [
    "acousticness",
    "danceability",
    "energy",
    "instrumentalness",
    "liveness",
    "loudness",
    "mode",
    "speechiness",
    # "tempo",
    "valence"
]


def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

# song = {
#     "feature-1": float,
#     "feature-2": float,
#     ...
# }
# where each float is some number representing that feature
# 
# get_normalized_data returns [float, float, float, float, float]
# where each float is between 0.0 and 1.0
def get_normalized_data(song, feature_groups):

    data = []

    for group in feature_groups:
        value = song[group[0]]

        min_value = group[1]
        max_value = group[2]

        normalized_value = (value - min_value) / (max_value - min_value)
        data.append(normalized_value)
    
    return data

# feat_list_n = [a,b,c,d,e]
# calc_distnace returns sqrt((a_1 - a_2)^2 + (b_1 - b_2)^2 + ...)
def calc_distance(feat_list_1, feat_list_2):
    sum = 0
    for (index, feat_1) in enumerate(feat_list_1):
        feat_2 = feat_list_2[index]
        square_diff = pow(feat_1 - feat_2 , 2)
        sum += square_diff
    return math.sqrt(sum)

# start = starting point index
# remaining_points = list of remaining points
# dist[a][b] = distance between points a & b
# get_tour returns (tour, tour_length):
#   tour = list of all points in order
#   tour_length = total size of tour
def get_tour(start, remaining_points, dist):
    tour = [start]
    tour_length = 0
    while len(remaining_points) > 0:
        shortest_distance = 9999999999999999
        closest_point = -1
        for next_point in remaining_points:
            curr_dist = dist[start][next_point]
            if curr_dist != -1 and curr_dist < shortest_distance:
                shortest_distance = curr_dist
                closest_point = next_point
            
        tour.append(closest_point)
        remaining_points.remove(closest_point)
        tour_length += shortest_distance
    
    return (tour, tour_length)

def get_feature_data(raw_data):
    feature_data = []
    for feature in feature_list:
        feat_max = 0
        feat_min = 999999999999999
        for song in raw_data:
            feat_value = song[feature]

            if feat_value > feat_max:
                feat_max = feat_value

            if feat_value < feat_min:
                feat_min = feat_value
        
        feature_data_item = [feature, float(feat_min), float(feat_max)]
        feature_data.append(feature_data_item)

    return feature_data


def calc(raw_data):
    feature_groups = get_feature_data(raw_data)

    data = [get_normalized_data(n, feature_groups) for n in raw_data]
    point_enums = enumerate(data)
    points = [i[0] for i in point_enums]

    dist = []
    for curr in points:
        append_list = []

        for adj in points:
            if curr == adj:
                append_list.append(-1)
            else:
                distance = calc_distance(data[curr], data[adj])
                append_list.append(distance)

        dist.append(append_list)

    shortest_tour = []
    shortest_tour_length = 9999999999999999
    shortest_starting_point = -1

    for start in points:
        
        remaining_points = points.copy()
        remaining_points.remove(start)

        (tour, tour_length) = get_tour(start, remaining_points, dist)

        if tour_length < shortest_tour_length:
            shortest_tour = tour
            shortest_tour_length = tour_length
            shortest_starting_point = start

    return shortest_tour


# Main
def generate_track_ordering(playlist_url):
    data = sp.playlist(playlist_url)
    data_store = {
        "user_id": data["owner"]["id"],
        "name": data["name"],
        "description": data["description"],
        "public": data["public"]
    }

    tracks = data["tracks"]
    track_store = tracks["items"]
    while tracks["next"]:
        tracks = sp.playlist_items(playlist_url, offset=len(track_store))
        for item in tracks["items"]:
            track_store.append(item)

    track_listing = [
        {
            "name": track["track"]["name"], 
            "id": track["track"]["id"]
        }
        for track in track_store
    ]

    track_info = []
    track_chunks = list(divide_chunks(track_listing, 100))
    for track_chunk in track_chunks:
        ids = [track["id"] for track in track_chunk]
        results = sp.audio_features(ids)
        for song in results:
            track_info.append(song)

    tour = calc(track_info)

    song_ids_in_order = []
    for id in tour:
        song_ids_in_order.append(track_info[id]["id"])
    

    return (data_store, song_ids_in_order)


def upload_songs(data_store, song_ids_in_order):
    chunk_size = 50
    id_chunks = list(divide_chunks(song_ids_in_order, chunk_size))
    rset = []
    for chunk in id_chunks:
        result = ""
        for id in chunk:
            result += f"spotify:track:{id},"
        rset.append(result[:-1])

    playlist_name = f"{data_store['name']} (Copy)"
    new_playlist = sp.user_playlist_create(user=data_store["user_id"], name=playlist_name, 
                                           public=data_store["public"], description=data_store["description"])
    new_playlist_id = new_playlist["id"]
    for (index, chunk) in enumerate(id_chunks):
        position = index * chunk_size
        sp.playlist_add_items(new_playlist_id, chunk, position)


playlist_url = 'https://open.spotify.com/playlist/726i7LcwWwusZMyFQSNYg8?si=e198c61c00a04ea4'
(data_store, song_ids_in_order) = generate_track_ordering(playlist_url)
upload_songs(data_store, song_ids_in_order)
