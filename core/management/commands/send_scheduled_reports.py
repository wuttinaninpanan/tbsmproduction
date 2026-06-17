"""Management command: ส่งรายงานอีเมลอัตโนมัติให้ผู้รับที่ถึงกำหนดวันนี้.

ตั้งเวลารัน **วันละครั้ง** ด้วย OS scheduler (cron / Windows Task Scheduler), เช่น::

    # รันทุกวันตอน 07:00
    0 7 * * *  python manage.py send_scheduled_reports

ตัวเลือก:
    --dry-run            ประเมินว่าจะส่งให้ใครบ้าง แต่ไม่ส่งจริง/ไม่อัปเดต last_sent_at
    --ref-date YYYY-MM-DD  วันที่อ้างอิงสำหรับคำนวณช่วงข้อมูล (ใช้ทดสอบย้อนหลัง)

ตรรกะการ "ถึงกำหนด" + กันส่งซ้ำอยู่ใน ``core.services.report_email``.
"""

from __future__ import annotations

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from core.services.report_email import run_scheduled_reports


class Command(BaseCommand):
    help = "ส่งรายงานอีเมลอัตโนมัติให้ผู้รับที่ถึงกำหนดวันนี้ (ตั้งเวลารันวันละครั้ง)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="แสดงว่าจะส่งให้ใครบ้าง แต่ไม่ส่งจริงและไม่อัปเดต last_sent_at",
        )
        parser.add_argument(
            "--ref-date",
            dest="ref_date",
            default=None,
            help="วันที่อ้างอิงรูปแบบ YYYY-MM-DD สำหรับคำนวณช่วงข้อมูล (ดีฟอลต์ = วันนี้)",
        )

    def handle(self, *args, **options):
        ref_date = None
        raw = options.get("ref_date")
        if raw:
            try:
                ref_date = datetime.strptime(raw, "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError(f"--ref-date ต้องเป็นรูปแบบ YYYY-MM-DD: {exc}") from exc

        dry_run = options.get("dry_run", False)
        summary = run_scheduled_reports(ref_date=ref_date, dry_run=dry_run)

        prefix = "[DRY-RUN] " if dry_run else ""
        self.stdout.write(
            f"{prefix}ถึงกำหนด {summary['due']} ราย "
            f"| ส่งสำเร็จ {summary['sent']} | ล้มเหลว {summary['failed']}"
        )

        for item in summary["sent_detail"]:
            if item.get("dry_run"):
                self.stdout.write(self.style.WARNING(f"  • (dry-run) {item['email']}"))
            else:
                files = ", ".join(item.get("attachments", [])) or "-"
                self.stdout.write(self.style.SUCCESS(f"  ✓ {item['email']} ({files})"))

        for item in summary["failed_detail"]:
            self.stderr.write(self.style.ERROR(f"  ✗ {item['email']}: {item['error']}"))

        if summary["failed"]:
            # exit code != 0 เพื่อให้ scheduler/monitoring จับได้ว่ามีรายที่ส่งไม่สำเร็จ
            raise CommandError(f"มี {summary['failed']} รายที่ส่งไม่สำเร็จ")
