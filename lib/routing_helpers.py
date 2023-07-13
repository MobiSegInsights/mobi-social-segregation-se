import requests
import io, os
from datetime import date
from pathlib import Path
import yaml
from shapely.geometry import mapping
import json
import requests as req


ROOT_dir = Path(__file__).parent.parent
with open(os.path.join(ROOT_dir, 'dbs', 'keys.yaml')) as f:
    keys_manager = yaml.load(f, Loader=yaml.FullLoader)


def gtfs_downloader(region='sweden',
                    user='yuan',
                    region_operator='sl',
                    skip_country=True):
    # regional_operators = ["blekinge", "dt", "dintur", "gotland", "halland", "jlt", "klt", "krono", "jamtland",
    #             "norrbotten", "vasterbotten", "orebro", "skane", "sl", "sormland", "ul", "vastmanland",
    #             "varm", "vt", "xt", "otraf", "sj"]
    today = date.today()
    folder = ROOT_dir + f"/dbs/gtfs_{region}_" + str(today)
    if os.path.exists(folder) is not True:
        print(f"Downloading latest GTFS data for {region}...")
        os.mkdir(folder)
    # The entire Sweden
    if ~skip_country:
        local_path_to_write = folder + "/sweden.zip"
        if os.path.exists(local_path_to_write) is not True:
            gtfs_sweden = "https://opendata.samtrafiken.se/gtfs-sweden/sweden.zip?key="
            response = requests.get(gtfs_sweden + keys_manager['gtfs_api'][user]['sweden_2_key'], stream=True)
            s = io.BytesIO(response.content)
            local_path_to_write = folder + "/sweden.zip"
            with open(local_path_to_write, 'wb') as f_out:
                f_out.write(s.getvalue())
    local_path_to_write = folder + f"/sweden_regional_{region_operator}.zip"
    if os.path.exists(local_path_to_write) is not True:
        # Specified regional repo
        apikey = keys_manager['gtfs_api'][user]['sweden_region_key']
        gtfs_sweden_regional = f"https://opendata.samtrafiken.se/gtfs/{region_operator}/{region_operator}.zip?key={apikey}"
        response = requests.get(gtfs_sweden_regional, stream=True)
        s = io.BytesIO(response.content)

        with open(local_path_to_write, 'wb') as f_out:
            f_out.write(s.getvalue())
    else:
        print(f"Latest GTFS data for {region_operator} exists. Downloading skipped.")


def gdf2poly(geodata=None, targetfile=None, buffer=0.03):
    """
    :param filename: .shp, a polygon
    :param targetfile: .poly, a polygon
    :param buffer: default 0.03, for the ease of cropping
    :return: None
    """
    g = [i for i in geodata.to_crs(4326).buffer(buffer).geometry]
    all_coords = mapping(g[0])["coordinates"][0]
    F = open(targetfile, "w")
    F.write("polygon\n")
    F.write("1\n")
    for point in all_coords:
        F.write("\t" + str(point[0]) + "\t" + str(point[1]) + "\n")
    F.write("END\n")
    F.write("END\n")
    F.close()


def osm_country2region(osm_file=None, terget_file=None, poly_file=None):
    command_line = f'''osmosis --read-pbf-fast file="{osm_file}" --bounding-polygon file="{poly_file}" --write-pbf file="{terget_file}"'''
    os.system(command_line)


def otp_build(otp_file=None, otp_folder=None, memory_gb=None):
    # command_line = f'''java -Xmx{memory_gb}G -jar {otp_file} --build --save {otp_folder}'''
    command_line = f'''java -Xmx{memory_gb}G -jar {otp_file} --cache {otp_folder} --basePath {otp_folder} --build {otp_folder}'''
    os.system(command_line)


def otp_server_starter(otp_file=None, otp_folder=None, memory_gb=None):
    # command_line = f'''java -Xmx{memory_gb}G -jar {otp_file} --build --save {otp_folder}'''
    command_line = f'''java -Xmx{memory_gb}G -jar {otp_file} --build {otp_folder} --inMemory'''
    os.system("start /B start cmd.exe @cmd /k " + command_line)


def req_define(fromPlace, toPlace, time, date, maxWalkDistance, numItineraries=1, clampInitialWait=0, mode="TRANSIT,WALK", arriveBy=False): # "TRANSIT,WALK"
    # fromPlace, toPlace: (59.33021, 18.07096)
    # numItineraries (int): 3
    # time (string): "5:00am"
    # date (string): "5-15-2019"
    # mode (string): "TRANSIT,WALK"
    # maxWalkDistance (int): 800 #meters
    # arriveBy (boolean): False
    otp_server = "http://localhost:8080/otp/routers/default/plan?"
    request = otp_server
    # places
    request += "fromPlace="
    request += str(fromPlace).strip(")").strip("(")
    request += "&toPlace="
    request += str(toPlace).strip(")").strip("(")
    # itinerary
    request += "&numItineraries="
    request += str(numItineraries)
    # clampInitialWait
    request += "&clampInitialWait="
    request += str(clampInitialWait)
    # time
    request += "&time="
    request += time
    # date
    request += "&date="
    request += date
    # mode
    request += "&mode="
    request += mode
    # maxWalkDistance
    request += "&maxWalkDistance="
    request += str(maxWalkDistance)
    # arriveBy
    request += "&arriveBy="
    if arriveBy == False:
        request += "false"
    else:
        request += "true"

    return request


def requesting_origin_batch(data, walkdistance=800, folder2save=None, region=None):
    origin = data.loc[:, 'origin'].values[0]
    print("Origin ID: ", origin, "# ODs", len(data))
    jsonList_ID = []
    def requesting(row):
        request = req_define((row['lat_o'], row['lng_o']),
                             (row['lat_d'], row['lng_d']), row['depart_time'], row['date'], walkdistance)
        resp = req.get(request)
        output = resp.json()
        if "plan" in output:
            plan = output["plan"]["itineraries"][0]
            plan["Hour"] = row['depart_time']
            plan["Destination"] = row['destination']
            jsonList_ID.append(plan)
    data.apply(lambda row: requesting(row), axis=1)
    if len(jsonList_ID) > 0:
        with open(folder2save + region + '_origin_' + str(origin) + ".json", 'w') as outfile:
            for ele in jsonList_ID:
                print(json.dumps(ele), file=outfile)
