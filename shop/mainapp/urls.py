from django.urls import path
from .views import (
    BaseView,
    ProductDetailView,
    CategoryDetailView,
    CartView,
    AddToCartView,
    DeleteFromCartView,
    ChangeQtyView,
    CheckoutView,
    MakeOrderView,
)

urlpatterns = [
    path('', BaseView.as_view(), name='base'),
    path('products/<slug:slug>/', ProductDetailView.as_view(), name='product_detail'),
    path('category/<str:slug>/', CategoryDetailView.as_view(), name='category_detail'),
    path('cart/', CartView.as_view(), name='cart'),
    path('add-to-cart/<slug:slug>/', AddToCartView.as_view(), name='add_to_cart'),
    path('delete-from-cart/<slug:slug>/', DeleteFromCartView.as_view(), name='delete_from_cart'),
    path('change-qty/<slug:slug>/', ChangeQtyView.as_view(), name='change_qty'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('make-order', MakeOrderView.as_view(), name='make_order')
]
