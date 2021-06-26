# .  __  __       _       _        ____
#  |  \/  | __ _| |_ ___| |__    / ___| __ _ _ __ ___   ___
#  | |\/| |/ _` | __/ __| '_ \  | |  _ / _` | '_ ` _ \ / _ \
#  | |  | | (_| | || (__| | | | | |_| | (_| | | | | | |  __/
#  |_|  |_|\__,_|\__\___|_| |_|  \____|\__,_|_| |_| |_|\___|


# Estrategia "blastoise"

botName = "baltazarortg-1"
import requests
import json
from random import sample, choice
from time import sleep


headers_vision = {
    "Ocp-Apim-Subscription-Key": "",
    "Content-Type": "application/octet-stream",
}
vision_base_url = "https://westeurope.api.cognitive.microsoft.com/vision/v2.0/"

# array con diccionarios que tienen keys: Index, State (ANALYSED, UNANALYSED, MATCHED), Subject y Category
analysed_tiles = []

previous_move = []
api_calls = []
move_number = 0
bonus_category = ""
matches_antes_fin_analisis = 0


def calculate_move(gamestate):
    global analysed_tiles
    global previous_move
    global move_number
    global bonus_category
    global matches_antes_fin_analisis

    # Variables del estado
    num_tiles = len(gamestate["Board"])
    bonus_category = gamestate["Bonus"].upper()

    if move_number == 0:
        categories_of_tiles = get_tiles_categories_from_backs(gamestate)
        print("Categories of tiles: {}".format(categories_of_tiles))

    move_number += 1

    if gamestate["UpturnedTiles"] == []:
        # No tendremos UpturnedTiles al comienzo del juego y cuando ultimo movimiento fue un match.
        print("{}. No upturned tiles for this move.".format(move_number))
    else:
        # Mostrar los UpturnedTiles
        print(
            "{}. ({}, {}) Upturned tiles for this move".format(
                move_number,
                gamestate["UpturnedTiles"][0]["Index"],
                gamestate["UpturnedTiles"][1]["Index"],
            )
        )
    print("  gamestate: {}".format(gamestate))

    # Primer turno del juego
    if analysed_tiles == []:
        for index in range(num_tiles):
            # Mark tile as not analysed
            analysed_tiles.append({})
            analysed_tiles[index]["Index"] = index
            analysed_tiles[index]["State"] = "UNANALYSED"
            analysed_tiles[index]["Category"] = categories_of_tiles[index]
            analysed_tiles[index]["Subject"] = None

    # Si tenemos UpturnedTiles
    if gamestate["UpturnedTiles"] != []:
        # Aqui se esta actualizando el array de analysed_tiles
        analyse_tiles(gamestate["UpturnedTiles"], gamestate)
    else:
        # No es nuestro primer move en el juego
        if previous_move != []:
            print(
                "  MATCH: ({}, {}) - {}".format(
                    previous_move[0],
                    previous_move[1],
                    analysed_tiles[previous_move[0]]["Subject"],
                )
            )
            analysed_tiles[previous_move[0]]["State"] = "MATCHED"
            analysed_tiles[previous_move[1]]["State"] = "MATCHED"

    # Primer movimiento
    if move_number == 1:
        unanalysed_tiles = get_unanalysed_tiles()
        print(
            "Len de unanalysed_tiles. Deberia ser n - 2. {}".format(
                len(unanalysed_tiles)
            )
        )
        tile_a, tile_b = search_tiles_same_category(unanalysed_tiles, bonus_category)
        move = [tile_a, tile_b]
        matches_antes_fin_analisis += 1
        print("  Primer movimiento: {}".format(move))
    elif move_number <= len(gamestate["Board"]) / 2:
        # Mientras esto sea verdad, continuamos explorando
        unanalysed_tiles = get_unanalysed_tiles()
        print(
            "Len de unanalysed_tiles. Deberia reducirse por 2 cada vez {}".format(
                len(unanalysed_tiles)
            )
        )

        if search_tiles_same_category(unanalysed_tiles, bonus_category):
            # Afortunado. Puedo investigar y ademas tener la probabilidad de hacer match
            tile_a, tile_b = search_tiles_same_category(
                unanalysed_tiles, bonus_category
            )
            move = [tile_a, tile_b]
            matches_antes_fin_analisis += 1
            print("Match categorico encontrado. {}".format(move))
        else:
            # Ni modo, pero puedo seguir investigando
            print("Seguimos investigando")
            tile_a, tile_b = unanalysed_tiles[0], unanalysed_tiles[1]
            move = [tile_a, tile_b]
            print("Nuevo move. {}".format(move))
    else:
        # Ya podemos comenzar a hacer matches
        print(
            "Matches encontrados durante el analisis: {}".format(
                matches_antes_fin_analisis
            )
        )
        unanalysed_tiles = get_unanalysed_tiles()

        match = search_for_matching_titles_bonus()
        if match is not None:
            print("  Matching Move: {}".format(match))
            move = match
        else:
            match = search_for_matching_tiles()
            # If SI tenemos un match
            if match is not None:

                print("  Matching Move: {}".format(match))
                move = match
                # La actualizacion a MATCHED ocurre en el proximo turno cuando UpturnedTiles == [] y el previous_move != []

            else:
                unanalysed_tiles = get_unanalysed_tiles()
                if unanalysed_tiles != []:

                    move = sample(unanalysed_tiles, 2)
                else:

                    unmatched_tiles = get_unmatched_tiles()

                    move = sample(unmatched_tiles, 2)

    previous_move = move
    return {"Tiles": move}


def search_for_matching_tiles():
    for index_1, tile_1 in enumerate(analysed_tiles):
        for index_2, tile_2 in enumerate(analysed_tiles):
            if (
                tile_1["State"] == tile_2["State"] == "ANALYSED"
                and tile_1["Subject"] == tile_2["Subject"]
                and tile_1["Subject"] is not None
                and index_1 != index_2
            ):
                return [index_1, index_2]
    return None


def search_for_matching_titles_bonus():
    for index_1, tile_1 in enumerate(analysed_tiles):
        for index_2, tile_2 in enumerate(analysed_tiles):
            if (
                tile_1["State"] == tile_2["State"] == "ANALYSED"
                and tile_1["Subject"] == tile_2["Subject"]
                and tile_1["Subject"] is not None
                and tile_1["Category"] == tile_2["Category"] == bonus_category
                and index_1 != index_2
            ):
                return [index_1, index_2]
    return None


def search_tiles_same_category(tiles_indeces, category):
    tiles_to_search = []

    for idx in tiles_indeces:
        tile_to_add = analysed_tiles[idx]
        tile_to_add["original_idx"] = analysed_tiles[idx]["Index"]
        tiles_to_search.append(tile_to_add)

    for index_1, tile_1 in enumerate(tiles_to_search):
        for index_2, tile_2 in enumerate(tiles_to_search):
            if (
                tile_1["Category"] == tile_2["Category"] == category
                and tile_1["Category"] is not None
                and tile_1["original_idx"] != tile_2["original_idx"]
            ):

                return [tile_1["original_idx"], tile_2["original_idx"]]
    # print("NO se encontro match categorico")
    return None


# Son los no analizados (obviamente) y los ya analizados, que no tienen match
def get_unmatched_tiles():
    unmatched_tiles = []
    # For every tile in the game
    for index, tile in enumerate(analysed_tiles):
        if tile["State"] != "MATCHED":
            unmatched_tiles.append(index)
    return unmatched_tiles


def get_unanalysed_tiles():
    unanalysed_tiles = []
    for index, tile in enumerate(analysed_tiles):
        if tile["State"] == "UNANALYSED":
            unanalysed_tiles.append(index)
    return unanalysed_tiles


# Va a analizar de dos en dos
def analyse_tiles(tiles, gamestate):
    for tile in tiles:
        analyse_tile(tile, gamestate)


# Determina la categoria
def analyse_tile(tile, gamestate):
    if analysed_tiles[tile["Index"]]["State"] != "UNANALYSED":
        return

    # Call analysis
    analyse_url = vision_base_url + "analyze"  # Use analyze API function
    # List of the features that we want to get
    params_analyse = {
        "visualFeatures": "categories,tags,description,faces,imageType,color",
        "details": "celebrities,landmarks",
    }
    data = {"url": tile["Tile"]}
    msapi_response = microsoft_api_call(
        analyse_url, params_analyse, headers_vision, data
    )
    print("  API Result tile #{}: {}".format(tile["Index"], msapi_response))

    subject = check_for_landmark(msapi_response)

    if subject is None:
        subject = check_for_animal(msapi_response, gamestate["AnimalList"])
        if subject is None:
            subject = check_for_text(tile)
        else:
            print("  Animal at tile #{}: {}".format(tile["Index"], subject))
    analysed_tiles[tile["Index"]]["State"] = "ANALYSED"
    analysed_tiles[tile["Index"]]["Subject"] = subject


def check_for_animal(msapi_response, animal_list):
    subject = None
    if "tags" in msapi_response:
        for tag in sorted(
            msapi_response["tags"], key=lambda x: x["confidence"], reverse=True
        ):
            if "name" in tag and tag["name"] in animal_list:
                subject = tag["name"].lower()
                print("  Animal: {}".format(subject))
                break
    # Return the subject
    return subject


def check_for_text(tile):
    subject = None

    # Call analysis
    analyse_url = vision_base_url + "ocr"  # Use OCR API function
    params_analyse = {}
    data = {"url": tile["Tile"]}
    msapi_response = microsoft_api_call(
        analyse_url, params_analyse, headers_vision, data
    )

    print("OCR Response: {}".format(msapi_response))

    if "regions" in msapi_response:  # Checando si el dict tiene ese key
        if msapi_response["regions"]:
            if "lines" in msapi_response["regions"][0]:
                if "words" in msapi_response["regions"][0]["lines"][0]:
                    if "text" in msapi_response["regions"][0]["lines"][0]["words"][0]:
                        subject = msapi_response["regions"][0]["lines"][0]["words"][0][
                            "text"
                        ]
                        print("***OCR text: {}".format(subject))

    return subject


def get_tiles_categories_from_backs(gamestate):
    # Lista con strings
    categories_of_tiles = []

    # Call analysis
    analyse_url = vision_base_url + "ocr"  # Use OCR API function
    params_analyse = {}

    for tile in gamestate["TileBacks"]:
        category = ""
        data = {"url": tile}
        msapi_response = microsoft_api_call(
            analyse_url, params_analyse, headers_vision, data
        )
        if "regions" in msapi_response:  # Checando si el dict tiene ese key
            if msapi_response["regions"]:
                if "lines" in msapi_response["regions"][0]:
                    if "words" in msapi_response["regions"][0]["lines"][0]:
                        if (
                            "text"
                            in msapi_response["regions"][0]["lines"][0]["words"][0]
                        ):
                            category = (
                                msapi_response["regions"][0]["lines"][0]["words"][0][
                                    "text"
                                ]
                                + "S"
                            )
                            categories_of_tiles.append(category)
                            print("***OCR Categoria en back: {}".format(category))
    return categories_of_tiles


def check_for_landmark(msapi_response):

    subject = None

    for category in msapi_response["categories"]:

        if (
            "detail" in category
            and "landmarks" in category["detail"]
            and category["detail"]["landmarks"]
        ):

            subject = category["detail"]["landmarks"][0]["name"].lower()

            print("Landmark: {}".format(subject))
            break

    return subject


# Call the Microsoft API to analyse the image and to return information
# about the contents of the image.
#
# Inputs:
#   url:     string     - The Microsoft API endpoint
#   params:  dictionary - Which Computer Vision services should the request check for
#   headers: dictionary - API Key to allow request to be made
#   data:    dictionary - The image that we want the API to analyse
# Outputs:
#   JSON dictionary - The result of the API call
#
def microsoft_api_call(url, params, headers, data):
    retry_count = 0
    res = {}

    while ("error" in res and res["error"]["code"] == "429") or res == {}:
        # Make API request and record the results
        try:
            r = requests.get(data["url"], allow_redirects=True)
            response = requests.post(
                url, headers=headers_vision, params=params, data=r.content
            )
            res = response.json()  # Convert result to JSON
        except Exception as e:
            retry_count += 1
            # print(f"  [WARN] ({retry_count}) There was an issue making the Microsoft API request, retrying...")
            # print(f"    {e}")

    return res


# Test the user has used a valid subscription key
def valid_subscription_key():
    # Make a computer vision api call
    params_analyse = {"visualFeatures": "categories,tags", "details": "landmarks"}
    data = {"url": "https://www.aigaming.com/Images/aiWebsiteLogo.png"}

    test_api_call = microsoft_api_call(
        vision_base_url + "analyze", params_analyse, headers_vision, data
    )

    if "error" in test_api_call:
        raise ValueError(
            "Invalid Microsoft Computer Vision API key for current region: {}".format(
                test_api_call
            )
        )


# Check the subscription key
valid_subscription_key()
