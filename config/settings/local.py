from .base import *
import copy

# Provide an alias `core_user` that points to the same DB as `default`.
DATABASES["core_user"] = copy.deepcopy(DATABASES.get("default", {}))