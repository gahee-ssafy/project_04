from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field
from drf_spectacular.types import OpenApiTypes
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


class SearchImageRequestSerializer(serializers.Serializer):
    """POST /search/image 요청 바디 유효성 검사"""
    query = serializers.CharField(min_length=1, max_length=1000)

    @extend_schema_field(OpenApiTypes.BINARY)
    def get_image(self, obj):
        return obj.get("image")

    image = serializers.ImageField()
    image._spectacular_annotation = {"field": OpenApiTypes.BINARY}