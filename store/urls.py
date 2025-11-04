from django.urls import path
from . import views
from .views import list_products_view, order_product_view,remove_from_cart_view,view_cart_view,add_to_cart_view,product_payment_view,cart_payment_view, order_cart_view, user_payments_view,view_invoice,user_orders_view,review_page



urlpatterns = [
    path('', views.login_view, name='login'),
    path('signup/', views.signup_view, name='signup'),
    path('products/', list_products_view, name='list_products'),
    path('order/<int:product_id>/', order_product_view, name='order_product'),
    path('payment/<int:order_id>/',product_payment_view, name='product_payment_view'),
    path('add_to_cart/<int:product_id>/', add_to_cart_view, name='add_to_cart'), 
    path('cart/', view_cart_view, name='view_cart'), 
    path('remove_from_cart/<int:item_id>/', remove_from_cart_view, name='remove_from_cart'),
    path('order_cart/', order_cart_view, name='order_cart'),
    path('cart_payment/', cart_payment_view, name='cart_payment_view'),
    path('payments/', user_payments_view, name='user_payments_view'),
    path('invoice/<int:invoice_id>/', view_invoice, name='view_invoice'),
    path('orders/', user_orders_view, name='user_orders_view'),
    path('reviews/<int:product_id>/', review_page, name='review_page'),
    path('order_status/', views.orders_by_status_view, name='orders_by_status'), # Updated URL
]
