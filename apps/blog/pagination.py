from rest_framework.pagination import PageNumberPagination

class PostPagination(PageNumberPagination):
    page_size = 6                 # nombre de posts par page
    page_size_query_param = "page_size"  # ?page_size=12
    max_page_size = 24
