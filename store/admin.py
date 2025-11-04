from django.contrib import admin
from .models import Customer, Product, Order, ItemDetail, Supplier, Category, Payment, CreditPayment, UPIPayment, BankPayment, Cart, CartItem, Invoice, Review,PhoneNumber

# Registering models with list display
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email', 'house_number', 'state', 'city','password')

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'price', 'stock', 'category', 'supplier', 'customer')

@admin.register(ItemDetail)
class ItemDetailAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'order', 'quantity', 'price_per_item', 'total_price')

@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'contact', 'address')

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user')

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'cart', 'product', 'quantity')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_id', 'invoice_date', 'payment')

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'product', 'description', 'rating')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'customer', 'order_date', 'status', 'total_amount')

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'payment_date')

@admin.register(CreditPayment)
class CreditPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'card_no', 'holder_name', 'expiry_date')

@admin.register(UPIPayment)
class UPIPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'wallet_id', 'email', 'wallet_provider')

@admin.register(BankPayment)
class BankPaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'payment', 'bank_acc_no', 'bank_name')

@admin.register(PhoneNumber)
class PhoneNumberAdmin(admin.ModelAdmin):
    list_display=('id','customer','number')