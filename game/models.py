from django.db import models


class ImportedGame(models.Model):
    pgn        = models.TextField()
    white      = models.CharField(max_length=100, blank=True)
    black      = models.CharField(max_length=100, blank=True)
    event      = models.CharField(max_length=200, blank=True)
    date       = models.CharField(max_length=20, blank=True)
    result     = models.CharField(max_length=10, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def display_name(self):
        name = f"{self.white} vs {self.black}" if self.white or self.black else "Unknown"
        if self.event:
            name += f" — {self.event}"
        return name

    def __str__(self):
        return self.display_name()
