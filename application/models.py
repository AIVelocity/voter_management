from django.db import models


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


class VoterList(models.Model):

    voter_list_id = models.AutoField(primary_key=True)

    sr_no = models.IntegerField()

    voter_id = models.CharField(max_length=20, null=True, blank=True)

    voter_name_marathi = models.TextField(null=True, blank=True)
    voter_name_eng = models.TextField(null=True, blank=True)

    surname = models.TextField(null=True, blank=True)
    first_name = models.TextField(null=True, blank=True)
    father_or_husband_name = models.TextField(null=True, blank=True)

    kramank = models.CharField(max_length=20, null=True, blank=True)

    current_address = models.TextField(null=True, blank=True)
    permanent_address = models.TextField(null=True, blank=True)

    age = models.CharField(max_length=10, null=True, blank=True)
    age_eng = models.IntegerField(null=True, blank=True)

    gender = models.TextField(null=True, blank=True)
    gender_eng = models.CharField(max_length=10, null=True, blank=True)

    image_name = models.CharField(max_length=255, null=True, blank=True)

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
