"""ระบบส่งรายงานทางอีเมลอัตโนมัติ.

ประกอบจาก:
- ``date_range_for_frequency`` : แปลงความถี่ -> ช่วงวันที่ของข้อมูล
- ``is_due``                   : ผู้รับรายนี้ถึงกำหนดส่งวันนี้ไหม (กันส่งซ้ำ)
- ``send_report_to_receiver``  : สร้างไฟล์ Excel ตามที่ตั้งค่า แล้วส่งอีเมล

ไฟล์ Excel ใช้ตัวสร้างชุดเดียวกับหน้า manage-production
(``build_scrap_workbook``) และผลตรวจ inspection machine
(``build_inspection_workbook``) เพื่อให้หน้าตา/กราฟเหมือนกันทุกที่.
"""

from __future__ import annotations

import io
import logging
from datetime import datetime, time, timedelta
from email.utils import formataddr, parseaddr

from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Q
from django.db.models import Prefetch
from django.utils import timezone

from core.models.email_receiver import EmailReceiver
from core.models.inspection.inspection_result import InspectionResult
from core.models.process_defect import ProcessDefect, ProcessDefectScrap, ProductionRecord
from core.services.scrap_export import build_inspection_workbook, build_scrap_workbook

logger = logging.getLogger(__name__)

XLSX_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _shift_display(user, record=None) -> str:
    """กะของรายการ — prefer the explicit ``ProductionRecord.shift`` chosen on
    /record/, fall back to the recorder's profile shift for legacy rows, then '-'."""
    if record is not None and getattr(record, "shift_id", None):
        return record.shift.name
    profile = getattr(user, "profile", None) if user is not None else None
    if profile is None:
        return "-"
    return profile.get_shift_display()


def date_range_for_frequency(frequency, ref_date=None):
    """คืน ``(date_from, date_to)`` (date, inclusive) ของรอบนั้น อิง ``ref_date``.

    - DAILY   : ข้อมูลของ "เมื่อวาน"
    - WEEKLY  : ข้อมูลสัปดาห์ก่อนหน้า (จันทร์ - อาทิตย์)
    - MONTHLY : ข้อมูลของ "เดือนก่อนหน้า"
    """
    ref = ref_date or timezone.localdate()
    F = EmailReceiver.Frequency

    if frequency == F.WEEKLY:
        monday_this_week = ref - timedelta(days=ref.weekday())
        date_from = monday_this_week - timedelta(days=7)
        date_to = monday_this_week - timedelta(days=1)
        return date_from, date_to

    if frequency == F.MONTHLY:
        first_this_month = ref.replace(day=1)
        date_to = first_this_month - timedelta(days=1)        # วันสุดท้ายของเดือนก่อน
        date_from = date_to.replace(day=1)
        return date_from, date_to

    # DAILY
    yesterday = ref - timedelta(days=1)
    return yesterday, yesterday


def is_due(receiver: EmailReceiver, now=None) -> bool:
    """ผู้รับรายนี้ถึงกำหนดส่งวันนี้ไหม (อิงเวลาท้องถิ่น) — กันส่งซ้ำด้วย last_sent_at.

    สมมติว่า command ถูกตั้งเวลารันวันละครั้ง:
    - DAILY   : ส่งทุกวัน
    - WEEKLY  : ส่งเฉพาะวันจันทร์
    - MONTHLY : ส่งเฉพาะวันที่ 1
    """
    now = now or timezone.now()
    today = timezone.localtime(now).date()
    F = EmailReceiver.Frequency

    if receiver.last_sent_at and timezone.localtime(receiver.last_sent_at).date() >= today:
        return False  # ส่งไปแล้ววันนี้

    if receiver.frequency == F.DAILY:
        return True
    if receiver.frequency == F.WEEKLY:
        return today.weekday() == 0
    if receiver.frequency == F.MONTHLY:
        return today.day == 1
    return False


def _production_export_data(date_from, date_to):
    """ประกอบข้อมูล 4-sheet (record / scrap / สรุป Line / สรุป Defect) จาก ProductionRecord."""
    qs = (
        ProductionRecord.objects
        .select_related("line", "item", "shift", "created_by", "created_by__profile")
        .prefetch_related(
            Prefetch(
                "defects",
                queryset=ProcessDefect.objects.select_related("defect_mode").prefetch_related(
                    Prefetch(
                        "details",
                        queryset=ProcessDefectScrap.objects.select_related("component_part"),
                    )
                ),
            )
        )
        .filter(
            Q(production_date__gte=date_from, production_date__lte=date_to)
            | Q(production_date__isnull=True, created_at__date__gte=date_from, created_at__date__lte=date_to)
        )
        .order_by("-created_at")
    )

    record_rows = []
    scrap_rows = []
    line_totals: dict[str, int] = {}
    defect_totals: dict[str, int] = {}

    for pr in qs:
        created = timezone.localtime(pr.created_at) if pr.created_at else None
        created_str = created.strftime("%d/%m/%Y %H:%M") if created else "-"
        prod_date_str = pr.production_date.strftime("%d/%m/%Y") if pr.production_date else "-"
        user = pr.created_by if pr.created_by_id else None
        user_str = user.get_short_name() if user else "-"
        shift_str = _shift_display(user, pr)
        line_name = pr.line.line_name if pr.line_id else "-"

        record_rows.append(
            [
                created_str,
                prod_date_str,
                user_str,
                shift_str,
                line_name,
                pr.lot_number or "-",
                (getattr(pr.item, "sd_code", "") or "-") if pr.item_id else "-",
                (getattr(pr.item, "part_name", "") or "-") if pr.item_id else "-",
                pr.products_quantity,
                pr.total_defect_quantity,
                (pr.defect_rate or 0) / 100.0,  # fraction → rendered as %
            ]
        )
        line_totals[line_name] = line_totals.get(line_name, 0) + pr.total_defect_quantity

        for d in pr.defects.all():
            dm_name = d.defect_mode.name if d.defect_mode_id else "-"
            defect_totals[dm_name] = defect_totals.get(dm_name, 0) + d.quantity
            for s in d.details.all():
                comp = s.component_part
                scrap_rows.append(
                    [
                        created_str,
                        prod_date_str,
                        user_str,
                        shift_str,
                        line_name,
                        pr.lot_number or "-",
                        (getattr(comp, "sd_code", "") or "-") or "-",
                        (getattr(comp, "part_number", "") or "-") or "-",
                        (getattr(comp, "part_name", "") or "-") or "-",
                        s.quantity,
                    ]
                )

    return record_rows, scrap_rows, line_totals, defect_totals


def _inspection_export_data(date_from, date_to):
    """ประกอบข้อมูลผลตรวจ inspection machine จาก InspectionResult."""
    dt_from = timezone.make_aware(datetime.combine(date_from, time.min))
    dt_to = timezone.make_aware(datetime.combine(date_to, time.max))
    qs = (
        InspectionResult.objects
        .select_related("inspectionitem", "inspection_line")
        .filter(created_at__gte=dt_from, created_at__lte=dt_to)
        .order_by("-created_at")
    )

    result_rows = []
    result_totals: dict[str, int] = {}
    for obj in qs:
        created = timezone.localtime(obj.created_at) if obj.created_at else None
        result_rows.append(
            [
                created.strftime("%d/%m/%Y %H:%M") if created else "-",
                getattr(obj.inspectionitem, "sd_code", "") or "-",
                getattr(obj.inspection_line, "line_name", "") or "-",
                obj.qr_work or "-",
                obj.result or "-",
            ]
        )
        key = obj.result or "(ไม่ระบุ)"
        result_totals[key] = result_totals.get(key, 0) + 1

    return result_rows, result_totals


def build_attachments_for(receiver: EmailReceiver, date_from, date_to):
    """คืน list ของ ``(filename, content_bytes)`` ตาม report ที่เปิดใช้งาน. Raises ImportError ถ้าไม่มี openpyxl."""
    attachments: list[tuple[str, bytes]] = []
    ts = f"{date_from:%Y%m%d}-{date_to:%Y%m%d}"

    if receiver.send_production_report:
        rr, sr, lt, dt_ = _production_export_data(date_from, date_to)
        wb = build_scrap_workbook(rr, sr, lt, dt_)
        buf = io.BytesIO()
        wb.save(buf)
        attachments.append((f"ProductionRecords_{ts}.xlsx", buf.getvalue()))

    if receiver.send_inspection_report:
        rr, rt = _inspection_export_data(date_from, date_to)
        wb = build_inspection_workbook(rr, rt)
        buf = io.BytesIO()
        wb.save(buf)
        attachments.append((f"InspectionResults_{ts}.xlsx", buf.getvalue()))

    return attachments


def send_report_to_receiver(receiver: EmailReceiver, ref_date=None, mark_sent=True) -> dict:
    """สร้างไฟล์ Excel ตามที่ตั้งค่า แล้วส่งอีเมลให้ผู้รับ 1 ราย. คืน dict ผลลัพธ์.

    Raises:
        ValueError : ผู้รับไม่ได้เลือกข้อมูลที่จะส่ง
        ImportError: ไม่มี openpyxl
        Exception  : การส่งอีเมลล้มเหลว (fail_silently=False)
    """
    if not (receiver.send_production_report or receiver.send_inspection_report):
        raise ValueError("ผู้รับนี้ยังไม่ได้เลือกข้อมูลที่จะส่ง (production/inspection)")

    date_from, date_to = date_range_for_frequency(receiver.frequency, ref_date)
    attachments = build_attachments_for(receiver, date_from, date_to)

    freq_label = receiver.get_frequency_display()
    subject = f"[TBSMRD] รายงาน{freq_label} {date_from:%d/%m/%Y} - {date_to:%d/%m/%Y}"

    parts = []
    if receiver.send_production_report:
        parts.append("• ข้อมูลการผลิต/ของเสีย (Production & Scrap)")
    if receiver.send_inspection_report:
        parts.append("• ผลตรวจ Inspection Machine")

    body = (
        f"เรียน {receiver.name}\n\n"
        f"ระบบได้แนบรายงาน{freq_label} ช่วงวันที่ {date_from:%d/%m/%Y} ถึง "
        f"{date_to:%d/%m/%Y} มาให้ดังนี้:\n"
        + "\n".join(parts)
        + "\n\nอีเมลฉบับนี้ส่งโดยอัตโนมัติจากระบบ TBSMRD กรุณาอย่าตอบกลับ"
    )

    # ส่งแบบ no-reply: ผู้ส่งเป็นชื่อ/ที่อยู่ no-reply, ตั้ง Reply-To กลับไปที่ no-reply
    # และใส่ Auto-Submitted (RFC 3834) เพื่อบอกว่าเป็นเมลอัตโนมัติ (ลด auto-reply).
    # ผู้รับ (to) ยังเป็นผู้ที่กำหนดไว้ใน EmailReceiver เหมือนเดิม.
    from_name, from_addr = parseaddr(settings.DEFAULT_FROM_EMAIL or "no-reply@tbsmrd.local")
    if not from_name:
        from_name = getattr(settings, "REPORT_FROM_NAME", "") or "no-reply"

    msg = EmailMessage(
        subject=subject,
        body=body,
        from_email=formataddr((from_name, from_addr)),
        to=[receiver.email],
        headers={
            "Reply-To": from_addr,
            "Auto-Submitted": "auto-generated",
        },
    )
    for filename, content in attachments:
        msg.attach(filename, content, XLSX_MIME)

    msg.send(fail_silently=False)

    if mark_sent:
        receiver.last_sent_at = timezone.now()
        receiver.save(update_fields=["last_sent_at", "updated_at"])

    logger.info(
        "Sent report email to %s (attachments=%s, range=%s..%s)",
        receiver.email,
        [a[0] for a in attachments],
        date_from,
        date_to,
    )
    return {
        "email": receiver.email,
        "attachments": [a[0] for a in attachments],
        "date_from": date_from,
        "date_to": date_to,
    }


def run_scheduled_reports(now=None, ref_date=None, dry_run=False) -> dict:
    """ส่งรายงานให้ผู้รับทุกคนที่ "ถึงกำหนด" วันนี้ — เป็นตัวขับเคลื่อนการส่งอัตโนมัติ.

    เรียกโดย management command ``send_scheduled_reports`` ที่ถูกตั้งเวลารันวันละครั้ง
    (cron / Task Scheduler). ทำงานเป็น 2 ขั้น:

    1. คัดเฉพาะผู้รับที่ ``is_active`` และเลือกข้อมูลส่งอย่างน้อย 1 อย่าง
       แล้วกรองด้วย :func:`is_due` (อิง frequency + กันส่งซ้ำด้วย last_sent_at)
    2. ส่งทีละราย **แยก error ออกจากกัน** — ผู้รับรายหนึ่งล้มเหลวจะไม่ทำให้
       ทั้งรอบหยุด รายที่เหลือยังถูกส่งต่อ

    Args:
        now:      เวลาอ้างอิงสำหรับตัดสิน "ถึงกำหนด" (ดีฟอลต์ = ตอนนี้)
        ref_date: วันที่อ้างอิงสำหรับคำนวณช่วงข้อมูล (ดีฟอลต์ = วันนี้)
        dry_run:  ``True`` = แค่ประเมินว่าจะส่งให้ใคร ไม่ส่งจริง/ไม่อัปเดต last_sent_at

    Returns:
        dict สรุปผล: ``due`` (จำนวนที่ถึงกำหนด), ``sent``, ``failed``,
        พร้อมรายละเอียด ``sent_detail`` / ``failed_detail``.
    """
    now = now or timezone.now()
    receivers = (
        EmailReceiver.objects
        .filter(is_active=True)
        .filter(Q(send_production_report=True) | Q(send_inspection_report=True))
        .order_by("name")
    )

    due = [r for r in receivers if is_due(r, now=now)]
    sent_detail: list[dict] = []
    failed_detail: list[dict] = []

    for receiver in due:
        if dry_run:
            sent_detail.append({"email": receiver.email, "dry_run": True})
            continue
        try:
            sent_detail.append(send_report_to_receiver(receiver, ref_date=ref_date))
        except Exception as exc:  # noqa: BLE001 — กันรายเดียวล้มแล้วลามทั้งรอบ
            logger.exception("Failed to send scheduled report to %s", receiver.email)
            failed_detail.append({"email": receiver.email, "error": str(exc)})

    summary = {
        "due": len(due),
        "sent": len([d for d in sent_detail if not d.get("dry_run")]),
        "failed": len(failed_detail),
        "dry_run": dry_run,
        "sent_detail": sent_detail,
        "failed_detail": failed_detail,
    }
    logger.info(
        "Scheduled reports run: due=%s sent=%s failed=%s dry_run=%s",
        summary["due"], summary["sent"], summary["failed"], dry_run,
    )
    return summary
