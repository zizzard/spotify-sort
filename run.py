import spotipy
import math 
import sys
from spotipy.oauth2 import SpotifyOAuth

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
    "tempo",
    "valence"
]

# Used by the spotify API to split large requests into multiple smaller ones
CHUNK_SIZE = 50

# Divide a list `l`` into a generator of lists of size `n`
# Need to convert back into a list upon retrevial 
def divide_chunks(l, n):
    for i in range(0, len(l), n):
        yield l[i:i + n]

# song = {
#     "feature-1": float,
#     "feature-2": float,
#     ...
# }
# where each float is some number representing that feature

# feature_groups = [ 
#   [feature_name (string), min_value (float), max_value (float)], ...
# ]
# exists for each feature in the feature_list provided above

# get_normalized_data returns [float, float, float, float, float]
# where each float is between 0.0 and 1.0 corresponding to each feature in the feature_list provided above
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

# Takes a list of raw song data and calculates the minumum and 
# maximum value for each feature among the playlist to ensure we 
# don't favor one feature over another - we will later normalize
# each feature value
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

# `raw_data` is the spotify api song data (w. unimportant data filtered out
# and split into chunks). This function returns the shortest tour for all 
# of the songs in the raw_data list, represented by a list tracks in order
def shortest_tour_calc(raw_data):
    # Get the feature groups, normalize the data values, and setup the list of points
    feature_groups = get_feature_data(raw_data)

    data = [get_normalized_data(n, feature_groups) for n in raw_data]
    point_enums = enumerate(data)
    points = [i[0] for i in point_enums]

    # Generate all of the distances pairs for all of the songs in the playlist
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

    # Find the shortest tour
    shortest_tour = []
    shortest_tour_length = 9999999999999999
    for start in points:
        
        remaining_points = points.copy()
        remaining_points.remove(start)

        (tour, tour_length) = get_tour(start, remaining_points, dist)

        if tour_length < shortest_tour_length:
            shortest_tour = tour
            shortest_tour_length = tour_length

    return shortest_tour


# Pulls the playlist data and generates the track ordering
def generate_track_ordering(playlist_url):
    # Get the playlist
    data = sp.playlist(playlist_url)

    # Extract information to be used when copying later
    data_store = {
        "user_id": data["owner"]["id"],
        "name": data["name"],
        "description": data["description"],
        "public": data["public"]
    }

    # Extract all of the tracks from the playlist and store them in a simpler format
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

    # Chunk the tracks in managable sizes (for the Spotify API) and get the audio features for each track
    track_info = []
    track_chunks = list(divide_chunks(track_listing, CHUNK_SIZE))
    for track_chunk in track_chunks:
        ids = [track["id"] for track in track_chunk]
        results = sp.audio_features(ids)
        for song in results:
            track_info.append(song)

    # Generate the shortest tour with the track info 
    tour = shortest_tour_calc(track_info)

    # Get only the track IDs from the shortest tour
    song_ids_in_order = []
    for id in tour:
        song_ids_in_order.append(track_info[id]["id"])
    
    return (data_store, song_ids_in_order)

# Uploads all of the songs to the new playlist in order
def upload_songs(data_store, song_ids_in_order):
    
    # Create the result set to create the new playlist
    id_chunks = list(divide_chunks(song_ids_in_order, CHUNK_SIZE))
    rset = []
    for chunk in id_chunks:
        result = ""
        for id in chunk:
            result += f"spotify:track:{id},"
        rset.append(result[:-1])

    # Create a new playlist
    playlist_name = f"{data_store['name']} (copy)"
    new_playlist = sp.user_playlist_create(user=data_store["user_id"], name=playlist_name, 
                                           public=data_store["public"], description=data_store["description"])

    # Upload each chunk to the new playlist
    new_playlist_id = new_playlist["id"]
    for (index, chunk) in enumerate(id_chunks):
        position = index * CHUNK_SIZE
        sp.playlist_add_items(new_playlist_id, chunk, position)
    
    return new_playlist["external_urls"]["spotify"]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("No playlist URL was provided, please run the application in using the following format: ")
        print("  $ python3 run.py https://open.spotify.com/playlist/example_id")
        sys.exit()
    
    # Example URL: https://open.spotify.com/playlist/726i7LcwWwusZMyFQSNYg8?si=e198c61c00a04ea4
    playlist_url = sys.argv[1]

    # Generate the track ordering for the provided playlist
    print("Generating track ordering...")
    (data_store, song_ids_in_order) = generate_track_ordering(playlist_url)
    print("Track ordering complete!")

    # Upload the songs to a new playlist
    print("Uploading to a new playlist...")
    new_playlist_url = upload_songs(data_store, song_ids_in_order)
    print("Complete!")
    print(f"The new playlist can be found at: {new_playlist_url}")
