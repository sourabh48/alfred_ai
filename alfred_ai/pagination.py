from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class OptionalPageNumberPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100

    def get_page_size(self, request):
        return super().get_page_size(request) or self.page_size

    def get_paginated_response(self, data):
        response = Response(data)
        response["X-Total-Count"] = str(self.page.paginator.count)
        response["X-Page"] = str(self.page.number)
        response["X-Page-Size"] = str(self.get_page_size(self.request))
        response["X-Has-Next"] = "true" if self.page.has_next() else "false"
        response["X-Has-Previous"] = "true" if self.page.has_previous() else "false"
        if self.page.has_next():
            response["X-Next-Page"] = str(self.page.next_page_number())
        if self.page.has_previous():
            response["X-Previous-Page"] = str(self.page.previous_page_number())
        return response
