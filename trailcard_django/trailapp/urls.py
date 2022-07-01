from django.urls import path
from trailapp.views import UploadFile, Redact, FileDelete, ListOfFile, FileCompare, FileDownload

app_name = "trailapp"

urlpatterns = [
    path('upload_file/', UploadFile.as_view(), name='upload_file'),
    path('redact/', Redact.as_view(), name='file_redact'),
    path('delete/', FileDelete.as_view(), name='file_delete'),
    path('list/', ListOfFile.as_view(), name='file_list'),
    path('compare/', FileCompare.as_view(), name='file_compare'),
    path('file_download/', FileDownload.as_view(), name='file_download'),

]
