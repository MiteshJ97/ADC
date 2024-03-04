from django.db import models
from django.core.files.storage import FileSystemStorage
import os
from rest_framework.viewsets import ModelViewSet
from rest_framework.serializers import ModelSerializer
from datetime import datetime

import json
from economy_research_service.settings import UPLOAD_ROOT
from rest_framework.decorators import api_view
from django.conf import settings
import requests
from rest_framework.response import Response
from django.core.files.base import ContentFile


# Class to remove the existing file.
# This will be used when we need to replace the existing file that is stored with the same name.

class Over_write_storage(FileSystemStorage):
    def get_replace_or_create_file(self, name, max_length=None):
        if self.exists(name):
            os.remove(os.path.join(self.location, name))
            return super(Over_write_storage, self).get_replace_or_create_file(name, max_length)


# upload storage location
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
class Sync_from_source(models.Model):
    source = models.URLField()
    source_name = models.CharField(max_length=30)
    file_content = models.FileField(upload_to=get_file_path, blank=True, null=True, storage=Over_write_storage)
    file_name = models.CharField(max_length=500)
    file_size = models.BigIntegerField(default=0)
    file_type = models.CharField(max_length=20)
    received_on = models.DateTimeField(auto_now_add=True)
    processed_on = models.DateTimeField(null=True)
    status = models.CharField(max_length=12)


    def __str__(self) -> str:
        return self.source
    

# serializer for SyncFromSource model
class Sync_from_source_serializers(ModelSerializer):
    class Meta:
        model = Sync_from_source
        fields = '__all__'


# views for SyncFromSource
class SyncFromSourceView(ModelViewSet):
    queryset = Sync_from_source.objects.all()
    serializer_class = Sync_from_source_serializers


 
class URL_to_be_accessed(models.Model):
    download_URL = models.URLField()
    resource = models.IntegerField(null=True)
    bureau_code = models.CharField(max_length=10)
    modified_on = models.DateField(null=True)
    identifier = models.TextField(null=True)
    access_level = models.TextField(null=True)
    program_code = models.TextField(null=True)
    description = models.TextField(null=True)
    title = models.TextField(null=True)
    media_type = models.TextField(null=True)
    distribution_type = models.TextField(null=True)
    distribution_title = models.TextField(null=True)
    publisher_name = models.TextField(null=True)
    publisher_type = models.TextField(null=True)
    contact_point_email = models.TextField(null=True)
    contact_point_type = models.TextField(null=True)
    contact_point_fn = models.TextField(null=True)
    license = models.TextField(null=True)

    last_accessed_status = models.CharField(max_length=10, default='initial')
    last_accessed_at = models.DateTimeField(default=datetime.now())
    next_due_date = models.DateTimeField(null=True)

    def __str__(self):
        return self.download_URL


class URL_to_be_accessed_serializer(ModelSerializer):
    class Meta:
        model = URL_to_be_accessed
        fields = '__all__'


class URL_to_be_accessed_view(ModelViewSet):
    queryset = URL_to_be_accessed.objects.all()
    serializer_class = URL_to_be_accessed_serializer





def make_entry_of_urls(response, resource_instance, bureau_code):
    json_data_1 = json.loads(response._content.decode('utf-8'))
    data = json_data_1["dataset"]
    result = []
    for item in data:
        obj = URL_to_be_accessed()
        obj.identifier = item.get("identifier", None)
        obj.access_level = item.get("accessLevel", None)
        # obj.program_code = item.get("program_code", None)
        obj.description = item.get("description", None)
        obj.publisher_type = item["publisher"].get('@type', None)
        obj.publisher_name = item["publisher"].get('name', None)

        obj.contact_point_email = (item["contactPoint"].get('hasEmail', None)).split(':')[1]
        obj.contact_point_type = item["contactPoint"].get('@type', None)
        obj.contact_point_fn = item["contactPoint"].get('fn', None)
        # obj.modified_on = item.get("modified", datetime.now())		
        obj.modified_on = item["modified"]	
        obj.license = item.get("license", None)			
        obj.resource = resource_instance.id

        for codes in item['bureauCode']:
            if codes == bureau_code:
                obj.bureau_code = bureau_code
                for distribution in item['distribution']:
                    obj.distribution_title = distribution.get("title", None)
                    obj.distribution_type = distribution.get("@type", None)
                    obj.media_type = distribution.get("mediaType", None)
                    obj.download_URL = distribution["downloadURL"]
                    if not (
                        URL_to_be_accessed.objects.filter(
                            download_URL=distribution["downloadURL"], 
                            modified_on=item["modified"]
                            ).exists()
                        ):
                        result.append(obj)

    try:
        URL_to_be_accessed.objects.bulk_create(result)
        return True
    except Exception as e:
        resource_instance.status="failed"
        resource_instance.save()
        return False





# @api_view(['GET'])
# def read_from_source_json(request):
#     bureau_code = "005:12"
#     response = requests.get(settings.JSON_SOURCE, verify=False)
#     json_data_1 = json.loads(response._content.decode('utf-8'))
#     x = json_data_1["dataset"]
#     data = []
#     for item in x:
#         for codes in item['bureauCode']:
#             if codes == '005:12':
#                 for dist in item['distribution']:
#                     data.append(dist['downloadURL'])
#                     print("###")
#                 continue
#             else:
#                 print("EEE")

#     return Response(data)


@api_view(['GET'])
def read_from_source_json(request):
    bureau_code = "005:12"
    response = requests.get(settings.JSON_SOURCE, verify=False)
    if response.status_code == 200:
        # Retrieve file name and file size from response headers
        content_disposition = response.headers.get('content-disposition')
        if content_disposition:
            file_name = content_disposition.split('filename=')[1]
        else:
            file_name = "data.json"  # Use URL as filename if content-disposition is not provided
        file_size = int(response.headers.get('content-length', 0))
        # file_type = os.path.splitext(file_name)[1]

        resource_instance = Sync_from_source.objects.create(
            file_name = file_name,
            source = settings.JSON_SOURCE,
            processed_on = datetime.today(),
            status = 'success',
            file_size = file_size,
            file_type = "json"
        )
        # save file
        resource_instance.file_content.save(file_name, ContentFile(response.content))

        res = make_entry_of_urls(response, resource_instance, bureau_code)
        if res:
            return Response("success")
        else:
            return Response("failed")

    else:
        Sync_from_source.objects.create(
        file_name = '',
        source = settings.JSON_SOURCE,
        processed_on = datetime.today(),
        status = 'failed',
        file_size = 0,
        file_type = 'none'
        )

    return Response("failed")