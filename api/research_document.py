from django.db import models
from django.core.files.storage import FileSystemStorage
import os
from rest_framework.viewsets import ModelViewSet
from rest_framework.serializers import ModelSerializer
from datetime import datetime

from economy_research_service.settings import UPLOAD_ROOT
from rest_framework.decorators import api_view
from django.conf import settings
import requests
from rest_framework.response import Response
from django.core.files.base import ContentFile


# Class to remove the existing file.
# This will be used when we need to replace the existing file that is stored with the same name.

class OverWriteStorage(FileSystemStorage):
    def get_replace_or_create_file(self, name, max_length=None):
        if self.exists(name):
            os.remove(os.path.join(self.location, name))
            return super(OverWriteStorage, self).get_replace_or_create_file(name, max_length)


upload_storage = FileSystemStorage(location=UPLOAD_ROOT, base_url='/uploads')

# Function to return the storage file path.
# This function will return file path as article_library/Current_year/Current_month/day/file_name_with_extension
# Any downloaded file will be stored like this.
# http://localhost:8000/article_library/2024/2/8/resume.pdf
        
def get_file_path(instance, filename):
    return '{0}/{1}/{2}/{3}'.format(
        datetime.today().year, 
        datetime.today().month,
        datetime.today().day, 
        filename
        )


# Model to record logs of downloaded files/folders from FTP/SFTP's
class ResearchDocument(models.Model):
    source = models.URLField()
    source_name = models.CharField(max_length=30)
    file_content = models.FileField(upload_to=get_file_path, blank=True, null=True, storage=OverWriteStorage())
    file_name = models.CharField(max_length=500)
    file_size = models.BigIntegerField(default=0)
    file_type = models.CharField(max_length=20)
    received_on = models.DateTimeField(auto_now_add=True)
    processed_on = models.DateTimeField(null=True)
    status = models.CharField(max_length=12)
    bureau_code = models.CharField(max_length=20)


    def __str__(self) -> str:
        return self.source
    

# serializer for SyncFromSource model
class ResearchDocumentSerializer(ModelSerializer):
    class Meta:
        model = ResearchDocument
        fields = '__all__'


# views for SyncFromSource
class SyncFromSourceView(ModelViewSet):
    queryset = ResearchDocument.objects.all()
    serializer_class = ResearchDocumentSerializer



def get_from_source_json(url):
    response = requests.get(url, verify=False)
    if response.status_code == 200:
        print(response._content)
        # Retrieve file name and file size from response headers
        content_disposition = response.headers.get('content-disposition')
        if content_disposition:
            file_name = content_disposition.split('filename=')[1]
        else:
            file_name = "xx"  # Use URL as filename if content-disposition is not provided
        file_size = int(response.headers.get('content-length', 0))
        file_type = os.path.splitext(file_name)[1]

        x = ResearchDocument.objects.create(
            file_name = file_name,
            source = url,
            processed_on = datetime.datetime.today(),
            status = 'waiting',
            file_size = file_size,
            file_type = file_type
        )
        # save file
        x.file_content.save('filename', ContentFile(response.content))
        return True

    else:
        ResearchDocument.objects.create(
        file_name = '',
        source = settings.JSON_SOURCE,
        processed_on = datetime.datetime.today(),
        status = 'failed',
        file_size = 0,
        file_type = 'none'
        )

    return False


@api_view(['GET'])
def read_from_source_json(reauest):
    state = get_from_source_json()
    if state:
        pass

