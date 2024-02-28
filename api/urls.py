from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .source_json import SyncFromSourceView, read_from_source_json
from django.conf import settings
from django.conf.urls.static import static

router = DefaultRouter()
router.register('fetch', SyncFromSourceView)

urlpatterns = [
    path('', include(router.urls)),
    path('read_from_source_json', read_from_source_json),
]


