from rest_framework import serializers
from .models import SearchQuery, SearchSource


class SearchSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SearchSource
        fields = ["id", "title", "url", "snippet", "rank"]


class SearchQuerySerializer(serializers.ModelSerializer):
    sources = SearchSourceSerializer(many=True, read_only=True)

    class Meta:
        model = SearchQuery
        fields = ["id", "query", "answer", "elapsed_seconds", "created_at", "sources"]


class SearchRequestSerializer(serializers.Serializer):
    """POST /search 요청 바디 유효성 검사"""
    query = serializers.CharField(min_length=1, max_length=1000)