# tbapp สร้างสภาพแวดล้อมสำหรับพัฒนาระบบ
# Django Start project

ด้วยคำสั่ง
```
Monthon@172.29.66.228
docker compose exec web bash
poetry run python manage.py runserver 0.0.0.0:8000
poetry run python manage.py tailwind start
```

## Run ในNASS หากมีการเปลี่ยนแปลงแล้วค่าไม่เปลี่ยนตาม
```
ssh Monthon@172.29.66.228
cd /volume1/Inhouseapp/tbsmproduction/deploy
sudo docker compose -p production_report -f docker-compose.yml build web
sudo docker compose -p production_report -f docker-compose.yml up -d
```

## กรณีมีการเปลี่ยนแปลง
### เคส A — แก้แค่โค้ด + migration (ไม่มี library ใหม่):
```
cd /volume1/Inhouseapp/tbsmproduction
git pull
sudo docker exec -it production_report-web-1 poetry run python manage.py migrate
sudo docker restart production_report-web-1   # ถ้าจำเป็น
```

### เคส B — มี library ใหม่ใน pyproject.toml:
```
cd /volume1/Inhouseapp/tbsmproduction
git pull
sudo docker compose build web      # rebuild เพื่อ poetry install ใหม่
sudo docker compose up -d          # สร้าง container ใหม่จาก image ที่ build
sudo docker exec -it production_report-web-1 poetry run python manage.py migrate
```