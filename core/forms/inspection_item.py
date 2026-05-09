from django import forms
from core.models.inspection.inspection_item import InspectionItem


class InspectionItemForm(forms.ModelForm):

    class Meta:
        model = InspectionItem
        fields = [
            "name",
            "bill_of_material_item_master",
            "class_name_bom",
            "inspection_model",
            "is_exist",
        ]

        labels = {
            "name": "Name",
            "bill_of_material_item_master": "BOM Item Master",
            "class_name_bom": "Class Name BOM",
            "inspection_model": "Inspection Model",
            "is_exist": "Is Exist",
        }

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500",
                "placeholder": "Enter inspection name"
            }),

            "bill_of_material_item_master": forms.Select(attrs={
                "class": "mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            }),

            "class_name_bom": forms.TextInput(attrs={
                "class": "mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2 focus:outline-none focus:ring-2 focus:ring-red-500",
                "placeholder": "Enter class name BOM"
            }),

            "inspection_model": forms.Select(attrs={
                "class": "mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2"
            }),

            "is_exist": forms.Select(
                choices=[
                    (True, "True"),
                    (False, "False"),
                ],
                attrs={
                    "class": "mt-1 w-full rounded-md border border-slate-300 bg-white px-3 py-2"
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data.get("name")
        if not name:
            raise forms.ValidationError("กรุณากรอก Name")
        return name