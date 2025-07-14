from rest_framework.pagination import PageNumberPagination


class PageSizeLimitPagination(PageNumberPagination):
    """Пагинация с лимитом."""
    page_size_query_param = 'limit'
    max_page_size = 100