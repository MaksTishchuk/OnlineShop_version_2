from django.db import transaction
from django.shortcuts import render, redirect
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.views.generic import DetailView, View
from .models import Category, Product, Customer, Cart, CartProduct, Order
from .mixins import CartMixin
from .forms import OrderForm, LoginForm, RegistrationForm
from .utils import recalc_cart


class BaseView(CartMixin, View):
    """Вывод товаров на главную страницу"""

    def get(self, request):
        categories = Category.objects.all()
        products = Product.objects.all()
        context = {
            'categories': categories,
            'products': products,
            'cart': self.cart
        }
        return render(request, 'base.html', context)


class ProductDetailView(CartMixin, DetailView):
    """Выводим детальное представление для моделей, указанных в словаре CT_MODEL_MODEL_CLASS.
    В методе Диспатч достаем ловеркейс название контенттайп модели и
    через словарь достаем правильное название модели"""

    model = Product
    context_object_name = 'product'
    template_name = 'product_detail.html'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = self.cart
        return context


class CategoryDetailView(CartMixin, DetailView):
    """Вывод товаров в определенной категории"""
    model = Category
    queryset = Category.objects.all()
    context_object_name = 'category'
    template_name = 'category_detail.html'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart'] = self.cart
        return context


class AddToCartView(CartMixin, View):
    """Добавление товара в корзину"""

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            product_slug = kwargs.get('slug')
            product = Product.objects.get(slug=product_slug)  # получаем продукт
            cart_product, created = CartProduct.objects.get_or_create(
                user=self.cart.owner,
                cart=self.cart,
                product=product
            )
            if created:
                self.cart.products.add(cart_product)
            recalc_cart(self.cart)
            messages.add_message(request, messages.INFO, "Товар успешно добавлен")
            return HttpResponseRedirect('/cart/')
        else:
            messages.add_message(
                request,
                messages.INFO,
                "Для добавления товаров в корзину необходимо авторизоваться!"
            )
            return redirect(request.META.get('HTTP_REFERER'))


class DeleteFromCartView(CartMixin, View):
    """Удаляем товар из корзины"""

    def get(self, request, *args, **kwargs):
        product_slug = kwargs.get('slug')
        product = Product.objects.get(slug=product_slug)  # получаем продукт
        cart_product = CartProduct.objects.get(
            user=self.cart.owner,
            cart=self.cart,
            product=product
        )
        self.cart.products.remove(cart_product)
        cart_product.delete()
        recalc_cart(self.cart)
        messages.add_message(request, messages.INFO, "Товар успешно удален")
        return HttpResponseRedirect('/cart/')


class ChangeQtyView(CartMixin, View):
    """Изменение количества товара в корзине"""

    def post(self, request, *args, **kwargs):
        product_slug = kwargs.get('slug')
        product = Product.objects.get(slug=product_slug)  # получаем продукт
        cart_product = CartProduct.objects.get(
            user=self.cart.owner,
            cart=self.cart,
            product=product
        )
        qty = int(request.POST.get('qty'))
        cart_product.qty = qty
        cart_product.save()
        recalc_cart(self.cart)
        messages.add_message(request, messages.INFO, "Кол-во успешно изменено")
        return HttpResponseRedirect('/cart/')


class CartView(CartMixin, View):
    """Представление корзины"""

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        context = {
            'cart': self.cart,
            'category': categories
        }
        return render(request, 'cart.html', context)


class CheckoutView(CartMixin, View):
    """Представление формы создания заказа"""

    def get(self, request, *args, **kwargs):
        categories = Category.objects.all()
        form = OrderForm(request.POST or None)
        context = {
            'cart': self.cart,
            'category': categories,
            'form': form
        }
        return render(request, 'checkout.html', context)


class MakeOrderView(CartMixin, View):
    """Представление обработки заказа"""

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = OrderForm(request.POST or None)
        customer = Customer.objects.get(user=request.user)
        if form.is_valid():
            new_order = form.save(commit=False)
            new_order.customer = customer
            new_order.first_name = form.cleaned_data['first_name']
            new_order.last_name = form.cleaned_data['last_name']
            new_order.phone = form.cleaned_data['phone']
            new_order.address = form.cleaned_data['address']
            new_order.buying_type = form.cleaned_data['buying_type']
            new_order.order_date = form.cleaned_data['order_date']
            new_order.comment = form.cleaned_data['comment']
            new_order.save()
            self.cart.in_order = True
            self.cart.save()
            new_order.cart = self.cart
            new_order.save()
            customer.orders.add(new_order)
            messages.add_message(
                request,
                messages.INFO,
                'Спасибо за ваш заказ! Менеджер с вами свяжется'
            )
            return HttpResponseRedirect('/')
        return HttpResponseRedirect('/checkout/')


class LoginView(CartView, View):
    """Предаставление для авторизации"""

    def get(self, request, *args, **kwargs):
        """Получение формы"""

        form = LoginForm(request.POST or None)
        categories = Category.objects.all()
        context = {
            'form': form,
            'categories': categories,
            'cart': self.cart
        }
        return render(request, 'login.html', context)

    def post(self, request, *args, **kwargs):
        """Отправка данных"""

        form = LoginForm(request.POST or None)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(username=username, password=password)
            if user:
                login(request, user)
                return HttpResponseRedirect('/')
        return render(request, 'login.html', {'form': form, 'cart': self.cart})


class RegistrationView(CartMixin, View):
    """Представление регистрации"""

    def get(self, request, *args, **kwargs):
        """Получение формы"""

        form = RegistrationForm(request.POST or None)
        categories = Category.objects.all()
        context = {
            'form': form,
            'categories': categories,
            'cart': self.cart
        }
        return render(request, 'registration.html', context)

    def post(self, request, *args, **kwargs):
        """Отправка данных"""

        form = RegistrationForm(request.POST or None)
        if form.is_valid():
            new_user = form.save(commit=False)
            new_user.username = form.cleaned_data['username']
            new_user.email = form.cleaned_data['email']
            new_user.first_name = form.cleaned_data['first_name']
            new_user.last_name = form.cleaned_data['last_name']
            new_user.save()
            new_user.set_password(form.cleaned_data['password'])
            new_user.save()
            Customer.objects.create(
                user=new_user,
                phone=form.cleaned_data['phone'],
                address=form.cleaned_data['address']
            )
            user = authenticate(
                username=new_user.username, password=form.cleaned_data['password']
            )
            login(request, user)
            return HttpResponseRedirect('/')
        categories = Category.objects.all()
        context = {
            'form': form,
            'categories': categories,
            'cart': self.cart
        }
        return render(request, 'registration.html', context)


# class ProfileView(CartMixin, View):
#     """Представление профиля пользователя"""
#
#     def get(self, request, *args, **kwargs):
#         customer = Customer.objects.get(user=request.user)
#         orders = Order.objects.filter(customer=customer).order_by('-created_at')
#         categories = Category.objects.all()
#         return render(
#             request,
#             'profile.html',
#             {'orders': orders, 'cart': self.cart, 'categories': categories}
#         )
