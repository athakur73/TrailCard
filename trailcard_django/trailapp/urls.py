from django.urls import path
from trailapp.views import UploadFile, Redact

app_name = "trailapp"

urlpatterns = [
    path('upload_file/', UploadFile.as_view(), name='upload_file'),
    path('redact/', Redact.as_view(), name='file_redact')
]
