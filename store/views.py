from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from django.db import connection, transaction, IntegrityError
from django.contrib.auth.models import User

# ===== IMPORT YOUR MODELS =====
from .models import (
    Customer, PhoneNumber, Product, Category, Supplier, 
    Order, Payment, CreditPayment, UPIPayment, BankPayment, 
    Invoice, Review, Cart, CartItem, ItemDetail
)


# ===== LOGIN VIEW =====
def login_view(request):
    if request.method == 'POST':
        email = request.POST['email']
        password = request.POST['password']

        # Authenticate user using email as the username
        user = authenticate(request, username=email, password=password)

        if user is not None:
            login(request, user)
            # Redirect to the product list page
            return redirect('list_products')
        else:
            return HttpResponse("Invalid login credentials. Please try again.")
    return render(request, 'login.html')


# ===== SIGNUP VIEW =====
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


# ===== CUSTOM LOGOUT VIEW =====
def custom_logout_view(request):
    logout(request)
    return redirect('login')


# ===== LIST PRODUCTS VIEW (MODIFIED FOR PROFILE) =====
@login_required
def list_products_view(request):
    order_by = request.GET.get('order_by', 'asc')
    category_filter = request.GET.get('category', '')
    supplier_filter = request.GET.get('supplier', '')
    min_price = request.GET.get('min_price', 0)
    max_price = request.GET.get('max_price', 1000000)
    search_query = request.GET.get('search', '')

    # Fetch all categories and suppliers for the filter dropdown
    categories = Category.objects.all()
    suppliers = Supplier.objects.all()

    # Get the cart for the cart count
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    # ✅ GET CUSTOMER & PHONE FOR PROFILE DROPDOWN
    customer = None
    phone_numbers = []
    try:
        customer = Customer.objects.get(email=request.user.username)
        phone_numbers = PhoneNumber.objects.filter(customer=customer)
    except Customer.DoesNotExist:
        # Handle case where user is logged in but has no customer profile
        pass 

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

    # ✅ ADD CUSTOMER & PHONES TO CONTEXT
    return render(request, 'list_products.html', {
        'products': product_details,
        'cart': cart,
        'categories': categories,
        'suppliers': suppliers,
        'order_by': order_by,
        'category_filter': category_filter,
        'supplier_filter': supplier_filter,
        'min_price': min_price,
        'max_price': max_price,
        'search_query': search_query,
        'customer': customer,  # Pass customer to template
        'phone_numbers': phone_numbers # Pass phone numbers to template
    })


# ===== REVIEW PAGE VIEW =====
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
        return render(request, 'review_page.html', {
            'products': products,
            'reviews': reviews,
            'selected_product_id': selected_product_id
        })

    return render(request, 'review_page.html', {
        'products': products,
        'reviews': reviews,
        'selected_product_id': selected_product_id
    })


# ===== PRODUCT PAYMENT VIEW =====
@login_required
def product_payment_view(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    # ✅ FIX: Pass total_amount to template
    total_amount = order.total_amount
    
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
                # ✅ NO UNIQUE CHECK: Just create the payment
                UPIPayment.objects.create(
                    payment=payment,
                    wallet_id=request.POST.get('wallet_id', ''),
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
            return HttpResponse(f"An error occurred: {str(e)}", status=400)

    # ✅ FIX: Pass total_amount to template for direct order now
    return render(request, 'payment_form.html', {'total_amount': total_amount})


# ===== ORDER PRODUCT VIEW =====
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


# ===== ADD TO CART VIEW =====
@login_required
def add_to_cart_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
    
    if not created:
        cart_item.quantity += int(request.POST.get('quantity', 1))
    else:
        cart_item.quantity = int(request.POST.get('quantity', 1))
    cart_item.save()
    
    return redirect('view_cart')


# ===== VIEW CART VIEW =====
@login_required
def view_cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    total_cost = sum(item.product.price * item.quantity for item in cart.items.all())
    return render(request, 'view_cart.html', {'cart': cart, 'total_cost': total_cost})


# ===== REMOVE FROM CART VIEW =====
@login_required
def remove_from_cart_view(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    cart_item.delete()
    return redirect('view_cart')


# ===== ORDER CART VIEW =====
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


# ===== CART PAYMENT VIEW =====
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
                # ✅ NO UNIQUE CHECK: Just create the payment
                UPIPayment.objects.create(
                    payment=payment,
                    wallet_id=request.POST.get('wallet_id', ''),
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
            return HttpResponse(f"An error occurred: {str(e)}", status=400)

    return render(request, 'payment_form.html', {'total_amount': total_amount})


# ===== USER PAYMENTS VIEW ✅ FIXED WITH AVERAGE_PURCHASE =====
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

    # ✅ FIX: Calculate average purchase - THIS WAS THE ERROR!
    average_purchase = round(total_spent / len(payment_details), 2) if payment_details else 0

    return render(request, 'user_payments.html', {
        'payment_details': payment_details, 
        'total_spent': total_spent,
        'average_purchase': average_purchase  # ✅ PASS THIS TO TEMPLATE
    })


# ===== VIEW INVOICE =====
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


# ===== USER ORDERS VIEW =====
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


# ===== ORDERS BY STATUS VIEW =====
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

@login_required
def get_order_items_api(request, order_id):
    """API endpoint to fetch order items"""
    try:
        # Get the order and verify it belongs to the logged-in user
        customer = Customer.objects.get(email=request.user.username)
        order = Order.objects.get(id=order_id, customer=customer)
        
        # Fetch all items for this order
        items = ItemDetail.objects.filter(order=order).select_related('product')
        
        items_data = []
        total_items_price = 0
        
        for item in items:
            item_total = item.price_per_item * item.quantity
            total_items_price += item_total
            
            items_data.append({
                'product_id': item.product.id,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price_per_item': float(item.price_per_item),
                'total_price': float(item_total),
                'category': item.product.category.name if item.product.category else 'N/A',
            })
        
        return JsonResponse({
            'success': True,
            'order_id': order.id,
            'order_date': order.order_date.strftime('%B %d, %Y'),
            'items': items_data,
            'total_items_count': len(items_data),
            'total_price': float(total_items_price),
        })
    
    except Order.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Order not found or access denied'
        }, status=44)
    
    except Customer.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Customer not found'
        }, status=404)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
        


#chat bot
import json
import google.generativeai as genai
from django.conf import settings
from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

# --- 1. YOUR API KEY ---
YOUR_NEW_SAFE_API_KEY = "keep your api key here"
genai.configure(api_key=YOUR_NEW_SAFE_API_KEY)


# --- 2. YOUR FULL STORE KNOWLEDGE ---
# (I've added a new formatting rule at the end)
FAQ_PROMPT = """
You are a friendly and helpful e-commerce assistant.
Your goal is to answer the user's questions based only on the information below.

--- STORE INFORMATION (FAQs) ---

1.  *Shipping Policy:*
    * We ship to the entire United States. Standard shipping takes 5-7 business days.
    * Shipping is free on all orders over $75.

2.  *Return Policy:*
    * We offer a 30-day, no-questions-asked return policy.
    * To start a return, email support@my-store.com.
    
3.  *Customer Care:*
    * For help with an order, you can call our customer care number: (555) 123-4567.

4.  *Categories:*
    * We sell: ELECTRONICS, WATCH, Clothing, TOYS, SPORTS, and BOOKS.

--- FULL PRODUCT CATALOG ---
(You must answer product questions only from this list. You cannot see stock.)

* *Product:* LEGO_FIREMAN
    * *Category:* TOYS
    * *Supplier:* LEGO
    * *Price:* $99
    * *Description:* Child-Friendly

* *Product:* DBMS BOOK
    * *Category:* BOOKS
    * *Supplier:* McGraw-Hill Education
    * *Price:* $150
    * *Description:* This book has good theory

* *Product:* PENDRIVE
    * *Category:* ELECTRONICS
    * *Supplier:* HP
    * *Price:* $200
    * *Description:* 64GB

* *Product:* ROKERZ 460
    * *Category:* ELECTRONICS
    * *Supplier:* BOAT
    * *Price:* $300
    * *Description:* 30 hrs Play Back

* *Product:* Boxing Gloves
    * *Category:* SPORTS
    * *Supplier:* JSW Sports
    * *Price:* $300
    * *Description:* nice comfort and soft

* *Product:* Chess Board
    * *Category:* SPORTS
    * *Supplier:* JSW Sports
    * *Price:* $300
    * *Description:* Board quality is good

* *Product:* BLOCKS
    * *Category:* TOYS
    * *Supplier:* LEGO
    * *Price:* $320
    * *Description:* SET OF 20

* *Product:* Hockey stick
    * *Category:* SPORTS
    * *Supplier:* JSW Sports
    * *Price:* $350
    * *Description:* material quality is nice

* *Product:* Basket Ball
    * *Category:* SPORTS
    * *Supplier:* JSW Sports
    * *Price:* $450
    * *Description:* material quality is top notch

* *Product:* Nirvana 751
    * *Category:* ELECTRONICS
    * *Supplier:* BOAT
    * *Price:* $500
    * *Description:* Active ANC

* *Product:* PS5
    * *Category:* ELECTRONICS
    * *Supplier:* SONY
    * *Price:* $800
    * *Description:* GAMING

* *Product:* Cricket Bat
    * *Category:* SPORTS
    * *Supplier:* JSW Sports
    * *Price:* $900
    * *Description:* light weighted and balanced

* *Product:* Race-Car
    * *Category:* TOYS
    * *Supplier:* HOT-WHEELS
    * *Price:* $999
    * *Description:* Metallic TOY

* *Product:* Titan neo
    * *Category:* WATCH
    * *Supplier:* REALIENCE
    * *Price:* $1000
    * *Description:* BEAUTIFUL WATCH

* *Product:* VICTUS
    * *Category:* ELECTRONICS
    * *Supplier:* REALIENCE
    * *Price:* $1300
    * *Description:* GAMING

* *Product:* Victus_HP
    * *Category:* ELECTRONICS
    * *Supplier:* HP
    * *Price:* $1500
    * *Description:* Gaming laptop

* *Product:* IPHONE
    * *Category:* ELECTRONICS
    * *Supplier:* REALIENCE
    * *Price:* $2000
    * *Description:* FASETEST PHONE

* *Product:* MEN-Shirt
    * *Category:* Clothing
    * *Supplier:* Raymond Ltd
    * *Price:* $2000
    * *Description:* Made with Cotton

* *Product:* Iphone_Apple
    * *Category:* ELECTRONICS
    * *Supplier:* Apple
    * *Price:* $2200
    * *Description:* Fastest phone (Note: This item is currently listed as Out of Stock)

* *Product:* MEN'S Premium
    * *Category:* Clothing
    * *Supplier:* Raymond Ltd
    * *Price:* $2300
    * *Description:* Printed with design

* *Product:* ROLEX
    * *Category:* WATCH
    * *Supplier:* IKEA
    * *Price:* $20000
    * *Description:* DIAMOND EDITION
--- HOW-TO GUIDES ---

* *How to check your cart:*
    * "To see your shopping cart, go to the main page. In the top-right corner, you will see a 'shopping_cart' icon. Click on that to view your cart."
* *How to track an order:*
    * "To track a past order, go to the main page and click on the 'My Orders' link in the navigation bar. You will be able to see your order history and tracking status there."
* *How to check payment history:*
    * "You can find your payment history by clicking on the 'Payment History' link, which is located in the navigation bar on the main page."
* *How to place an order:*
    * "To place an order, find the product you want and click 'Add to Cart'. When you are ready, go to your cart by clicking the 'shopping_cart' icon and follow the checkout steps."    

--- IMPORTANT RULES ---
* *NEW RULE:* When listing products, you *MUST* use a bulleted list (using an asterisk ), with **one product per line*. Do not put them all on one line.
* You *CAN* see all products, prices, and descriptions from the catalog.
* You *CANNOT* see live inventory or stock.
* If a user asks about stock or availability, you must answer: "I can't see live inventory. For the most accurate stock information, please check the product page on the website for live updates."
* If a user asks about the "Iphone_Apple", you should mention it is listed as Out of Stock.
"""
# --- End of store information ---


@ensure_csrf_cookie
def chat_api(request):
    """Handles AJAX requests from the frontend."""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            user_message = data.get('message')

            # --- 3. YOUR WORKING MODEL NAME ---
            model = genai.GenerativeModel(
                'models/gemini-2.5-flash',  # This name is from your working list
                system_instruction=FAQ_PROMPT
            )

            # 4. Start the chat and send the user's message
            chat = model.start_chat(history=[])
            response = chat.send_message(user_message) 

            return JsonResponse({'reply': response.text, 'status': 'success'})

        except Exception as e:
            print(f"Chat API Error: {e}")
            return JsonResponse({'error': str(e), 'status': 'error'}, status=500)

    return JsonResponse({'error': 'Invalid request'}, status=400)

def chat_page(request):
    """Renders the HTML page containing the chat widget."""
    return render(request, 'chat.html')

# ===== VIEW CART VIEW (UPDATED FOR PROFILE DROPDOWN) =====
@login_required
def view_cart_view(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    total_cost = sum(item.product.price * item.quantity for item in cart.items.all())
    
    # --- ADD THIS CODE ---
    customer = None
    phone_numbers = []
    try:
        customer = Customer.objects.get(email=request.user.username)
        phone_numbers = PhoneNumber.objects.filter(customer=customer)
    except Customer.DoesNotExist:
        # User is logged in but might not have a customer profile
        pass 
    # --- END OF ADDED CODE ---

    # --- UPDATE THE RETURN DICTIONARY ---
    return render(request, 'view_cart.html', {
        'cart': cart, 
        'total_cost': total_cost,
        'customer': customer,          # <-- Pass customer to template
        'phone_numbers': phone_numbers # <-- Pass phone numbers to template
    })

# ===== CHAT PAGE VIEW (UPDATED FOR NAVBAR) =====
@login_required
def chat_page(request):
    """Renders the HTML page containing the chat widget."""
    
    # --- ADD THIS DATA FOR THE NAVBAR ---
    customer = None
    phone_numbers = []
    try:
        customer = Customer.objects.get(email=request.user.username)
        phone_numbers = PhoneNumber.objects.filter(customer=customer)
    except Customer.DoesNotExist:
        pass 
    
    cart, created = Cart.objects.get_or_create(user=request.user)
    # --- END OF ADDED DATA ---

    # --- UPDATE THE RETURN DICTIONARY ---
    return render(request, 'chat.html', {
        'customer': customer,
        'phone_numbers': phone_numbers,
        'cart': cart
    })

from django.shortcuts import render
from django.contrib.auth import get_user_model
from django.http import HttpResponse # Keep if needed for raw responses, though render is better here

# Get the User model
User = get_user_model() 

def forgot_password_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        try:
            # Check if a user with this email exists in the database
            user = User.objects.get(email__iexact=email) 
            
            # --- User FOUND Logic ---
            
            # 1. (Real-world: Generate token and send actual reset email here)
            
            # 2. Respond with the success message
            context = {
                # SUCCESS message: Tells the user the email is sent
                'message': 'Password reset mail will be sent to the provided email address shortly.',
                'status': 'success'
            }
            return render(request, 'forgot_password.html', context)

        except User.DoesNotExist:
            # --- User NOT FOUND Logic ---
            
            # Respond with the 'create account' message as requested
            context = {
                # FAILURE message: Tells the user to create an account
                'message': f"The email address '{email}' was not found. Please verify the address or create an account first.",
                'status': 'not_found'
            }
            return render(request, 'forgot_password.html', context)

    # For GET requests or initial page load
    return render(request, 'forgot_password.html')
