# tbapp สร้างสภาพแวดล้อมสำหรับพัฒนาระบบ
# Django Start project
สร้างไฟล์โดยตั้งชื่อดังนี้
```
.env.local
```
นำโค๊ดนี้ไปใส่ในไฟล์ชื่อ .env.local
```
POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=app_password
POSTGRES_HOST=db
POSTGRES_PORT=5432
DJANGO_SETTINGS_MODULE=config.settings.local
```

ไฟล์ที่ต้องมี
```
folder project
   |-- docker
        |-Dockerfile
        |-Dockerfile.local
   |-- docker-compose.yaml
   |-- .env.local
   |-- pyproject.toml
```

Biuld docker image
```
docker compose build
```

กรณีbuildไม่ได้
```
docker compose build --no--cache
```

เมื่อBuildเสร็จให้ run docker composeสร้างContainer
```
docker compose up -d
```

เข้าContainer
```
docker compose exec web bash
```

ติดตั้งLibraryที่จำเป็นผ่านไฟล์pyproject.toml
เช่น python , django , psycopg , django-tailwind , pillow etc.
```
poetry install --no-root
```

สร้างโปรเจ็คท์Django => ตั้งชื่อว่า config
```
poetry run django-admin startproject config .
```

สร้างapplication Django => ตั้งชื่อว่า core
```
poetry run python manage.py startapp core
```
#ไฟล์Setting
สร้างfolderใหม่ในconfigชื่อsettings
เปลี่ยนชื่อไฟล์setting.py เป็นbase.pyแล้วย้ายไปเก็บในโฟล์เดอร์settings
สร้างไฟล์ __init__.py ในโฟล์เดอร์settings
สร้างไฟล์ local.py ในโฟล์เดอร์settings
```
project
  |- config
      |-- settings
           |- __init__.py
           |-base.py
           |- local.py
```

ในไฟล์local.py
```
from .base import *
```

ในไฟล์base.py
เพิ่ม 'tailwind', เข้าไปในINSTALLED_APPSตามตัวอย่างข้างล่าง
```
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tailwind',
]

```
ติดตั้งTailwind css
```
poetry add django-tailwind
```

สร้างDirectoryสำหรับcss
```
poetry run python manage.py tailwind init
```

จะมีคำถามให้สร้างชื่อtheme
Enter Tailwind app name [theme]:theme
```
theme
```

จะขึ้นแบบนี้ให้เลือกให้กด 3
```
1 - Tailwind v4 Standalone - Simple and doesn't require Node.js
2 - Tailwind v4 Full - All the bells and whistles, requires Node.js
3 - Tailwind v3 Full - Legacy template for Tailwind v3 projects, requires Node.js
Enter choice [1-3]:
```
เมื่อขึ้นแบบนี้ให้กด y
```
Include DaisyUI component library? (y/n):
```

run node
```
 cd theme/static_src/
 npm install
```

กลับมาที่app
```
 cd ../..
```

# ทดสอบrunserver
```
poetry run python manage.py runserver 0.0.0.0:8000
```
http://localhost:8001/


## ติดตั้งสำเร็จ
# การตั้งค่าในไฟล์base.py
เพิ่มcode : import os
```
from pathlib import Path
import os
TAILWIND_APP_NAME = 'theme'
```

เพิ่ม .parent ไปอีก 1 ให้เป็น 3
```
BASE_DIR = Path(__file__).resolve().parent.parent.parent
```

เพิ่มappและcssเข้าไปใน INSTALLED_APPS
```
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
    'tailwind',
    'theme',
]
```

SECRET_KEY , DEBUG MODE , ALLOWED_HOSTS
```
SECRET_KEY = os.getenv("SECRET_KEY", "unsafe-secret")
```
```
DEBUG = os.getenv("DEBUG", "True") == "True"
```
```
ALLOWED_HOSTS = ["*"]
```
TEMPLATES
```
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR/'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]
```
DATABASES
```
DATABASES = {
"default": {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": os.environ.get("POSTGRES_DB"),
    "USER": os.environ.get("POSTGRES_USER"),
    "PASSWORD": os.environ.get("POSTGRES_PASSWORD"),
    "HOST": os.environ.get("POSTGRES_HOST"),
    "PORT": os.environ.get("POSTGRES_PORT", "5432"),
  }
}
```

STATIC
```
STATIC_URL = "/static/"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
```

สุดท้ายเป็น 2 Terminal
เข้าสู่containerทั้ง 2 Terminal
ด้วยคำสั่ง
```
docker compose exec web bash
```
Terminalที่ 1 run [Run server]
```
poetry run python manage.py runserver 0.0.0.0:8000
```
Terminalที่ 2 run [Run Tailwind watch]
```
poetry run python manage.py tailwind start
```

# อื่นๆ

เกี่ยวกับpoetry
ทุกครั้งที่มีการBuild projectใหม่จะต้องรันคำสั่งนีัทุกครั้ง
```
poetry install --no-root
```

หากต้องการลงLibraryสามารถใช้คำสั่งนี้ได้
```
poetry add <Library>
```

migrate Run modelสร้างตารางในฐานข้อมูล
```
poetry run python manage.py migrate
```

# ลำดับขั้นตอน การทำให้รองรับได้หลายภาษา
① พิมพ์{% trans %} ลงในTemplateหรือpython
```
{% trans "Workbook list" %}
```

② Run makemessages
```
poetry run python manage.py makemessages -l ja
poetry run python manage.py makemessages -l en
poetry run python manage.py makemessages -l th
```

③ msgstr
```
msgid "problem list"
msgstr "รายการปัญหา"
```

④ compile
```
poetry run python manage.py compilemessages
```

⑤ เปิดหน้าเว็บ
http://localhost:8001/th


# เกี่ยวกับฐานข้อมูล
เวลาที่ต้องการดูฐานข้อมูล
```
docker-compose exec database bash 
```
Loginเข้าposgre
```
psql -U tbapp_user -d tbapp_db
```

ดูตาราง
```
\dt
```