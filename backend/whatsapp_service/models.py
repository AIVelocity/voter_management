# whatsapp_service/models.py
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError

PHONE_VALIDATOR = RegexValidator(regex=r'^\d{10}$', message='Enter 10 digit mobile number')


class VoterChatMessage(models.Model):
    MESSAGE_STATUS = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
        ('received', 'Received'),
    ]

    SENDER_TYPES = [
        ('user', 'User'),
        ('voter', 'Voter'),
    ]

    MESSAGE_TYPES = [
        ('text', 'Text'),
        ('image', 'Image'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('document', 'Document'),
        ('template', 'Template'),
        ('location', 'Location'),
        ('reaction', 'Reaction'),
    ]

    id = models.AutoField(primary_key=True)
    message_id = models.CharField(max_length=200, unique=True)

    voter = models.ForeignKey(
        'application.VoterList',
        db_column='voter_id',
        on_delete=models.CASCADE,
        related_name='chat_messages',
        null=True,
        blank=True,
    )

    sender_user = models.ForeignKey(
        'application.VoterUserMaster',
        db_column='sender_user_id',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='outgoing_messages'
    )

    sender = models.CharField(max_length=20, choices=SENDER_TYPES)
    status = models.CharField(max_length=20, choices=MESSAGE_STATUS)

    message = models.TextField(null=True, blank=True)
    media_id = models.CharField(max_length=200, null=True, blank=True)
    type = models.CharField(max_length=20, choices=MESSAGE_TYPES, default='text')

    media_url = models.TextField(null=True, blank=True)
    file_name = models.TextField(null=True, blank=True)

    latitude = models.CharField(max_length=50, null=True, blank=True)
    longitude = models.CharField(max_length=50, null=True, blank=True)
    location_name = models.CharField(max_length=255, null=True, blank=True)
    location_address = models.TextField(null=True, blank=True)

    reply_to = models.ForeignKey(
        'self',
        db_column='reply_to',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='replies'
    )

    sent_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    # denormalized snapshot for fast reads/historical accuracy
    sender_role = models.CharField(max_length=100, null=True, blank=True)
    sender_role_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "voter_chat_messages"
        indexes = [
            models.Index(fields=["voter", "sent_at"]),
            models.Index(fields=["sender_user", "sent_at"]),
            models.Index(fields=["sender", "sent_at"]),
        ]

    def clean(self):
        errors = {}
        if self.sender == 'user':
            if not self.sender_user:
                errors['sender_user'] = 'sender_user must be provided when sender is user.'
        elif self.sender == 'voter':
            if not self.voter:
                errors['voter'] = 'voter must be provided when sender is voter.'

        if not self.sender_user and not self.voter:
            errors['participant'] = 'Either sender_user or voter must be set.'

        if errors:
            raise ValidationError(errors)

    def _auto_fill_sender_user_for_voter(self):
        from django.apps import apps
        try:
            VoterUserMaster = apps.get_model('application', 'VoterUserMaster')
        except Exception:
            VoterUserMaster = None

        if self.sender == 'voter' and self.voter_id and not self.sender_user_id and VoterUserMaster:
            try:
                if hasattr(self.voter, 'volunteer_pk') and self.voter.volunteer_pk:
                    candidate = VoterUserMaster.objects.filter(user_id=self.voter.volunteer_pk).first()
                    if candidate:
                        self.sender_user = candidate
                        try:
                            role_obj = candidate.role_id
                            if role_obj:
                                self.sender_role = getattr(role_obj, 'role_name', None)
                                self.sender_role_id = getattr(role_obj, 'role_id', None)
                        except Exception:
                            pass
                        return
                if hasattr(self.voter, 'volunteer_mobile') and getattr(self.voter, 'volunteer_mobile'):
                    candidate = VoterUserMaster.objects.filter(mobile_no=self.voter.volunteer_mobile).first()
                    if candidate:
                        self.sender_user = candidate
                        try:
                            role_obj = candidate.role_id
                            if role_obj:
                                self.sender_role = getattr(role_obj, 'role_name', None)
                                self.sender_role_id = getattr(role_obj, 'role_id', None)
                        except Exception:
                            pass
                        return
            except Exception:
                pass

    def save(self, *args, **kwargs):
        self._auto_fill_sender_user_for_voter()
        if self.sender_user_id and not self.sender_role:
            from django.apps import apps
            try:
                role = getattr(self.sender_user, 'role_id', None)
                if role:
                    self.sender_role = getattr(role, 'role_name', None)
                    self.sender_role_id = getattr(role, 'role_id', None)
            except Exception:
                pass
        self.full_clean()
        super().save(*args, **kwargs)

    def get_recipient_agent(self):
        if self.sender == 'voter' and self.sender_user_id:
            return ('user', self.sender_user)
        if self.sender == 'user' and self.voter_id:
            return ('voter', self.voter)
        return (None, None)

    def mark_read(self, when=None):
        when = when or timezone.now()
        self.read_at = when
        self.status = 'read'
        self.save(update_fields=['read_at', 'status'])

    def __str__(self):
        target = f"voter_id={self.voter_id}" if self.voter_id else "user chat"
        return f"#{self.id} {self.sender} -> {target} ({self.status})"


class TemplateName(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        db_table = "template_names"
        ordering = ['name']
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name
