from django.contrib.auth import authenticate, login
from django.http import HttpResponse
from django.shortcuts import render, redirect


def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        # Authenticate user using email as the username
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            # Redirect to the product list page
            return redirect('list_products')  # Replace 'list_products' with the actual URL name
        else:
            return HttpResponse("Invalid login credentials. Please try again.")
    return render(request, 'login.html')
from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.contrib.auth.models import User
from .models import Customer, PhoneNumber

def signup_view(request):
    if request.method == 'POST':
        name = request.POST['name']
        email = request.POST['email']
        phones = request.POST.getlist('phone')
        house_number = request.POST['house_number']
        state = request.POST['state']
        city = request.POST['city']
        password = request.POST['password']

        # Check if email already exists
        if User.objects.filter(username=email).exists():
            return HttpResponse("Email already exists. Please log in.")
        else:
            # Create the user
            user = User.objects.create_user(username=email, email=email, password=password)

            # Create the customer entry
            customer = Customer.objects.create(
                name=name,
                email=email,
                house_number=house_number,
                state=state,
                city=city
            )

            # Create phone numbers for the customer
            for phone in phones:
                PhoneNumber.objects.create(customer=customer, number=phone)

            return redirect('login')

    return render(request, 'signup.html')



from .models import Product, Customer, Order
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse

from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Category, Supplier
from django.db import connection
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from .models import Category, Supplier

@login_required
def list_products_view(request):
    order_by = request.GET.get('order_by', 'asc')
    category_filter = request.GET.get('category', '')
    supplier_filter = request.GET.get('supplier', '')
    min_price = request.GET.get('min_price', 0)
    max_price = request.GET.get('max_price', 1000000)
    search_query = request.GET.get('search', '')  # Ensure the search query parameter is correctly named

    # Fetch all categories and suppliers for the filter dropdown
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()

    # Base query for fetching products
    query = """
    SELECT p.id, p.name, p.description, p.price, p.stock, c.name AS category_name, 
           s.name AS supplier_name, s.contact AS supplier_contact
    FROM store_product p
    LEFT JOIN store_category c ON p.category_id = c.id
    LEFT JOIN store_supplier s ON p.supplier_id = s.id
    WHERE p.price BETWEEN %s AND %s
    """
    params = [min_price, max_price]

    # Apply search query if provided
    if search_query:
        query += " AND p.name LIKE %s"
        params.append(f"%{search_query}%")

    # Apply category filter if selected
    if category_filter:
        query += " AND c.name = %s"
        params.append(category_filter)

    # Apply supplier filter if selected
    if supplier_filter:
        query += " AND s.name = %s"
        params.append(supplier_filter)

    # Apply sorting
    if order_by == 'desc':
        query += " ORDER BY p.price DESC"
    else:
        query += " ORDER BY p.price ASC"

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        products = cursor.fetchall()

    product_details = [{
        'id': row[0],
        'name': row[1],
        'description': row[2],
        'price': row[3],
        'stock': row[4],
        'category_name': row[5],
        'supplier_name': row[6],
        'supplier_contact': row[7],
    } for row in products]

    return render(request, 'list_products.html', {
        'products': product_details,
        'categories': categories,
        'suppliers': suppliers,
        'order_by': order_by,
        'category_filter': category_filter,
        'supplier_filter': supplier_filter,
        'min_price': min_price,
        'max_price': max_price,
        'search_query': search_query
    })





from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Product, Review

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import Product, Review

@login_required
def review_page(request, product_id=None):
    products = Product.objects.all()
    selected_product_id = product_id or request.POST.get('product') or request.GET.get('product')
    reviews = Review.objects.filter(product_id=selected_product_id) if selected_product_id else None

    if request.method == 'POST' and 'description' in request.POST and 'rating' in request.POST:
        description = request.POST.get('description')
        rating = request.POST.get('rating')
        product = Product.objects.get(id=selected_product_id)
        Review.objects.create(
            customer=request.user,
            product=product,
            description=description,
            rating=rating
        )
        # Directly render the reviews page with updated reviews
        reviews = Review.objects.filter(product_id=selected_product_id)
        return render(request, 'review_page.html', {'products': products, 'reviews': reviews, 'selected_product_id': selected_product_id})

    return render(request, 'review_page.html', {'products': products, 'reviews': reviews, 'selected_product_id': selected_product_id})




from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import Order, Payment, CreditPayment, UPIPayment, BankPayment, Invoice

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Order, Payment, CreditPayment, UPIPayment, BankPayment, Invoice
from django.db import IntegrityError

@login_required
def product_payment_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    
    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        payment = Payment.objects.create(order=order)
        
        try:
            if payment_method == 'credit':
                CreditPayment.objects.create(
                    payment=payment,
                    card_no=request.POST['card_no'],
                    holder_name=request.POST['holder_name'],
                    expiry_date=request.POST['expiry_date']
                )
            elif payment_method == 'upi':
                UPIPayment.objects.create(
                    payment=payment,
                    wallet_id=request.POST['wallet_id'],
                    email=request.POST['email'],
                    wallet_provider=request.POST['wallet_provider']
                )
            elif payment_method == 'bank':
                BankPayment.objects.create(
                    payment=payment,
                    bank_acc_no=request.POST['bank_acc_no'],
                    bank_name=request.POST['bank_name']
                )

            # Update order status to 'Shipped'
            order.status = 'Shipped'
            order.save()

            # Generate invoice
            invoice = Invoice.objects.create(payment=payment)

            return redirect('view_invoice', invoice_id=invoice.invoice_id)

        except IntegrityError as e:
            return HttpResponse(f"An error occurred: {e}")

    return render(request, 'payment_form.html', {'order': order})




from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Product, Customer
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Product, Customer, Order, ItemDetail

@login_required
def order_product_view(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        try:
            customer = Customer.objects.get(email=request.user.username)
        except Customer.DoesNotExist:
            return HttpResponse("Customer not found.", status=404)

        try:
            quantity = int(request.POST['quantity'])
            if quantity <= 0:
                return HttpResponse("Invalid quantity.", status=400)
        except ValueError:
            return HttpResponse("Quantity must be a number.", status=400)

        if product.stock >= quantity:
            total_amount = product.price * quantity

            from django.db import transaction
            with transaction.atomic():
                order = Order.objects.create(
                    customer=customer,
                    total_amount=total_amount,
                    status='Pending'
                )
                product.stock -= quantity
                product.save()

                ItemDetail.objects.create(
                    order=order,
                    product=product,
                    quantity=quantity,
                    price_per_item=product.price,
                    total_price=total_amount
                )

            return redirect('product_payment_view', order_id=order.id)
        else:
            return HttpResponse(f"Insufficient stock for {product.name}. Only {product.stock} left.", status=400)

    return HttpResponse("Invalid request.", status=405)





from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import Product, Cart, CartItem

@login_required
def add_to_cart_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not created:
        cart_item.quantity += int(request.POST['quantity'])
    else:
        cart_item.quantity = int(request.POST['quantity'])
    cart_item.save()
    
    return redirect('view_cart')

@login_required
def view_cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    total_cost = sum(item.product.price * item.quantity for item in cart.items.all())
    return render(request, 'view_cart.html', {'cart': cart, 'total_cost': total_cost})


@login_required
def remove_from_cart_view(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('view_cart')





from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Product, Customer, Cart, CartItem, Order, ItemDetail, Payment, CreditPayment, UPIPayment, BankPayment
from decimal import Decimal

@login_required
def order_cart_view(request):
    cart = get_object_or_404(Cart, user=request.user)
    try:
        customer = Customer.objects.get(email=request.user.username)
    except Customer.DoesNotExist:
        return HttpResponse("Customer not found.")

    if not cart.items.exists():
        return HttpResponse("Your cart is empty.")

    total_amount = sum(item.product.price * item.quantity for item in cart.items.all())
    request.session['total_amount'] = str(total_amount)

    # Create the order for each cart item
    order = Order.objects.create(
        customer=customer,
        total_amount=total_amount,
        status='Pending'
    )

    for item in cart.items.all():
        ItemDetail.objects.create(
            order=order,
            product=item.product,
            quantity=item.quantity,
            price_per_item=item.product.price,
            total_price=item.product.price * item.quantity
        )
        item.product.stock -= item.quantity
        item.product.save()

    # Clear the cart
    cart.items.all().delete()

    return redirect('cart_payment_view')

from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Customer, Order, Payment, CreditPayment, UPIPayment, BankPayment, Invoice, ItemDetail
from decimal import Decimal
from django.db import IntegrityError
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse
from .models import Customer, Order, Payment, CreditPayment, UPIPayment, BankPayment, Invoice
from decimal import Decimal
from django.db import IntegrityError

@login_required
def cart_payment_view(request):
    total_amount = request.session.get('total_amount')

    if not total_amount:
        return HttpResponse("Invalid session data. Please start the order process again.")

    try:
        customer = Customer.objects.get(email=request.user.username)
    except Customer.DoesNotExist:
        return HttpResponse("Customer not found.")

    order = Order.objects.filter(customer=customer, status='Pending').latest('order_date')

    if request.method == 'POST':
        payment_method = request.POST.get('payment_method')
        payment = Payment.objects.create(order=order)

        try:
            if payment_method == 'credit':
                CreditPayment.objects.create(
                    payment=payment,
                    card_no=request.POST['card_no'],
                    holder_name=request.POST['holder_name'],
                    expiry_date=request.POST['expiry_date']
                )
            elif payment_method == 'upi':
                UPIPayment.objects.create(
                    payment=payment,
                    wallet_id=request.POST['wallet_id'],
                    email=request.POST['email'],
                    wallet_provider=request.POST['wallet_provider']
                )
            elif payment_method == 'bank':
                BankPayment.objects.create(
                    payment=payment,
                    bank_acc_no=request.POST['bank_acc_no'],
                    bank_name=request.POST['bank_name']
                )

            # Update order status to 'Shipped'
            order.status = 'Shipped'
            order.save()

            # Generate invoice
            invoice = Invoice.objects.create(payment=payment)

            return redirect('view_invoice', invoice_id=invoice.invoice_id)

        except IntegrityError as e:
            return HttpResponse(f"An error occurred: {e}")

    return render(request, 'payment_form.html', {'total_amount': total_amount})
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.http import HttpResponse
from .models import Customer

@login_required
def user_payments_view(request):
    user_email = request.user.username

    # Combining queries using UNION without any JOIN
    query = f"""
    SELECT p.id AS payment_id, p.payment_date, o.id AS order_id, o.total_amount,
           cp.card_no AS payment_detail, 'Credit Card' AS payment_type
    FROM store_payment p, store_order o, store_customer c, store_creditpayment cp
    WHERE p.order_id = o.id AND o.customer_id = c.id AND p.id = cp.payment_id
    AND c.email = %s

    UNION

    SELECT p.id AS payment_id, p.payment_date, o.id AS order_id, o.total_amount,
           up.wallet_id AS payment_detail, 'UPI' AS payment_type
    FROM store_payment p, store_order o, store_customer c, store_upipayment up
    WHERE p.order_id = o.id AND o.customer_id = c.id AND p.id = up.payment_id
    AND c.email = %s

    UNION

    SELECT p.id AS payment_id, p.payment_date, o.id AS order_id, o.total_amount,
           bp.bank_acc_no AS payment_detail, 'Bank Transfer' AS payment_type
    FROM store_payment p, store_order o, store_customer c, store_bankpayment bp
    WHERE p.order_id = o.id AND o.customer_id = c.id AND p.id = bp.payment_id
    AND c.email = %s

    ORDER BY payment_date DESC;
    """

    total_spent_query = """
    SELECT SUM(o.total_amount)
    FROM store_payment p, store_order o, store_customer c
    WHERE p.order_id = o.id AND o.customer_id = c.id
    AND c.email = %s;
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [user_email, user_email, user_email])
        payments = cursor.fetchall()

        cursor.execute(total_spent_query, [user_email])
        total_spent = cursor.fetchone()[0] or 0

    payment_details = [{
        'payment_id': row[0],
        'payment_date': row[1],
        'order_id': row[2],
        'total_amount': row[3],
        'payment_detail': row[4],
        'payment_type': row[5],
    } for row in payments]

    return render(request, 'user_payments.html', {'payment_details': payment_details, 'total_spent': total_spent})

@login_required
def view_invoice(request, invoice_id):
    invoice_query = """
    SELECT i.invoice_id, i.invoice_date, p.id AS payment_id, o.id AS order_id, o.total_amount, 
           c.name AS customer_name, c.email AS customer_email, c.house_number || ', ' || c.city || ', ' || c.state AS customer_address
    FROM store_invoice i
    LEFT JOIN store_payment p ON i.payment_id = p.id
    LEFT JOIN store_order o ON p.order_id = o.id
    LEFT JOIN store_customer c ON o.customer_id = c.id
    WHERE i.invoice_id = %s;
    """

    items_query = """
    SELECT id.product_id, pr.name, id.quantity, id.price_per_item, id.total_price
    FROM store_itemdetail id
    LEFT JOIN store_product pr ON id.product_id = pr.id
    WHERE id.order_id = %s;
    """

    with connection.cursor() as cursor:
        cursor.execute(invoice_query, [invoice_id])
        invoice_details = cursor.fetchone()

        if invoice_details is None:
            return HttpResponse("Invoice not found.", status=404)

        invoice_data = {
            'invoice_id': invoice_details[0],
            'invoice_date': invoice_details[1],
            'payment_id': invoice_details[2],
            'order_id': invoice_details[3],
            'total_amount': invoice_details[4],
            'customer_name': invoice_details[5],
            'customer_email': invoice_details[6],
            'customer_address': invoice_details[7],
        }

        cursor.execute(items_query, [invoice_data['order_id']])
        items_details = cursor.fetchall()

        items_data = [{
            'product_id': row[0],
            'product_name': row[1],
            'quantity': row[2],
            'price_per_item': row[3],
            'total_price': row[4],
        } for row in items_details]

    # Fetch phone numbers separately
    phone_numbers_query = """
    SELECT number
    FROM store_phonenumber
    WHERE customer_id = (SELECT id FROM store_customer WHERE email = %s);
    """
    with connection.cursor() as cursor:
        cursor.execute(phone_numbers_query, [invoice_data['customer_email']])
        phone_numbers = cursor.fetchall()
        phone_numbers = [phone[0] for phone in phone_numbers]

    return render(request, 'invoice.html', {
        'invoice': invoice_data,
        'items': items_data,
        'phone_numbers': phone_numbers
    })




from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Customer, Order

@login_required
def user_orders_view(request):
    try:
        customer = Customer.objects.get(email=request.user.username)
    except Customer.DoesNotExist:
        return HttpResponse("Customer not found.", status=404)

    orders = Order.objects.filter(customer=customer).select_related('customer').prefetch_related('item_details')

    order_details = []
    for order in orders:
        items = []
        for item in order.item_details.all():
            items.append({
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price_per_item': item.price_per_item,
                'total_price': item.total_price,
            })

        order_details.append({
            'order_id': order.id,
            'order_date': order.order_date,
            'total_amount': order.total_amount,
            'status': order.status,
            'items': items,
        })
    
    return render(request, 'user_orders.html', {'order_details': order_details})



from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.db import connection
from django.contrib.auth.decorators import login_required

@login_required
def orders_by_status_view(request):
    status_list = request.GET.getlist('status')
    user_email = request.user.username
    orders = []
    
    if status_list:
        format_strings = ','.join(['%s'] * len(status_list))
        query = f"""
            SELECT o.id, o.customer_id, o.order_date, o.status, o.total_amount
            FROM store_order o
            INNER JOIN store_customer c ON o.customer_id = c.id
            WHERE c.email = %s AND o.status IN ({format_strings})
        """
        with connection.cursor() as cursor:
            cursor.execute(query, [user_email] + status_list)
            orders = cursor.fetchall()
    
    return render(request, 'user_orders.html', {
        'orders': orders,
        'status_list': status_list
    })



