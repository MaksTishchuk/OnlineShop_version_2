from PIL import Image

from django.forms import ModelChoiceField, ModelForm, ValidationError
from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import *


class NotebookAdminForm(ModelForm):
    """Переопределение стандартной инициализации с добавлением нового поведения"""

    def __init__(self, *args, **kwargs):
        """Добавили help_text для поля image"""
        super().__init__(*args, **kwargs)
        self.fields['image'].help_text = mark_safe(
            f'<span style="color:red; font-size:14px;">Изображение будет пропорционально '
            f'изменено, чтобы стороны не превышали размер: ' \
            f'{Product.MAX_RESOLUTION[0]}x{Product.MAX_RESOLUTION[1]}</span>')

    # def clean_image(self):
    #     """Валидация размера изображения и выбрасывание исключения"""
    #     image = self.cleaned_data['image']
    #     img = Image.open(image)
    #     min_width, min_height = Product.MIN_RESOLUTION
    #     max_width, max_height = Product.MAX_RESOLUTION
    #     if image.size() > Product.MAX_IMAGE_SIZE:
    #         raise ValidationError('Размер изображения не должен превышать 3 Мб!')
    #     if img.width < min_width or img.height < min_height:
    #         raise ValidationError('Разрешение изображения меньше минимального!')
    #     if img.width > max_width or img.height > max_height:
    #         raise ValidationError('Разрешение изображения больше максимального!')
    #     return image


class NotebookAdmin(admin.ModelAdmin):
    """Переопределяем выбор категории для ноутбуков"""

    form = NotebookAdminForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            return ModelChoiceField(Category.objects.filter(slug='notebooks'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class SmartphoneAdmin(admin.ModelAdmin):
    """Переопределяем выбор категории для смартфонов"""

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'category':
            return ModelChoiceField(Category.objects.filter(slug='smartphones'))
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Category)
admin.site.register(Notebook, NotebookAdmin)
admin.site.register(Smartphone, SmartphoneAdmin)
admin.site.register(CartProduct)
admin.site.register(Cart)
admin.site.register(Customer)
admin.site.register(Order)
