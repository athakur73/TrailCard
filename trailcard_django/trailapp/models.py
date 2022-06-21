from django.db import models

# Create your models here.


class File(models.Model):
    class Meta:
        db_table = "file"

    filename = models.CharField(max_length=250, default="")
    uploaded_by = models.IntegerField()
    file_status = models.IntegerField()
    uploaded_date = models.DateTimeField()
    last_modified_date = models.DateTimeField()
    last_modified_by = models.IntegerField()
    is_delete = models.BooleanField(default=False)

    file = models.FileField(blank=False)
