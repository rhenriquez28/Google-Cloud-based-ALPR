from base64 import b64encode
from PIL import Image
from six import BytesIO
import os, json, requests, re, cv2
import mysql.connector as mariadb
from contextlib import closing
from cloudant.client import Cloudant
from cloudant.query import Query
from dotenv import load_dotenv

load_dotenv()

client = None
db = None
db_selector = os.getenv("DB_SELECTOR")


def json_to_dict(json_str):
    return json.loads(json.dumps(json_str))

def db_init():
    if db_selector == 1:
        db = mariadb.connect(host=os.getenv("DB_HOST"),
                                            user=os.getenv("DB_USER"), 
                                            password=os.getenv("DB_PASSWORD"), 
                                            database=os.getenv("DB_NAME"), 
                                            port=os.getenv("DB_PORT"))
    elif db_selector == 2:
        client = Cloudant(os.getenv("SERVICE_USERNAME"),
                          os.getenv("SERVICE_PASSWORD"), 
                          url=os.getenv("SERVICE_URL"))
        client.connect()
        db = client[os.getenv("CLOUDANT_DB_NAME")]


def query_str_builder(plates):
    plates_length = len(plates)
    plate_query_str = ""
    i = 1
    for plate in plates:
        if i == plates_length:
            plate_query_str += "'" + plate + "'"
        else:
            plate_query_str += "'" + plate + "', "
        i += 1
    return plate_query_str

def db_check(plates):
    if db_selector == 1:
        with closing(db.cursor()) as cursor:
            cursor.execute(
                "SELECT * FROM placas WHERE placa IN ({})".format(query_str_builder(plates)))
            records = cursor.fetchall()
        if records:
            for row in records:
                if row[5] == "Sospechoso":
                    print(
                        "El auto con numero de placa {} es sospechoso".format(row[1]))
                else:
                    print(
                        "El auto con numero de placa {} es no sospechoso".format(row[1]))
    elif db_selector == 2:
        query = Query(db, selector={'matricula': {"$in": plates}})
        if query():
            for doc in query()['docs']:
                results = json_to_dict(doc)
                print("El auto con placa {} tiene las siguientes alertas: {}"
                    .format(results['matricula'], results['alerta']))

def db_close():
    if db_selector == 1:
        db.close()
    elif db_selector == 2:
        client.disconnect()

def convert_array_to_bytes(frame):
    """
    frame is an ndarray that we got from OpenCV
    Returns a base64-encoded string
    """
    frame_im = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_im = Image.fromarray(frame_im)
    stream = BytesIO()
    pil_im.save(stream, format="JPEG")
    stream.seek(0)
    img_for_post = stream.read()
    img_base64 = b64encode(img_for_post)
    return img_base64

def make_image_data_list(frame):
    """
    Returns a list of dicts formatted as the Vision API
        needs them to be
    """
    img_requests = []
    ctxt = convert_array_to_bytes(frame).decode()
    img_requests.append({
            'image': {'content': ctxt},
            'features': [{
                'type': 'TEXT_DETECTION',
                'maxResults': 1
            }]
    })
    return img_requests

def make_image_data(frame):
    """Returns the image data lists as bytes"""
    imgdict = make_image_data_list(frame)
    return json.dumps({"requests": imgdict }).encode()


def request_ocr(frame):
    response = requests.post(os.getenv("ENDPOINT_URL"),
                             data=make_image_data(frame),
                             params={'key': os.getenv("GCLOUD_VISION_API_KEY")},
                             headers={'Content-Type': 'application/json'})
    return response

def india_regex(data):
    print("Applying Regular Expression and deriving License Plate Number")
    match=re.match('[A-Z]{0,1}[\s]*[A-Z]{0,1}[\s]*[0-9]{0,1}[\s]*[0-9]{0,1}[\s]*[A-Z]{0,1}[\s]*[A-Z]{0,1}[\s]*[A-Z]{0,1}[\s]*[0-9]{1}[\s]*[0-9]{1}[\s]*[0-9]{1}[\s]*[0-9]{1}[\s]*',data)
    if(re.match('[A-Z]{0,1}[\s]*[A-Z]{0,1}[\s]*[0-9]{0,1}[\s]*[0-9]{0,1}[\s]*[A-Z]{0,1}[\s]*[A-Z]{0,1}[\s]*[A-Z]{0,1}[\s]*[0-9]{1}[\s]*[0-9]{1}[\s]*[0-9]{1}[\s]*[0-9]{1}[\s]*',data)):
        print(match.group(0))
    if(re.match('[^^][A-Z]{0,1}[\s]*[A-Z]{0,1}[\s]*[0-9]{0,1}[\s]*[0-9]{0,1}[\s]*[A-Z]{0,1}[\s]*[A-Z]{0,1}[\s]*[A-Z]{0,1}[\s]*[0-9]{1}[\s]*[0-9]{1}[\s]*[0-9]{1}[\s]*[0-9]{1}[\s]*',data)):
        print(match.group(0))
    else:
        print("No plate detected")
    return 0

def panama_regex(data):
    match=re.match('[0-9A-Z]{2}[0-9]{4}',data)
    if(re.match('[0-9A-Z]{2}[0-9]{4}',data)):
        return match.group(0)
    else:
        pass
    return 0

if __name__ == "__main__":
    db_init()
    '''
    Using the Video Caputure method from OpenCV to connect to a video source:
    It can be a video file, a MJPEG IP Camera stream, 
    or a direct video camera connected to your machine (webcam, usb camera, etc).
    '''
    cap = cv2.VideoCapture(os.getenv("VIDEO_PATH"))
    STATUS = True
    while STATUS == True:
        STATUS, frame = cap.read()
        response = request_ocr(frame)
        if response.status_code != 200 or response.json().get('error'):
            print(response.text)
        else:
            plates = []
            for i, annotation in enumerate(response.json()['responses'][0]['textAnnotations']):
                if i == 0:
                    pass
                else:
                    plates.append(panama_regex(annotation['description']))
            db_check(plates)
    db_close()
    cap.release()
    cv2.destroyAllWindows()
