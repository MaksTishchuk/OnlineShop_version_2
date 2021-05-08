import sys

from PIL import Image

from django.db import models
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.urls import reverse
from django.utils import timezone
from io import BytesIO

User = get_user_model()


def get_product_url(obj, view_name):
    ct_model = obj.__class__._meta.model_name
    return reverse(view_name, kwargs={'ct_model': ct_model, 'slug': obj.slug})


def get_models_for_count(*model_names):
    return [models.Count(model_name) for model_name in model_names]


class MinResolutionErrorException(Exception):
    """Исключение, если изображение меньше заданных параметров"""
    pass


class MaxResolutionErrorException(Exception):
    """Исключение, если изображение больше заданных параметров"""
    pass


class LatestProductsManager:
    """Получение товаров для главной страницы"""

    @staticmethod
    def get_products_for_main_page(*args, **kwargs):
        """Получаем последние 5 товаров моделей, которые были переданы в args.
        В kwargs можно передать имя модели, предпочитаемой для сортировки в начало,
        с помощью ключевого аргумента with_respect_to"""

        products = []
        with_respect_to = None
        ct_models = ContentType.objects.filter(model__in=args)
        for ct_model in ct_models:
            model_products = ct_model.model_class()._base_manager.all().order_by('-id')[:5]
            products.extend(model_products)
        if kwargs.get('with_respect_to') in args:
            with_respect_to = kwargs.get('with_respect_to')
        if with_respect_to:
            ct_model = ContentType.objects.filter(model=with_respect_to)
            if ct_model.exists():
                return sorted(
                    products,
                    key=lambda x: x.__class__._meta.model_name.startswith(with_respect_to),
                    reverse=True
                )

        return products


class LatestProducts:
    """Модель со своим менеджером"""
    objects = LatestProductsManager


class CategoryManager(models.Manager):
    """Менеджер для вывода категорий в сайдбар"""

    CATEGORY_NAME_COUNT_NAME = {
        'Ноутбуки': 'notebook__count',
        'Смартфоны': 'smartphone__count'
    }

    def get_queryset(self):
        return super().get_queryset()

    def get_categories_for_left_sidebar(self):
        """Получение списка категорий, юрл, количество товаров в категории для вывода в сайдбар"""
        models = get_models_for_count('notebook', 'smartphone')
        qs = list(self.get_queryset().annotate(*models))
        data = [
            dict(
                name=category.name,
                url=category.get_absolute_url(),
                count=getattr(category,
                              self.CATEGORY_NAME_COUNT_NAME[category.name])
            ) for category in qs
        ]
        return data


class Category(models.Model):
    """Модель категорий"""

    name = models.CharField(max_length=255, verbose_name='Имя категории')
    slug = models.SlugField(unique=True)
    objects = CategoryManager()

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('category_detail', kwargs={'slug': self.slug})


class Product(models.Model):
    """Каркас товара - абстрактная модель"""

    MAX_RESOLUTION = (512, 512)
    MAX_IMAGE_SIZE = 3145728

    class Meta:
        abstract = True

    category = models.ForeignKey(Category, verbose_name='Категория', on_delete=models.CASCADE)
    title = models.CharField(max_length=255, verbose_name='Наименование')
    slug = models.SlugField(unique=True)
    image = models.ImageField(verbose_name='Изображение')
    description = models.TextField(verbose_name='Описание', null=True)
    price = models.DecimalField(max_digits=9, decimal_places=2, verbose_name='Цена')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """ В метод добавили приведение изображения к нужному размеру, которое не превышает заданного максимального"""
        image = self.image
        img = Image.open(image)
        new_img = img.convert('RGB')
        new_img.thumbnail([*self.MAX_RESOLUTION], Image.ANTIALIAS)
        filestream = BytesIO()
        new_img.save(filestream, 'JPEG', quality=90)
        filestream.seek(0)
        self.image = InMemoryUploadedFile(
            filestream, 'ImageField',
            self.image.name,
            'jpeg/image',
            sys.getsizeof(filestream),
            None
        )
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return get_product_url(self, 'product_detail')

    def get_model_name(self):
        """Получаем имя модели товара"""
        return self.__class__.__name__.lower()


class Notebook(Product):
    """Модель для товаров ноутбуков"""

    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display_type = models.CharField(max_length=255, verbose_name="Тип дисплея")
    processor_freq = models.CharField(max_length=255, verbose_name='Частота процессора')
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    video = models.CharField(max_length=255, verbose_name='Видеокарта')
    time_without_charge = models.CharField(
        max_length=255, verbose_name='Время работы от аккумулятора'
    )

    def __str__(self):
        return f'{self.category.name}: {self.title}'


class Smartphone(Product):
    """Модель для товаров смартфонов"""

    diagonal = models.CharField(max_length=255, verbose_name='Диагональ')
    display_type = models.CharField(max_length=255, verbose_name="Тип дисплея")
    resolution = models.CharField(max_length=255, verbose_name="Разрешение экрана")
    accum_volume = models.CharField(max_length=255, verbose_name="Емкость аккумулятора")
    ram = models.CharField(max_length=255, verbose_name='Оперативная память')
    sd = models.BooleanField(default=True, verbose_name='Наличие SD карты')
    sd_volume_max = models.CharField(
        max_length=255, null=True, blank=True, verbose_name='Максимальный объем micro sd карты'
    )
    main_cam_mp = models.CharField(max_length=255, verbose_name='Основная камера')
    frontal_cam_mp = models.CharField(max_length=255, verbose_name='Фронтальная камера')

    def __str__(self):
        return f'{self.category.name}: {self.title}'


class CartProduct(models.Model):
    """Товар из корзины"""

    user = models.ForeignKey('Customer', verbose_name='Покупатель', on_delete=models.CASCADE)
    cart = models.ForeignKey(
        'Cart', verbose_name='Корзина', on_delete=models.CASCADE, related_name='related_products'
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    qty = models.PositiveSmallIntegerField(default=1)  # Количество товара
    final_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        blank=True,
        verbose_name='Финальная цена')

    def __str__(self):
        return f'Продукт: {self.content_object.title} (для корзины)'

    def save(self, *args, **kwargs):
        self.final_price = self.qty * self.content_object.price
        super().save(*args, **kwargs)


class Cart(models.Model):
    """Модель корзины"""

    owner = models.ForeignKey(
        'Customer',
        null=True,
        verbose_name='Владелец',
        on_delete=models.CASCADE
    )
    products = models.ManyToManyField(CartProduct, blank=True, related_name='related_cart')
    total_products = models.PositiveIntegerField(default=0)
    final_price = models.DecimalField(
        max_digits=9,
        decimal_places=2,
        default=0,
        verbose_name='Финальная цена'
    )
    in_order = models.BooleanField(default=False)
    for_anonymous_user = models.BooleanField(default=False)

    def __str__(self):
        return str(self.id)


class Customer(models.Model):
    """Модель пользователя"""

    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE)
    phone = models.CharField(max_length=20, verbose_name='Номер телефона', null=True, blank=True)
    address = models.CharField(max_length=255, verbose_name='Адрес', null=True, blank=True)
    orders = models.ManyToManyField(
        'Order',
        verbose_name='Заказы покупателя',
        related_name='related_customer'
    )

    def __str__(self):
        return f'Покупатель: {self.user} {self.user.last_name}'


class Order(models.Model):
    """Модель заказа"""

    STATUS_NEW = 'new'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_READY = 'is_ready'
    STATUS_COMPLETED = 'completed'

    BUYING_TYPE_SELF = 'self'
    BUYING_TYPE_DELIVERY = 'delivery'

    STATUS_CHOICES = (
        (STATUS_NEW, 'Новый заказ'),
        (STATUS_IN_PROGRESS, 'Заказ в обработке'),
        (STATUS_READY, 'Заказ готов'),
        (STATUS_COMPLETED, 'Заказ выполнен')
    )

    BUYING_TYPE_CHOICES = (
        (BUYING_TYPE_SELF, 'Самовывоз'),
        (BUYING_TYPE_DELIVERY, 'Доставка')
    )

    customer = models.ForeignKey(
        Customer,
        verbose_name='Покупатель',
        related_name='related_orders',
        on_delete=models.CASCADE
    )
    first_name = models.CharField(max_length=255, verbose_name='Имя')
    last_name = models.CharField(max_length=255, verbose_name='Фамилия')
    phone = models.CharField(max_length=20, verbose_name='Номер телефона')
    cart = models.ForeignKey(
        Cart,
        verbose_name='Корзина',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )
    address = models.CharField(max_length=1024, verbose_name='Адрес', null=True, blank=True)
    status = models.CharField(
        max_length=100,
        verbose_name='Статус заказ',
        choices=STATUS_CHOICES,
        default=STATUS_NEW
    )
    buying_type = models.CharField(
        max_length=100,
        verbose_name='Тип заказа',
        choices=BUYING_TYPE_CHOICES,
        default=BUYING_TYPE_SELF
    )
    comment = models.TextField(verbose_name='Комментарий к заказу', null=True, blank=True)
    created_at = models.DateTimeField(auto_now=True, verbose_name='Дата создания заказа')
    order_date = models.DateField(verbose_name='Дата получения заказа', default=timezone.now)

    def __str__(self):
        return str(self.id)
