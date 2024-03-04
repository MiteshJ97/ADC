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

class Over_write_storage(FileSystemStorage):
    def get_replace_or_create_file(self, name, max_length=None):
        if self.exists(name):
            os.remove(os.path.join(self.location, name))
            return super(Over_write_storage, self).get_replace_or_create_file(name, max_length)


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
    file_content = models.FileField(upload_to=get_file_path, blank=True, null=True, storage=Over_write_storage())
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
        model = Over_write_storage
        fields = '__all__'


# views for SyncFromSource
class SyncFromSourceView(ModelViewSet):
    queryset = Sync_from_source.objects.all()
    serializer_class = Sync_from_source_serializers



class URL_to_be_accessed(models.Model):
    download_URL = models.URLField()
    resource = models.ForeignKey(Sync_from_source, on_delete=models.CASCADE)
    bureau_code = models.CharField(max_length=10)
    modified_on = models.DateField()
    identifier = models.TextField()
    access_level = models.TextField()
    program_code = models.TextField()
    description = models.TextField()
    title = models.TextField()
    media_type = models.TextField()
    distribution_type = models.TextField()
    distribution_title = models.TextField()
    publisher_name = models.TextField()
    publisher_type = models.TextField()
    contact_point_email = models.TextField()
    contact_point_type = models.TextField()
    contact_point_fn = models.TextField()

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





def make_entry_of_urls(data, bureau_code):
    a = 0
    for item in data["dataset"]:
        obj = URL_to_be_accessed()
        # Check if the "bureauCode" value matches the desired value
        if "bureauCode" in item and bureau_code in item["bureauCode"]:
            obj.bureau_code = bureau_code
            obj.modified = item["modified"]
            # Check if the item has a "distribution" field
            if "distribution" in item:
                # Iterate through the distributions
                for distribution in item["distribution"]:
                    obj.distribution_title = distribution[0]["title"]
                    obj.distribution_type = distribution[0]["type"]
                    obj.media_type = distribution[0]["mediaType"]
                    obj.license = distribution["license"]

                    # Check if the distribution has a "downloadURL" field
                    if "downloadURL" in distribution:
                        obj.download_URL = distribution[0]["downloadURL"]
                        obj.save()
                        a+=1

    return Response(f'''all done. Total new entry made : {a}''')



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
            file_name = "xx"  # Use URL as filename if content-disposition is not provided
        file_size = int(response.headers.get('content-length', 0))
        file_type = os.path.splitext(file_name)[1]

        x = Sync_from_source.objects.create(
            file_name = file_name,
            source = settings.JSON_SOURCE,
            processed_on = datetime.today(),
            status = 'success',
            file_size = file_size,
            file_type = file_type
        )
        # save file
        x.file_content.save(file_name, ContentFile(response.content))
        make_entry_of_urls(x, bureau_code)
        return Response("success")

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