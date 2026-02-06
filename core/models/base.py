from django.db import models


# Create your models here.
class BaseModels:
    created_at = models.DateTimeField(auto_now_add=True)
    Updated_at = models.DateField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        abstract = True