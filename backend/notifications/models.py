from django.db import models

class Notification(models.Model):
    title = models.CharField(max_length=255)
    message = models.TextField()
    to_role = models.CharField(max_length=100, null=True, blank=True)   # e.g. "admin"
    to_agent = models.IntegerField(null=True, blank=True)               # agent id target
    to_user_id = models.IntegerField(null=True, blank=True)             # direct user id
    meta = models.JSONField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
