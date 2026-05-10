from django.urls import path
from .views import SearchView, SearchImageView, HistoryView, HistoryDetailView

urlpatterns = [
    path("search/", SearchView.as_view()),
    path("search/image/", SearchImageView.as_view()),
    path("history/", HistoryView.as_view()),
    path("history/<int:query_id>/", HistoryDetailView.as_view()),
]