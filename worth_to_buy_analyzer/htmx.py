"""HTML fragments with the same authorization and validation as full pages."""

from django.http import HttpResponse
from django.shortcuts import render
from django.utils.cache import patch_vary_headers


def is_partial(request):
    return request.headers.get("HX-Request") == "true" and request.headers.get("HX-History-Restore-Request") != "true"


def page_or_fragment(request, page, fragment, context):
    response = render(request, fragment if is_partial(request) else page, context)
    patch_vary_headers(response, ("HX-Request", "HX-History-Restore-Request"))
    response.headers["Cache-Control"] = "no-store"
    return response


def login_redirect(request, response):
    if is_partial(request):
        return HttpResponse(headers={"HX-Redirect": response.url, "Cache-Control": "no-store"})
    return response
