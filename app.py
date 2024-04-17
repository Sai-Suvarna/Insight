import uvicorn
from fastapi import FastAPI, Request, File, UploadFile,Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import cv2
import pickle
import numpy as np
import os
import requests
import subprocess
import shutil
from fastapi.responses import RedirectResponse
import easyocr
import psycopg2
import os
from dotenv import load_dotenv
import pathlib
import textwrap
from fastapi import HTTPException
import google.generativeai as genai
import PIL.Image

from IPython.display import display
from IPython.display import Markdown
from google.cloud import vision
from google.cloud.vision_v1 import types
import os

from io import BytesIO

from fastapi import FastAPI, File, UploadFile, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import shutil
import requests
import string

import base64
import uuid

import re

load_dotenv()

UPLOAD_FOLDER='static'

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

GOOGLE_API_KEY=os.getenv("GOOGLE_API_KEY")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-pro-vision')



@app.get('/')
def index(request: Request):
    return templates.TemplateResponse("open.html", {"request": request})

@app.get('/upload')
def upload(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.get('/result')
def result(request: Request):
    return templates.TemplateResponse("result.html", {"request": request})

@app.get('/live')
def live(request: Request):
    return templates.TemplateResponse("live.html", {"request": request})


@app.get('/search')
def live(request: Request):
    return templates.TemplateResponse("search.html", {"request": request})


def get_nearby_stores(location, object_name, radius=1000):
        api_key = 'AIzaSyB8zWPtv1G6B05tim27903BAeUQXjGS9dc'  # Replace with your Google Maps API key
        url = f'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={location}&radius={radius}&keyword={object_name}&key={api_key}'
        response = requests.get(url)
        data = response.json()
        return data['results']


def fetch_from_knowledge_graph(query):
    api_key = "AIzaSyBHQghHp4b6DdrlAftGluFOe6a6WQQpAn0"  # Replace with your actual API key
    api_endpoint = "https://kgsearch.googleapis.com/v1/entities:search"
    params = {
        "query": query,
        "key": api_key
    }
    response = requests.get(api_endpoint, params=params)
    data = response.json()
    return data

def display_knowledge_graph_data(data, query,upimage,location):
    results = []
    unique_names = set() 
    if "itemListElement" in data:
        for item in data["itemListElement"]:
            name = item["result"]["name"]
            print(name)
            if name.lower() == query.lower() and name not in unique_names:  # Check if the name is unique
                item_image = item["result"].get("image", {}).get("contentUrl", "No image available")
                if item_image != "No image available":
                    
                    description = item["result"].get("detailedDescription", {}).get("articleBody", "No detailed description available")

                    detailed_description = item["result"].get("detailedDescription", {}).get("url", "No detailed description available")
                    
                    nearby_stores = get_nearby_stores(location, name)
                
                    locations = []
                    for store in nearby_stores:
                        s = store['name'] + ' ' + store['vicinity']
                        locations.append(s)

                    
                    result_dict = {
                        "Name": name,
                        "Description": description,
                        "Detailed Description": detailed_description,
                        "item_image": item_image,
                        "locations":locations
                    }
                    results.append(result_dict)
                    unique_names.add(name)
                else:
                    model1 = genai.GenerativeModel('gemini-pro')
                    query="Give me a description of 60 words about" + name
                    response = model1.generate_content(query)
                    description=response.text

                    detailed_description = item["result"].get("detailedDescription", {}).get("url", "No detailed description available")
                    item_image=upimage
                    
                    nearby_stores = get_nearby_stores(location, name)
                
                    locations = []
                    for store in nearby_stores:
                        s = store['name'] + ' ' + store['vicinity']
                        locations.append(s)

                    result_dict = {
                        "Name": name,
                        "Description": description,
                        "Detailed Description": detailed_description,
                        "item_image": item_image,
                        "locations":locations
                    }
                    results.append(result_dict)
                    unique_names.add(name)

    print(unique_names)

    return results



def display_knowledge_graph_data1(data, query):
    results = []
    unique_names = set() 
    

   
    location = f'{latitude},{longitude}'

    if "itemListElement" in data:
        for item in data["itemListElement"]:
            name = item["result"]["name"]
            print(name)
            if name.lower() == query.lower() and name not in unique_names:  # Check if the name is unique
                item_image = item["result"].get("image", {}).get("contentUrl", "No image available")
                description = item["result"].get("detailedDescription", {}).get("articleBody", "No detailed description available")

                detailed_description = item["result"].get("detailedDescription", {}).get("url", "No detailed description available")
                
                nearby_stores = get_nearby_stores(location, name)
                
                locations = []
                for store in nearby_stores:
                    s = store['name'] + ' ' + store['vicinity']
                    locations.append(s)

                 
                
                result_dict = {
                        "Name": name,
                        "Description": description,
                        "Detailed Description": detailed_description,
                        "item_image": item_image,
                        "locations":locations
                    }

                results.append(result_dict)
                unique_names.add(name)
               
    print(unique_names)

    return results



@app.post("/upload_image", response_class=HTMLResponse)
async def upload_image( request: Request,image_file: UploadFile = File(...),latitude: float = Form(...), longitude: float = Form(...) ):
    image_path = f"{UPLOAD_FOLDER}/{image_file.filename}"
    save_path = os.path.join(UPLOAD_FOLDER, image_file.filename)
    
    with open(save_path, "wb") as image:
        content = await image_file.read()
        image.write(content)
         
    img = PIL.Image.open(image_path)
    
    location=f'{latitude},{longitude}'

    response = model.generate_content(["Identify the only some important things that are in the image.I should have the response only consist of names of all the objects name in a single word for each one without any stopwords in the object names separated by comma in the image", img], stream=True)
    response.resolve()
    
    res = response.text.split(',')
    res = [word.strip() for word in res if word.strip()]
    
    object_results = []
    for obj in res:
        data = fetch_from_knowledge_graph(obj)        
        object_data = display_knowledge_graph_data(data, obj,save_path,location)
        object_results.extend(object_data)
        
    
    print(object_results)

    
    context = {
        "request": request,
        "res":res,
        "object_results":object_results,
        "image_path": image_path
        
    }


    return templates.TemplateResponse("result.html", context)



@app.post("/search_objects", response_class=HTMLResponse)
async def search_objects(request: Request, search_word: str = Form(...)):
    
   
    object_results = []
    data = fetch_from_knowledge_graph(search_word)
    object_data = display_knowledge_graph_data1(data, search_word)
    
    object_results.extend(object_data)
    
    print(object_results)

    
    context = {
        "request": request,
        "object_results":object_results
    }
    
    return templates.TemplateResponse("search.html", context)




@app.post("/submit_snapshot", response_class=HTMLResponse)
async def save_snapshot(request: Request, image_file: UploadFile = File(...)):
        # Define the path where you want to save the image
        static_folder = "static"  # Or any other folder where you want to save the images
        image_path = os.path.join(static_folder, image_file.filename)
        print(image_path)
        # Save the image
        with open(image_path, "wb") as img:
            content = await image_file.read()
            img.write(content)
        
        
        img = PIL.Image.open(image_path)

        # Assuming model.generate_content() is an asynchronous operation
        response = model.generate_content(["Identify the only some important things that are in the image.I should have the response only consist of names of all the objects name in a single word for each one without any stopwords in the object names separated by comma in the image", img], stream=True)
        response.resolve()
        
        res = response.text.split(',')
        res = [word.strip() for word in res if word.strip()]
        
        object_results = []
        for obj in res:
            data = fetch_from_knowledge_graph(obj)
            object_data = display_knowledge_graph_data(data, obj, image_path)  # Assuming save_path is defined somewhere
            object_results.extend(object_data)
        
        
        context = {
            "request": request,
            "res": res,
            "object_results": object_results,
            "image_path": image_path
        }
        
        print(context)

        return templates.TemplateResponse("result.html", context)
  
    



    

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)