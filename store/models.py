from django.db import models

# Create your models here.
from django.db import models

class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    house_number = models.CharField(max_length=50,unique=True)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    password = models.CharField(max_length=100)

    def __str__(self):
        return self.email
from django.db import models

class Product(models.Model):
    id = models.AutoField(primary_key=True)  # Default primary key
    name = models.CharField(max_length=100,unique=True)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    supplier = models.ForeignKey('Supplier', on_delete=models.CASCADE, related_name='products', null=True, blank=True, default=1)
    category = models.ForeignKey('Category', on_delete=models.CASCADE, related_name='products', null=True, blank=True, default=1)
    def __str__(self):
        return self.name


        
class Order(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='orders')
    order_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[('Pending', 'Pending'), ('Shipped', 'Shipped'), ('Delivered', 'Delivered')],
        default='Pending'
    )
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # Make it nullable

    def __str__(self):
        return f"Order {self.id} by {self.customer.name}"





class ItemDetail(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='item_details')
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    price_per_item = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Item {self.product.name} in Order {self.order.id}"

    def save(self, *args, **kwargs):
        # Automatically calculate total_price when saving ItemDetail
        self.total_price = self.price_per_item * self.quantity
        super().save(*args, **kwargs)





class Supplier(models.Model):
    name = models.CharField(max_length=100,unique=True)
    contact = models.CharField(max_length=15)
    address = models.TextField()

    def __str__(self):
        return self.name



class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
     


class Payment(models.Model):
    order = models.ForeignKey('Order', on_delete=models.CASCADE, related_name='payments')
    payment_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.id} for Order {self.order.id}"

class CreditPayment(models.Model):
    payment = models.OneToOneField('Payment', on_delete=models.CASCADE, related_name='credit')
    card_no = models.CharField(max_length=16)
    holder_name = models.CharField(max_length=100)
    expiry_date = models.CharField(max_length=5)

    def __str__(self):
        return f"Credit Payment {self.payment.id}"

class UPIPayment(models.Model):
    payment = models.OneToOneField('Payment', on_delete=models.CASCADE, related_name='upi')
    wallet_id = models.CharField(max_length=100)
    email = models.EmailField()
    wallet_provider = models.CharField(max_length=100)

    def __str__(self):
        return f"UPI Payment {self.payment.id}"

class BankPayment(models.Model):
    payment = models.OneToOneField('Payment', on_delete=models.CASCADE, related_name='bank')
    bank_acc_no = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=100)

    def __str__(self):
        return f"Bank Payment {self.payment.id}"


from django.db import models
from django.contrib.auth.models import User

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cart')
    
    def __str__(self):
        return f"Cart of {self.user.username}"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    def __str__(self):
        return f"{self.quantity} of {self.product.name}"


from django.db import models
from .models import Payment

class Invoice(models.Model):
    invoice_id = models.AutoField(primary_key=True)
    invoice_date = models.DateTimeField(auto_now_add=True)
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE)

    def __str__(self):
        return f"Invoice {self.invoice_id} for Payment {self.payment.id}"


from django.db import models
from django.contrib.auth.models import User  # Assuming you use the default User model

class Review(models.Model):
    customer = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    description = models.TextField()
    rating = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.customer.username} - {self.product.name}"


class PhoneNumber(models.Model):
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='phone_numbers')
    number = models.CharField(max_length=15)

    def __str__(self):
        return self.number

