from django.views.generic import TemplateView

class ServicesView(TemplateView):
    template_name = 'services.html'  # ชื่อไฟล์ HTML ที่คุณจะใช้