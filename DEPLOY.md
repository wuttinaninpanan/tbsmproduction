# Deploy — Synology NAS (Container Manager)

คู่มือ deploy โปรเจกต์นี้ขึ้น **Synology NAS** ผ่านแอป **Container Manager** (เทียบเท่า Docker Desktop บน Windows)

| รายการ | ค่า |
|---|---|
| Server (Local) | Synology NAS — `RD_NAS` |
| IP | `172.29.66.228` |
| OS | Linux (DSM) |
| Path บน NAS | `/volume1/Inhouseapp/tbsmproduction` |
| Port ที่ใช้ | **8003** → เข้าใช้งานที่ http://172.29.66.228:8003 |
| Web server | gunicorn + WhiteNoise (ไม่ต้องมี nginx แยก) |
| Database | PostgreSQL 16 (รันเป็น container `db` ในโปรเจกต์เดียวกัน) |

---

## สถาปัตยกรรม

โปรเจกต์รัน 2 container ผ่าน [docker-compose.prod.yaml](docker-compose.prod.yaml):

- **web** — Django + gunicorn (build จาก [docker/Dockerfile](docker/Dockerfile))
  ตอน start จะรัน **migrate + collectstatic** อัตโนมัติผ่าน [docker/entrypoint.prod.sh](docker/entrypoint.prod.sh)
- **db** — PostgreSQL 16 พร้อม healthcheck (web รอ db พร้อมก่อนค่อยเริ่ม)

ข้อมูลที่ persist ข้ามการ rebuild:
- `postgres_data_prod` — ข้อมูลใน database
- `media_data` — ไฟล์ที่ผู้ใช้อัปโหลด (`/app/media`)

> Tailwind CSS ถูก build แล้ว commit ไว้ใน repo (`theme/static/css/dist/styles.css`)
> ดังนั้น image นี้ **ไม่ต้องใช้ Node** — แค่ collectstatic แล้วเสิร์ฟด้วย WhiteNoise

---

## เตรียมก่อน deploy: ไฟล์ `.env.production`

ไฟล์นี้เก็บ secret ทั้งหมด และถูก **gitignore** (ไม่ขึ้น git) — สร้างไว้แล้วบน NAS

> ถ้ายังไม่มี: `cp .env.example .env.production` แล้วแก้ค่าตามด้านล่าง

ค่าสำคัญที่ต้องตั้ง:

```ini
DJANGO_SETTINGS_MODULE=config.settings.production
SECRET_KEY=<strong random key>          # python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"

POSTGRES_DB=tbsm_prod
POSTGRES_USER=tbsm_user
POSTGRES_PASSWORD=<strong password>
POSTGRES_HOST=db
POSTGRES_PORT=5432

ALLOWED_HOSTS=172.29.66.228,localhost,127.0.0.1
CSRF_TRUSTED_ORIGINS=http://172.29.66.228:8003   # ต้องมี scheme + port ให้ตรง
```

> ⚠️ ถ้าเปลี่ยน port ที่เข้าใช้งาน ต้องแก้ `CSRF_TRUSTED_ORIGINS` ให้ตรง port ด้วย ไม่งั้น login (POST) จะโดน CSRF block

---

## ขั้นตอน Deploy (Container Manager GUI)

### 1. สร้าง Project
Container Manager → เมนู **Project** → **Create**

- **Project Name:** `production_report`
- **Path:** เลือกโฟลเดอร์ **`/Inhouseapp/tbsmproduction/deploy`**  ← ชี้เข้าโฟลเดอร์ย่อย `deploy`
- **File:** Container Manager จะ auto-load `docker-compose.yml` (ตัว prod) ในโฟลเดอร์นั้นให้เอง ไม่ต้องวาง content

> **ทำไมต้องชี้ที่ `deploy/` ?**
> Container Manager จะ auto-detect ไฟล์ compose ในโฟลเดอร์ Path ที่เลือก ถ้าชี้ที่ repo root มันจะหยิบ `docker-compose.yaml` (ตัว **dev** — `sleep infinity`) ผิดตัว
> โฟลเดอร์ `deploy/` มี compose ไฟล์เดียวคือตัว prod ([deploy/docker-compose.yml](deploy/docker-compose.yml)) จึงไม่สับสน และไม่ไปทับไฟล์ dev ที่ใช้ git ร่วมกัน
> (compose ตัวนี้ตั้ง `context: ..` ให้ build จาก repo root และอ้าง `../.env.production`)

### 2. ตรวจ compose ที่ระบบโหลดมา
ยืนยันว่าเป็น prod (มี `dockerfile: docker/Dockerfile`, `ports: "8003:8000"`, `env_file: ../.env.production`) — เนื้อหาเต็มดูได้ที่ [deploy/docker-compose.yml](deploy/docker-compose.yml)

### 3. Build & Run
กด **Next → Build**

Container Manager จะ build image (ครั้งแรก ~3-5 นาที เพราะลง dependencies) แล้วรัน container `web` + `db` ให้เอง
ตอน `web` เริ่ม entrypoint จะรัน **migrate + collectstatic** อัตโนมัติ

### 4. โหลดข้อมูลตั้งต้น (ทำครั้งเดียวหลัง build เสร็จ)
Container Manager → **Container** → เลือก `tbsmproduction-web-1` → แท็บ **Terminal** → **Create** (bash) แล้วรัน:

```bash
python manage.py data_load --no-input
```

คำสั่งนี้จะล้าง seed-managed tables แล้วโหลดจาก `core/fixtures/master_seed.json` (ดูรายละเอียดใน [core/management/commands/data_load.py](core/management/commands/data_load.py))

> ใน prod image poetry ลงแบบ system-wide (`virtualenvs.create false`) จึงเรียก `python manage.py ...` ตรงๆ ได้ — **ไม่ต้องมี** `poetry run`

### 5. เข้าใช้งาน
เปิดเบราว์เซอร์ → **http://172.29.66.228:8003**

---

## งานหลัง deploy ที่อาจต้องทำ

### รหัสผ่าน login
ผู้ใช้มาจาก `master_seed.json` (ใช้รหัสเดิมจากต้นทาง) ถ้าจำไม่ได้ ใน Terminal ของ container `web`:

```bash
python manage.py createsuperuser          # สร้าง admin ใหม่
python manage.py changepassword <username> # เปลี่ยนรหัสผู้ใช้เดิม
```

### เปลี่ยน port
แก้ `ports: - "8003:8000"` ในcompose (เลขซ้าย = port บน NAS) แล้วแก้ `CSRF_TRUSTED_ORIGINS` ใน `.env.production` ให้ตรง จากนั้น rebuild project

### ตั้งค่า email จริง
ตอนนี้ `EMAIL_HOST` ว่าง = ใช้ console backend (ไม่ส่งจริง) เติมค่า `EMAIL_HOST` / `EMAIL_HOST_USER` / `EMAIL_HOST_PASSWORD` ใน `.env.production` เพื่อส่งเมลจริง (ระบบรายงานอัตโนมัติ — ดู [core/services/report_email.py](core/services/report_email.py))

---

## อัปเดตเวอร์ชันใหม่ (re-deploy)

### เคส A — แก้แค่โค้ด + migration (ไม่มี library ใหม่)
1. `git pull` บน NAS (หรืออัปเดตไฟล์ในโฟลเดอร์)
2. Container Manager → Project → **Build** ใหม่ (หรือ restart container `web`)
3. migrate รันอัตโนมัติตอน start อยู่แล้ว — ถ้าต้องการรันเอง: Terminal → `python manage.py migrate`

### เคส B — มี library ใหม่ใน `pyproject.toml`
1. `git pull`
2. Container Manager → Project → **Build** (จะ `poetry install` ใหม่ใน image)
3. up project ใหม่

> หมายเหตุ: ข้อมูลใน `postgres_data_prod` และ `media_data` จะ **ไม่หาย** ตอน rebuild
> (อย่าลบ volume เว้นแต่ตั้งใจล้างข้อมูลทั้งหมด)

---

## Troubleshooting

| อาการ | สาเหตุ / วิธีแก้ |
|---|---|
| เปิดเว็บไม่ได้ | เช็คว่า port 8003 ว่างบน NAS / container `web` รันอยู่ / ดู log ใน Container Manager |
| `DisallowedHost` | IP/hostname ไม่อยู่ใน `ALLOWED_HOSTS` → เพิ่มใน `.env.production` แล้ว rebuild |
| Login แล้ว 403 CSRF | `CSRF_TRUSTED_ORIGINS` ไม่ตรง scheme/port → ต้องเป็น `http://172.29.66.228:8003` |
| web ขึ้นแต่ db error | db ยังไม่พร้อม → web มี `depends_on healthy` อยู่แล้ว ลอง restart project |
| CSS/หน้าตาเพี้ยน | collectstatic ไม่ทำงาน → ดู log entrypoint, หรือรัน `python manage.py collectstatic --no-input` เอง |
