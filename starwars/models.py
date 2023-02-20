from django.db import models

class Metadata(models.Model):
    file_name = models.CharField(max_length=255)
    file_path= models.CharField(max_length=255)
    date = models.DateTimeField(auto_now_add=True)
    etag = models.CharField(max_length=255, default = '')
    table_info_type = models.CharField(max_length=255, default = '')

