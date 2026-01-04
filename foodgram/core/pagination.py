from rest_framework.pagination import PageNumberPagination


class PageNumberLimitPagination(PageNumberPagination):
    pagination_class = PageNumberPagination
    page_size_query_param = 'limit'
    page_size = 20
