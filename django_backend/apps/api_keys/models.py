import hashlib
import secrets
import uuid

from django.conf import settings
from django.db import models


class APIKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="api_keys",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_api_keys",
    )
    name = models.CharField(max_length=255)
    key_hash = models.CharField(max_length=64)
    prefix = models.CharField(max_length=8)
    scopes = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "api_keys_apikey"
        ordering = ["-created_at"]
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"
        indexes = [
            models.Index(fields=["organization"]),
            models.Index(fields=["key_hash"]),
            models.Index(fields=["prefix"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"{self.organization.name} / {self.name} ({self.prefix}...)"

    @classmethod
    def generate_key(cls):
        """Generate a new API key and return (plain_key, key_hash, prefix)"""
        plain_key = f"sk_{secrets.token_urlsafe(32)}"
        key_hash = hashlib.sha256(plain_key.encode()).hexdigest()
        prefix = plain_key[:8]
        return plain_key, key_hash, prefix

    @classmethod
    def hash_key(cls, plain_key):
        """Hash a plain API key"""
        return hashlib.sha256(plain_key.encode()).hexdigest()

    def verify_key(self, plain_key):
        """Verify a plain API key against the stored hash"""
        return self.key_hash == self.hash_key(plain_key)
