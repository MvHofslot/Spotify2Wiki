import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from datasets import load_dataset
from urllib.parse import urlparse
import re


# SPARQL Endpoint URL
url = 'https://dbpedia.org/sparql'

# Set Spotify client credentials
os.environ['SPOTIPY_CLIENT_ID'] = 'dbc18bf9ac38428ab2f685086f1e4d14'
os.environ['SPOTIPY_CLIENT_SECRET'] = '5de9a018825d47b0b13477cf2638799e'

# Create a Spotify object
spotify = spotipy.Spotify(client_credentials_manager=SpotifyClientCredentials())

def popularity(pop_number):
    rounded_pop = round(pop_number/10)
    if rounded_pop == 0:
        pop_text = "Virtually Unknown: The artist is virtually unknown and has minimal recognition, even within a niche audience."
    elif rounded_pop == 1:
        pop_text = "Local Act: The artist has some recognition within a small local community or specific niche, but remains relatively obscure."
    elif rounded_pop == 2:
        pop_text = "Emerging Talent: The artist is starting to gain some traction and may have a modest following in a specific genre or region."
    elif rounded_pop == 3:
        pop_text = "Regional Success: The artist has achieved recognition in a specific region or within a niche community, but is not widely known beyond that."
    elif rounded_pop == 4:
        pop_text = "Developing Fan Base: The artist is building a fan base and may have released music or work that is getting noticed by a broader global audience."
    elif rounded_pop == 5:
        pop_text = "Mainstream Recognition: The artist is gaining recognition in the mainstream and may have had a hit song or work that charted."
    elif rounded_pop == 6:
        pop_text = "Established Artist: The artist has a dedicated fan base, has released multiple successful works, and is recognized by a wide audience."
    elif rounded_pop == 7:
        pop_text = "Popular Mainstream Artist: The artist is widely known, with a substantial fan base, and has released multiple chart-topping hits."
    elif rounded_pop == 8:
        pop_text = "International Sensation: The artist has achieved global recognition, with a massive following and a significant impact on the music or art industry."
    elif rounded_pop >= 9:
        pop_text = "Superstar Status: The artist is a household name, with an enormous global fan base, and is one of the most influential and successful figures in their field."
    return pop_text

def get_artist_info(artist_name):
    # Search for the artist on Spotify
    results = spotify.search(q='artist:' + artist_name, type='artist')
    items = results['artists']['items']
    if len(items) > 0:
        artist = items[0]
        return artist
    return None

def get_artist_info_from_dbpedia(artist_name):
    artist_name = artist_name.replace(" ", "_")
    query = f'''
        PREFIX dbpedia: <http://dbpedia.org/resource/>
        PREFIX dbo: <http://dbpedia.org/ontology/>

        SELECT ?birthdate ?birthPlace ?birthName
        WHERE {{
          dbpedia:{artist_name} dbo:birthDate ?birthdate .
          OPTIONAL {{ dbpedia:{artist_name} dbo:birthPlace ?birthPlace . }}
          OPTIONAL {{ dbpedia:{artist_name} dbo:birthName ?birthName . }}
        }}

    '''
    results = requests.get(url, params={'query': query, 'format': 'json'}).json()
    artist_info = results["results"]["bindings"]

    return artist_info

def get_artist_data(artist_uri):
    # Get the artist's album information
    results = spotify.artist_albums(artist_uri, album_type='album')
    albums = results['items']

    results = spotify.artist_albums(artist_uri, album_type='single')
    singles = results['items']

    # Get the artist's top tracks
    top_tracks = spotify.artist_top_tracks(artist_uri, country='US')  # You can choose top tracks based on a specific country

    # Get the artist's genres (if available)
    artist_info = spotify.artist(artist_uri)
    if 'genres' in artist_info:
        genres = artist_info['genres']
    else:
        genres = []

    image_url = artist_info['images'][1]['url']

    return {"artist": artist_info, "albums": albums, "singles": singles, "top_tracks": top_tracks, "genres": genres, "image_url": image_url}

def generate_wikipedia_content(artist_name, birth_date, birthPlace, albums, top_tracks, genres):
    content = "== {} ==\n\n".format(artist_name)
    content += "The artist's name is'''{}'''.\n\n".format(artist_name)

    if birth_date:
        content += "Born on: {}\n\n".format(birth_date)

    if birthPlace:
        birthPlace = urlparse(birthPlace).path.split('/')[-1]
        content += "birthPlace: {}\n\n".format(birthPlace)

    content += "== Albums ==\n\n"
    for album in albums:
        content += "* {}\n".format(album['name'])

    content += "\n== Top Tracks ==\n\n"
    for track in top_tracks['tracks']:
        content += "* {}\n".format(track['name'])

    content += "\n== Genres ==\n\n"
    for genre in genres:
        content += "* {}\n".format(genre)

    content += "\n\n"  # Add a separator between artist information

    return content

def from_data():
    # Load the dataset with artist names
    dataset = load_dataset("maharshipandya/spotify-tracks-dataset")
    artists = dataset['train']['artists']

    for artist_name in artists:
      # Get Spotify artist information
      artist_uri = get_artist_info(artist_name)
      if artist_uri:
        # Check if the artist's Wikipedia page exists in DBpedia
        dbpedia_info = get_artist_info_from_dbpedia(artist_name)

        # Get Spotify data for the artist
        albums, top_tracks, genres, image_url = get_artist_data(artist_uri)

        birth_date = dbpedia_info[0]['birthdate']['value'] if dbpedia_info and 'birthdate' in dbpedia_info[0] else None
        birthPlace = dbpedia_info[0]['birthPlace']['value'] if dbpedia_info and 'birthPlace' in dbpedia_info[0] else None
        print(birth_date, birthPlace)
        # Generate Wikipedia content
        content = generate_wikipedia_content(artist_name, birth_date, birthPlace, albums, top_tracks, genres)

def process_albums(artist_dict):
    album_dict = {}

    for album in artist_dict['albums']:
        album_dict[album['name']] = album


    #remove duplicates or deluxe editions
    album_name_list = []
    removed_albums = []
    for album_name in album_dict:
        album_name_list.append(album_name)
    for album_name in album_name_list:
        for other_album_name in album_name_list:
            #check if not album itself
            if other_album_name != album_name:
                #check whether other album contains entire title
                if album_name in other_album_name:
                    #keep only most basic version
                    removed_albums.append(other_album_name)
    for removed_album in removed_albums:
        if removed_album in album_dict:
            del album_dict[removed_album]

    album_output = {}
    for album_name in album_dict:
        album = album_dict[album_name]
        album_output[album_name] = {}
        album_output["first_album"] = album_name
        album_output[album_name]["release_date"] = album['release_date'][:4]
        album_output[album_name]["image_url"] = album['images'][1]['url']
        album_output[album_name]["tracks"] = []
        album_tracks_data = spotify.album_tracks(album['id'])
        for album_track in album_tracks_data['items']:
            album_output[album_name]["tracks"] += [album_track['name']]
    return album_output

def fill_template(artist_dict, albums, singles):
    artist_image_url = artist_dict['image_url']
    newstring = ""
    with open("template.html") as my_file:
        i = 0
        for line in my_file.read().split("\n"):
            i += 1
            if i == 72:
                newline = "<h1>"+artist_dict['artist']['name']+"</h1>"
            elif i == 77:
                newline = "<img src=\""+artist_image_url+"\" alt=\"pencil\" />"
            elif i == 96:
                newline = ""
                for album_name in albums:
                    if not(isinstance(albums[album_name], str)):
                        album = albums[album_name]
                        album_image_url = album['image_url']
                        newline += """
                        <b>"""+album_name+"""
                        </b>
                        <p>This album was released in """ + "2012" + """, and contains the following tracklist:
                        </p>
                        <div class="articleRight">
                                <img src="
                        """ + album_image_url + """
                        " alt="pencil" width="200"/>
                        </div>
                        <ol>
                        """
                        for track_name in album['tracks']:
                            newline += "<li>" + track_name + "</li>"
                        newline += "</ol>"
            elif i == 98 and singles[0]:
                singles_string = "<h3 id=\"Singles\">Singles</h3><ul>"
                for single in singles:
                    singles_string += "<li>" + re.sub(r'\[[^]]*\]', '', re.sub(r'\([^)]*\)', '', single[0])) + "\t\t\t(" + single[1].split("-")[0] + ")</li>"
                newline = singles_string+"</ul>"
                print(newline)
            else:
                newline = line
            newstring += newline + "\n"
    with open("index.html", "w") as text_file:
        text_file.write(newstring)


def main():
    search_name = "Bob Dylan"
    # Get Spotify artist information
    artist = get_artist_info(search_name)
    artist_uri = artist['uri']
    if artist_uri:
    # Check if the artist's Wikipedia page exists in DBpedia
        # Get Spotify data for the artist
        artist_dict = get_artist_data(artist_uri)

        albums = process_albums(artist_dict)
        singles = []
        for item in artist_dict['singles']:
            singles.append([item['name'], item['release_date']])

        fill_template(artist_dict, albums, singles)

        artist_name = artist_dict['artist']['name']
        genres = artist_dict['artist']['genres']
        genre_string = ""
        i = 0
        for genre in genres:
            if i != 0:
                genre_string += ", "
            genre_string += genre
            i+=1


        first_album = albums["first_album"]


        # === TOP TRACKS ===
        top_tracks = spotify.artist_top_tracks(artist_uri)
        #print(top_tracks[0]['name'])
        top_tracks_list = []
        removed_tracks = []
        for track in top_tracks['tracks']:
            track_string = re.sub(r'\[[^]]*\]', '', re.sub(r'\([^)]*\)', '', track['name']))
            top_tracks_list.append(track_string)
        for track1 in top_tracks['tracks']:
            for track2 in top_tracks['tracks']:
                if track1['name'] != track2['name']:
                    if track1['name'] in track2['name']:
                        removed_tracks.append(track2['name'])


        #remove duplicates or deluxe editions
        top_tracks_final = [x for x in top_tracks_list if x not in removed_tracks]
        top_tracks_string = ""
        i = 0
        for track in top_tracks_final[:3]:
            if i != 0:
                top_tracks_string += ", "
            top_tracks_string += track
            i+=1

        # === DBPEDIA ===

        dbpedia_info = get_artist_info_from_dbpedia(artist_name)
        if dbpedia_info:
            if 'birthdate' in dbpedia_info[0]:
                birth_date = dbpedia_info[0]['birthdate']['value']
            if 'birthPlace' in dbpedia_info[0]:
                birth_place = dbpedia_info[0]['birthPlace']['value']
                birth_place = urlparse(birth_place).path.split('/')[-1].replace("_", " ")
            if 'birthName' in dbpedia_info[0]:
                birth_name = dbpedia_info[0]['birthName']['value']
            print("Can you write a Wikipedia style introduction text for an artist, based on only the following information:\n\n"
                  "\nartist name: "+artist_name,
                  "\nReal name: "+birth_name,
                  "\nBirth date: "+birth_date,
                  "\nBirth place: "+birth_place,
                  "\npopularity: "+popularity(artist_dict['artist']['popularity']),
                  "\ngenres: "+genre_string,
                  "\nfirst studio album: "+first_album,
                  "\ncurrently most popular songs: "+top_tracks_string)

        else:
            print("Can you write a Wikipedia style introduction text for an artist, based on only the following information. Make sure the text uses formal language and is not too long or elaborate:\n\n"
                  "\nartist name: "+artist_name,
                  "\npopularity: "+popularity(artist_dict['artist']['popularity']),
                  "\nfirst studio album: "+first_album,
                  "\ncurrently most popular songs: "+top_tracks_string)
            if genre_string != "":
                print("genres: "+genre_string)
if __name__ == "__main__":
  main()