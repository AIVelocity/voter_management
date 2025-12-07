from django.db import models


# roles list
class Roles(models.Model):
    role_id = models.AutoField(primary_key=True)
    role_name = models.CharField(
        max_length=100,
        unique=True,
        db_column="role"
    )
    
    created_by = models.IntegerField(null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)

    updated_by = models.IntegerField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    deleted_by = models.IntegerField(null=True, blank=True)
    deleted_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "voter_role_master"
        managed = False
    
    def __str__(self):
        return self.role_name

# voter tags list
class VoterTag(models.Model):
    tag_id = models.AutoField(primary_key=True)

    tag_name = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)

    created_by = models.IntegerField(null=True, blank=True)
    created_date = models.DateTimeField(null=True, blank=True)

    updated_by = models.IntegerField(null=True, blank=True)
    updated_date = models.DateTimeField(null=True, blank=True)

    deleted_by = models.IntegerField(null=True, blank=True)
    deleted_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "voter_tags"
        managed = False

    def __str__(self):
        return self.tag_name


# voters list
class VoterList(models.Model):

    voter_list_id = models.AutoField(primary_key=True)

    sr_no = models.IntegerField()

    voter_id = models.CharField(max_length=20, null=True, blank=True)

    voter_name_marathi = models.TextField(null=True, blank=True)
    voter_name_eng = models.TextField(null=True, blank=True)

    initial_full_name = models.TextField(null=True, blank=True)

    last_name = models.TextField(null=True, blank=True)
    first_name = models.TextField(null=True, blank=True)
    middle_name = models.TextField(null=True, blank=True)

    kramank = models.CharField(max_length=20, null=True, blank=True)

    current_address = models.TextField(null=True, blank=True)
    permanent_address = models.TextField(null=True, blank=True)

    address_line1 = models.TextField(null=True, blank=True)
    address_line2 = models.TextField(null=True, blank=True)
    address_line3 = models.TextField(null=True, blank=True)

    age = models.CharField(max_length=10, null=True, blank=True)

    age_eng = models.TextField(null=True, blank=True)

    gender = models.TextField(null=True, blank=True)
    gender_eng = models.CharField(max_length=10, null=True, blank=True)

    image_name = models.CharField(max_length=255, null=True, blank=True)

    mobile_no = models.CharField(max_length=10, null=True, blank=True)
    alternate_mobile1 = models.CharField(max_length=10, null=True, blank=True)
    alternate_mobile2 = models.CharField(max_length=10, null=True, blank=True)
    badge = models.TextField(null=True, blank=True)
    location = models.TextField(null=True, blank=True)
    occupation = models.TextField(null=True,blank=True)
    cast = models.TextField(null=True,blank=True)
    organisation = models.TextField(null=True,blank=True)

    tag_id = models.ForeignKey(
        VoterTag,
        db_column="tag_id",
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True
    )

    ward_no = models.IntegerField()

    class Meta:
        db_table = "voter_list"
        managed = False
        unique_together = ("sr_no", "ward_no")

    def __str__(self):
        return str(self.voter_id)

# models.py

from django.db import models

class VoterRelationshipDetails(models.Model):

    RELATION_CHOICES = [
        ("father", "Father"),
        ("mother", "Mother"),
        ("husband", "Husband"),
        ("wife", "Wife"),
        ("child", "Child"),
        ("brother", "Brother"),
        ("sister", "Sister"),
        ("sibling", "Sibling"),
    ]

    id = models.BigAutoField(primary_key=True)

    # maps -> voter_list_id (FK voter_list.voter_list_id)
    voter = models.ForeignKey(
        "VoterList",
        db_column="voter_list_id",
        on_delete=models.DO_NOTHING,
        related_name="relations"
    )

    # maps -> related_voter_id (FK voter_list.voter_list_id)
    related_voter = models.ForeignKey(
        "VoterList",
        db_column="related_voter_id",
        on_delete=models.DO_NOTHING,
        related_name="related_to"
    )

    # maps -> relation_with_voter
    relation_with_voter = models.CharField(
        max_length=20,
        choices=RELATION_CHOICES
    )

    # maps -> created_at timestamptz
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "voter_relationship_details"
        unique_together = (
            ("voter", "related_voter", "relation_with_voter"),
        )
        managed = False

    def __str__(self):
        return f"{self.voter.voter_list_id} - {self.relation_with_voter} -> {self.related_voter.voter_list_id}"
