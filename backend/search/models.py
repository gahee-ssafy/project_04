from django.db import models


class SearchQuery(models.Model):
    query = models.TextField()
    answer = models.TextField(null=True, blank=True)
    elapsed_seconds = models.FloatField(null=True, blank=True)
    image_data = models.BinaryField(null=True, blank=True)  # 이미지 바이트
    image_mime = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_queries"
        ordering = ["-created_at"]

    def __str__(self):
        return self.query[:50]


class SearchSource(models.Model):
    query = models.ForeignKey(SearchQuery, on_delete=models.CASCADE, related_name="sources")
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=2000)
    snippet = models.TextField(null=True, blank=True)
    rank = models.IntegerField(default=1)

    class Meta:
        db_table = "search_sources"
        ordering = ["rank"]

    def __str__(self):
        return self.title