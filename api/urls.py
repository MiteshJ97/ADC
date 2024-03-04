from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .source_json import SyncFromSourceView, URL_to_be_accessed_view, read_from_source_json
from .research_document import download_research_documents
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register('fetch', SyncFromSourceView)
router.register('url-to-be-accessed', URL_to_be_accessed_view)

urlpatterns = [
    path('', include(router.urls)),
    path('download-research-doc/', download_research_documents),
    path('read-from-source/', read_from_source_json),
]


