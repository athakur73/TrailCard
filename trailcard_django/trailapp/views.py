import os
import string
import re
import nltk
from dateutil import parser
import datetime
import random
import pandas as pd
from nltk.corpus import words
from datetime import timedelta
from contextlib import suppress
from pathlib import Path
from rest_framework.generics import GenericAPIView
from rest_framework.renderers import JSONRenderer
from django.http import HttpResponse, FileResponse
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser

from trailapp.util import extract_all_entities
from trailapp.serializers import FileSerializer
from trailapp.models import File
from django.conf import settings
import pytesseract
import nltk
from geotext import GeoText
import re

nltk.download('punkt')
nltk.download('words')
eng_dict_words = set(words.words())

import subprocess
import pickle
import pytesseract
import nltk
from geotext import GeoText
import re


class UploadFile(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, *args, **kwargs):
        files = request.FILES.getlist('file')
        data = request.data
        data["file_status"] = 1
        data["uploaded_date"] = datetime.datetime.now()
        data["last_modified_by"] = data["uploaded_by"]
        data["last_modified_date"] = datetime.datetime.now()
        result = []
        status = 200
        for file in files:
            data["file"] = file
            data["filename"] = file.name
            file_serializer = FileSerializer(data=data)
            if file_serializer.is_valid():
                file_serializer.save()
                result.append(file_serializer.data)
            else:
                status = 400
                result.append(file_serializer.errors)

        res = {
            "message": "File Upload complete",
            "status": status,
            "result": result
        }
        json_data = JSONRenderer().render(res)
        return HttpResponse(json_data, content_type='application/json')


class Redact(APIView):

    def post(self, request, *args, **kwargs):
        file_id = request.data.get('file_id')
        user_id = request.data.get('user_id')
        file_name = File.objects.filter(id=file_id).values('filename')
        document_name = file_name.values()[0]['filename']

        extract_all_entities(document_name)

        res = {
            "message": "File extracted successfully ",
            # "status": status,
            # "result": result
        }
        json_data = JSONRenderer().render(res)
        return HttpResponse(json_data, content_type='application/json')


class ListOfFile(GenericAPIView):
    def get(self, request, *args, **kwargs):
        file_list = File.objects.filter(is_delete=0)
        file_list_array = []
        for files in file_list:
            fileData = File.objects.get(id=files.id)
            file_url = fileData.file.url
            if files.file_status == 1:
                file_url = fileData.file.url
            else:
                print("file path not found")

            # print(file_url)
            file_list_array.append({
                "id": files.id,
                "filename": files.filename,
                "uploaded_by": files.uploaded_by,
                "file_status": files.file_status,
                "Uploaded_date": files.uploaded_date,
                "Last_modified_date": files.last_modified_date,
                "file_url": file_url,
            })
        res = {
            "message": "List of files",
            "status": 200,
            "data": file_list_array
        }
        json_data = JSONRenderer().render(res)
        return HttpResponse(json_data, content_type='application/json')


class FileDelete(GenericAPIView):
    def post(self, request, *args, **kwargs):
        file_id = request.data['file_id']
        file_exists = File.objects.filter(id=file_id)
        # user_id = request.data['user_id']
        if file_exists:
            file = File.objects.get(id=file_id)#.delete()
            file.is_delete = True
            file.save()
            res = {
                    "message": "File has deleted successfully",
                    "status": 200,
                }
            json_data = JSONRenderer().render(res)
            return HttpResponse(json_data, content_type='application/json')
        else:
            res = {
                    "message": "File not yet created or already deleted",
                    "status": 200,
                }
            json_data = JSONRenderer().render(res)
            return HttpResponse(json_data, content_type='application/json')


class FileCompare(APIView):
    def post(self, request, *args, **kwargs):
        file_id = request.data['file_id']
        files_data = File.objects.filter(id=file_id)
        f_name = files_data[0].filename
        new_file = f_name.replace(".pdf", "")

        json_data = ('./trailapp/json_outputs/' + new_file + ".json")
        json_data = json_data[:-9]+'.json'

        pdf = ('./upload/' + new_file + ".pdf")

        res = {
            "message": "Pdf and Extracted excel data",
            "status": 200,
            "pdf_data": pdf,
            "json_data": json_data,

        }
        json_data = JSONRenderer().render(res)
        return HttpResponse(json_data, content_type='application/json')