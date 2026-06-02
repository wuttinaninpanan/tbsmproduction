# tbapp สร้างสภาพแวดล้อมสำหรับพัฒนาระบบ
# Django Start project

ด้วยคำสั่ง
```
docker compose exec web bash
poetry run python manage.py runserver 0.0.0.0:8000
poetry run python manage.py tailwind start
```

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

<!-- 1) สร้าง Google App Password (ผมทำแทนไม่ได้)

เปิด 2-Step Verification ที่บัญชี Google ก่อน → https://myaccount.google.com/security
สร้าง App Password ที่ → https://myaccount.google.com/apppasswords
จะได้รหัส 16 หลัก → วางลงบรรทัด EMAIL_HOST_PASSWORD= (พิมพ์ติดกัน ไม่ต้องเว้นวรรค) -->

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


### การDump data ปัจจุบัน
```
poetry run python manage.py data_dump

```
### การโหลดData ที่Dumpใว้เข้าฐานข้อมูล

มี 3 วิธี เลือกตามสถานการณ์

**1) โหลดอัตโนมัติตอน migrate (เฉพาะฐานข้อมูลว่าง)**
เมื่อ clone โปรเจกต์ลงเครื่องใหม่ / ฐานข้อมูลยังว่าง (ยังไม่มี user) แค่รัน migrate ระบบจะโหลด `master_seed.json` ให้อัตโนมัติ
ถ้าฐานข้อมูลมีข้อมูลอยู่แล้ว จะ **ไม่ทำอะไร** (ไม่ทับข้อมูลเดิม)
```
poetry run python manage.py migrate
```
ปิดการโหลดอัตโนมัติได้ด้วย env (ใส่ใน .env.local)
```
DISABLE_AUTO_SEED=1
```

**2) โหลดแบบ merge/upsert (ไม่ลบของเดิม)**
โหลดเข้าฐานที่มีข้อมูลอยู่แล้ว — แถวที่ primary key ซ้ำจะถูก "เขียนทับ" ด้วยข้อมูลจากไฟล์, แถว PK ใหม่จะถูกเพิ่ม, ส่วนแถวเดิมที่ไม่มีในไฟล์จะ **ไม่ถูกลบ**
```
poetry run python manage.py loaddata core/fixtures/master_seed.json
```

**3) โหลดแบบ mirror เต็ม (ลบของเดิมทั้งหมดแล้วโหลดใหม่)**
อันตราย — ลบทุกแถวใน seed tables แล้วโหลดจากไฟล์ ทำให้ข้อมูลตรงกับไฟล์เป๊ะ
```
poetry run python manage.py data_load --no-input
```

### Build แบบไม่กระทบDB_load 
```
docker compose up -d --no-deps --force-recreate web
```

### Sync employee data from tbapp_application

`core/fixtures/employee_seed.json` is a snapshot of users and employee master
data from `tbapp_application`. The sync command updates users by `username`, so
existing ERP foreign keys remain valid. It replaces only employee records when
`--replace` is used; local-only ERP users are retained.

```shell
poetry run python manage.py migrate
poetry run python manage.py sync_employee_data --replace
poetry run python manage.py data_dump
```

Existing local passwords are preserved during sync. Add `--sync-passwords`
only when local password hashes must be refreshed from the source snapshot.

To refresh the employee snapshot, copy `tbapp_application/core/fixtures/fixture.json`
to `core/fixtures/employee_seed.json` before running the sync command. The
importer ignores unrelated cloud models.
