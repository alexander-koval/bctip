from django.conf import settings
from django.conf.urls import url
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin

from core import views

admin.autodiscover()

urlpatterns = i18n_patterns(
    url(r'^$', views.home, name='home'),
    url(r'^new/$', views.new, name='new'),
    url(r'^statistics/$', views.statistics, name='statistics'),
    url(r'^(?P<key>\w+-\w+-\w+-\w+-\w+)$', views.tip_redir),
    url(r'^(?P<key>\w+-\w+-\w+-\w+-\w+)/$', views.tip),
    url(r'^(?P<key>\w+-\w+-\w+)$', views.tip_redir, name='tip_redir'),
    url(r'^(?P<key>\w+-\w+-\w+)/$', views.tip, name='tip'),
    url(r'^gratuity-example/$', views.tips_example, name='tips_example'),
    url(r'^w/(?P<key>\w+)/$', views.get_wallet, name='wallet'),
    url(r'^w/(?P<key>\w+)/comments/$', views.comments, name='comments'),
    url(r'^w/(?P<key>\w+)/pdf/$', views.download, {'format': "pdf"}, name='download'),
    url(r'^w/(?P<key>\w+)/pdf-us/$', views.download, {'format': "pdf", "page_size": "US"}, name='download'),
    url(r'^w/(?P<key>\w+)/odt/$', views.download, {'format': "odt"}, name='download'),
    url(r'^w/(?P<key>\w+)/png/$', views.download, {'format': "png"}, name='download'),
    url(r'^w/(?P<key>\w+)/wajax/$', views.wajax, name='wajax'),
)

urlpatterns += [
    url(r'^admin/', admin.site.urls),
    url(r'qrcode/(?P<key>\w+)/$', views.qrcode_view, name='qrcode'),
]

if settings.BCTIP_MOD:
    import bctip.urls_custom
    urlpatterns += bctip.urls_custom.urlpatterns