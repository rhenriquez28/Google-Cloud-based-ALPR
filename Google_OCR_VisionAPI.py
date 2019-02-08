from base64 import b64encode
from PIL import Image
from six import BytesIO
import os
import json
import requests
import re
import cv2
from dotenv import load_dotenv

load_dotenv()

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
        print(match.group(0))
    else:
        pass
    return 0

STATUS = True

'''
Using the Video Caputure method from OpenCV to connect to a video source:
It can be a video file, a MJPEG IP Camera stream, 
or a direct video camera connected to your machine (webcam, usb camera, etc).
'''
cap = cv2.VideoCapture(os.getenv("VIDEO_PATH"))
while STATUS == True:
    STATUS, frame = cap.read()
    response = request_ocr(frame)
    if response.status_code != 200 or response.json().get('error'):
        print(response.text)
    else:
        for i, annotation in enumerate(response.json()['responses'][0]['textAnnotations']):
            if i == 0:
                pass
            else:
                panama_regex(annotation['description'])
    
cap.release()
cv2.destroyAllWindows()