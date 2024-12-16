from django.contrib import admin
from django.urls import path, include
from django.conf.urls.static import static

import client_side.urls
import work.urls
from . import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    path('work/', include(work.urls)),
    path('', include(client_side.urls)),  
] 

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
