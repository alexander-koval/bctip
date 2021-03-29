from django.shortcuts import render
from django.utils.deprecation import MiddlewareMixin


class FacebookFakeRootMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        ua = request.META.get('HTTP_USER_AGENT')
        if ua and "facebookexternalhit" in ua:
            return render(request, "index.html", {})
        else:
            return response
