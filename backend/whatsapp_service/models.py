from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator
from django.contrib.auth.hashers import make_password, check_password

from django.core.exceptions import ValidationError

PHONE_VALIDATOR = RegexValidator(regex=r'^\d{10}$', message='Enter 10 digit mobile number')

class Admin(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=120, null=True, blank=True)
    middle_name = models.CharField(max_length=120, null=True, blank=True)
    last_name = models.CharField(max_length=120, null=True, blank=True)
    full_name = models.CharField(max_length=360, null=True, blank=True)
    mobile_no = models.CharField(max_length=10, unique=True, validators=[PHONE_VALIDATOR])
    password = models.CharField(max_length=128)  # store hashed
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "admin"
        indexes = [
            models.Index(fields=["mobile_no"]),
        ]

    def save(self, *args, **kwargs):
        # if password is not hashed (a simple heuristic: no $ in it), hash it
        if self.password and '$' not in self.password:
            self.password = make_password(self.password)
        if not self.full_name:
            names = [self.first_name, self.middle_name, self.last_name]
            self.full_name = " ".join(p for p in names if p)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.full_name or self.mobile_no} (Admin)"

class SubAdmin(models.Model):
    id = models.AutoField(primary_key=True)
    admin_pk = models.ForeignKey(Admin, db_column='admin_pk', on_delete=models.CASCADE, related_name='subadmins')
    first_name = models.CharField(max_length=120, null=True, blank=True)
    middle_name = models.CharField(max_length=120, null=True, blank=True)
    last_name = models.CharField(max_length=120, null=True, blank=True)
    full_name = models.CharField(max_length=360, null=True, blank=True)
    mobile_no = models.CharField(max_length=10, unique=True, validators=[PHONE_VALIDATOR])
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "sub_admin"
        indexes = [models.Index(fields=["admin_pk"]), models.Index(fields=["mobile_no"])]

    def save(self, *args, **kwargs):
        if self.password and '$' not in self.password:
            self.password = make_password(self.password)
        if not self.full_name:
            names = [self.first_name, self.middle_name, self.last_name]
            self.full_name = " ".join(p for p in names if p)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.full_name or self.mobile_no} (SubAdmin)"

class Volunteer(models.Model):
    id = models.AutoField(primary_key=True)
    subadmin_pk = models.ForeignKey(SubAdmin, db_column='subadmin_pk', on_delete=models.CASCADE, related_name='volunteers')
    first_name = models.CharField(max_length=120, null=True, blank=True)
    middle_name = models.CharField(max_length=120, null=True, blank=True)
    last_name = models.CharField(max_length=120, null=True, blank=True)
    full_name = models.CharField(max_length=360, null=True, blank=True)
    mobile_no = models.CharField(max_length=10, unique=True, validators=[PHONE_VALIDATOR])
    password = models.CharField(max_length=128)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "volunteer"
        indexes = [models.Index(fields=["subadmin_pk"]), models.Index(fields=["mobile_no"])]

    def save(self, *args, **kwargs):
        if self.password and '$' not in self.password:
            self.password = make_password(self.password)
        if not self.full_name:
            names = [self.first_name, self.middle_name, self.last_name]
            self.full_name = " ".join(p for p in names if p)
        super().save(*args, **kwargs)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    def __str__(self):
        return f"{self.full_name or self.mobile_no} (Volunteer)"


class VoterChatMessage(models.Model):
    MESSAGE_STATUS = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('failed', 'Failed'),
        ('received', 'Received'),
    ]

    SENDER_TYPES = [
        ('admin', 'Admin'),
        ('sub-admin', 'Sub Admin'),
        ('volunteer', 'Volunteer'),
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
    ]

    id = models.AutoField(primary_key=True)
    message_id = models.CharField(max_length=200, unique=True)

    # voter is nullable to allow agent<->agent messages
    voter = models.ForeignKey(
        'application.VoterList',
        db_column='voter_id',
        on_delete=models.CASCADE,
        related_name='chat_messages',
        null=True,
        blank=True,
    )

    admin = models.ForeignKey(
        'Admin',
        db_column='admin_pk',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='admin_messages'
    )

    subadmin = models.ForeignKey(
        'SubAdmin',
        db_column='subadmin_pk',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='subadmin_messages'
    )

    volunteer = models.ForeignKey(
        'Volunteer',
        db_column='volunteer_pk',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='volunteer_messages'
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

    class Meta:
        db_table = "voter_chat_messages"
        indexes = [
            models.Index(fields=["voter", "sent_at"]),
            models.Index(fields=["admin", "sent_at"]),
            models.Index(fields=["subadmin", "sent_at"]),
            models.Index(fields=["volunteer", "sent_at"]),
            models.Index(fields=["sender", "sent_at"]),
        ]

    def clean(self):
        """
        Validation rules:
          - If sender == 'admin'  -> admin must be set; subadmin & volunteer must be NULL.
          - If sender == 'sub-admin' -> subadmin must be set; admin & volunteer must be NULL.
          - If sender == 'volunteer' -> volunteer must be set; admin & subadmin must be NULL.
          - If sender == 'voter' -> voter must be set; agent FKs must be NULL.
          - If voter is NULL, message must be agent<->agent (sender cannot be 'voter').
        """
        errors = {}

        # Check sender-specific required agent
        if self.sender == 'admin':
            if not self.admin:
                errors['admin'] = 'admin must be provided when sender is admin.'
            if self.subadmin:
                errors['subadmin'] = 'subadmin must be NULL when sender is admin.'
            if self.volunteer:
                errors['volunteer'] = 'volunteer must be NULL when sender is admin.'
        elif self.sender == 'sub-admin':
            if not self.subadmin:
                errors['subadmin'] = 'subadmin must be provided when sender is sub-admin.'
            if self.admin:
                errors['admin'] = 'admin must be NULL when sender is sub-admin.'
            if self.volunteer:
                errors['volunteer'] = 'volunteer must be NULL when sender is sub-admin.'
        elif self.sender == 'volunteer':
            if not self.volunteer:
                errors['volunteer'] = 'volunteer must be provided when sender is volunteer.'
            if self.admin:
                errors['admin'] = 'admin must be NULL when sender is volunteer.'
            if self.subadmin:
                errors['subadmin'] = 'subadmin must be NULL when sender is volunteer.'
        elif self.sender == 'voter':
            if not self.voter:
                errors['voter'] = 'voter must be provided when sender is voter.'
            if self.admin or self.subadmin or self.volunteer:
                errors['agent'] = 'agent fields must be NULL when sender is voter.'

        # If voter is None, sender cannot be 'voter'
        if self.voter is None and self.sender == 'voter':
            errors['voter'] = 'voter sender cannot be used when voter is NULL.'

        if errors:
            raise ValidationError(errors)

    def _auto_fill_volunteer_for_voter_sender(self):
        """
        If message is from a voter and volunteer is not set, attempt to auto-fill
        the volunteer from voter assignment. Supports two possible shapes:
         - VoterList has a 'volunteer_pk' column/property, OR
         - VoterList has a related VoterAssignment accessible at .assignment.volunteer_id
        If a volunteer id is found we set volunteer_id (not volunteer object) to avoid extra queries.
        """
        if self.sender == 'voter' and self.voter_id and not self.volunteer_id:
            try:
                # preferred: direct column on VoterList
                if hasattr(self.voter, 'volunteer_pk') and self.voter.volunteer_pk:
                    self.volunteer_id = self.voter.volunteer_pk
                    return
                # fallback: VoterAssignment relation named 'assignment'
                assignment = getattr(self.voter, 'assignment', None)
                if assignment and getattr(assignment, 'volunteer_id', None):
                    self.volunteer_id = assignment.volunteer_id
                    return
            except Exception:
                # swallow any lookup exceptions and leave volunteer_id as-is (NULL)
                pass

    def save(self, *args, **kwargs):
        # Auto-fill recipient volunteer for voter messages (immutable snapshot)
        self._auto_fill_volunteer_for_voter_sender()

        # run validation for safety
        self.full_clean()
        super().save(*args, **kwargs)

    # ---------- helper methods ---------- #
    def get_recipient_agent(self):
        """
        Returns (agent_type, agent_object) tuple for the message recipient as detected:
        - For agent->voter messages: returns (None, None) because recipient is the voter.
        - For voter->agent messages (or messages where volunteer was auto-filled): returns ('volunteer', Volunteer instance) etc.
        - For agent<->agent messages: returns the agent object on the other side if determinable.
        Note: this is a best-effort helper; use application logic for precise routing.
        """
        # If volunteer_id exists and sender is voter => recipient is volunteer
        if self.volunteer_id and self.sender == 'voter':
            return ('volunteer', self.volunteer)

        # If sender is an agent and voter is set => recipient is voter
        if self.sender in ('admin', 'sub-admin', 'volunteer') and self.voter_id:
            return ('voter', self.voter)

        # Agent<->agent message: we don't track explicit recipient column.
        # You may implement recipient_admin/subadmin/volunteer later if needed.
        return (None, None)

    def mark_read(self, when=None):
        when = when or timezone.now()
        self.read_at = when
        self.status = 'read'
        self.save(update_fields=['read_at', 'status'])

    def __str__(self):
        target = f"voter_id={self.voter_id}" if self.voter_id else "agent chat"
        return f"#{self.id} {self.sender} -> {target} ({self.status})"
