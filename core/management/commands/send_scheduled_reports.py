"""ส่งรายงาน Excel ทางอีเมลให้ผู้รับที่ "ถึงกำหนด".

ออกแบบให้ตั้งเวลารัน **วันละครั้ง** ด้วย cron (ใน container) หรือ Windows Task
Scheduler — ตัว command จะเลือกผู้รับที่ถึงกำหนดเองตาม ``frequency`` + ``last_sent_at``.

ตัวอย่าง:
    # รันตามกำหนด (ใช้ใน cron)
    python manage.py send_scheduled_reports

    # ส่งทดสอบให้ผู้รับรายเดียว (ไม่สนใจว่าถึงกำหนดหรือยัง)
    python manage.py send_scheduled_reports --receiver <uuid>

    # บังคับส่งทุกคน / ดูว่าจะส่งให้ใครโดยไม่ส่งจริง
    python manage.py send_scheduled_reports --force
    python manage.py send_scheduled_reports --dry-run
"""

from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.models.email_receiver import EmailReceiver
from core.services.report_email import is_due, send_report_to_receiver


class Command(BaseCommand):
    help = "ส่งรายงาน Excel ทางอีเมลให้ผู้รับที่ถึงกำหนด (ตั้งเวลารันวันละครั้ง)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="ส่งทุกผู้รับที่ active โดยไม่สนใจว่าถึงกำหนดหรือยัง",
        )
        parser.add_argument(
            "--receiver",
            dest="receiver_id",
            help="ส่งให้ผู้รับรายเดียวตาม UUID (ใช้ทดสอบ — ข้ามการเช็คกำหนดให้อัตโนมัติ)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="แสดงว่าจะส่งให้ใครบ้าง แต่ไม่ส่งจริง",
        )

    def handle(self, *args, **opts):
        receiver_id = opts.get("receiver_id")
        # ระบุผู้รับตรง ๆ = ตั้งใจทดสอบ -> ข้ามการเช็คกำหนด
        force = opts["force"] or bool(receiver_id)
        dry_run = opts["dry_run"]
        now = timezone.now()
        ref_date = timezone.localtime(now).date()

        if receiver_id:
            qs = EmailReceiver.objects.filter(pk=receiver_id)
            if not qs.exists():
                raise CommandError(f"ไม่พบ EmailReceiver id={receiver_id}")
        else:
            qs = EmailReceiver.objects.filter(is_active=True)

        self.stdout.write(f"ตรวจสอบผู้รับ {qs.count()} ราย (force={force}, dry_run={dry_run}) ...")

        sent = skipped = failed = 0
        for r in qs:
            if not force and not is_due(r, now):
                skipped += 1
                self.stdout.write(
                    f"  - ข้าม {r.email} ({r.get_frequency_display()}) — ยังไม่ถึงกำหนด"
                )
                continue

            if not (r.send_production_report or r.send_inspection_report):
                skipped += 1
                self.stdout.write(
                    self.style.WARNING(f"  - ข้าม {r.email} — ยังไม่ได้เลือกข้อมูลที่จะส่ง")
                )
                continue

            if dry_run:
                sent += 1
                self.stdout.write(f"  [dry-run] จะส่งให้ {r.email} ({r.get_frequency_display()})")
                continue

            try:
                res = send_report_to_receiver(r, ref_date=ref_date)
                sent += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ ส่งให้ {res['email']} — {', '.join(res['attachments'])} "
                        f"({res['date_from']:%d/%m/%Y}–{res['date_to']:%d/%m/%Y})"
                    )
                )
            except Exception as e:  # noqa: BLE001 — สรุปผลแล้วทำต่อรายถัดไป
                failed += 1
                self.stderr.write(self.style.ERROR(f"  ✗ ส่งให้ {r.email} ไม่สำเร็จ: {e}"))

        summary = f"เสร็จสิ้น: ส่ง {sent}, ข้าม {skipped}, ล้มเหลว {failed}"
        self.stdout.write(self.style.SUCCESS(summary) if not failed else self.style.WARNING(summary))
