# store/context_processors.py
from .models import Cart, CartItem
from django.db.models import Sum

def cart_item_count(request):
    # Ensure user is logged in
    if not request.user.is_authenticated:
        return {'cart_item_count': 0}

    try:
        # Get the user's active cart
        cart = Cart.objects.get(user=request.user)

        # Calculate the total quantity of all items in the cart
        # This sums up the 'quantity' field of all items
        count_data = CartItem.objects.filter(cart=cart).aggregate(total_quantity=Sum('quantity'))

        # Get the total, or 0 if the cart is empty
        count = count_data['total_quantity'] or 0

    except Cart.DoesNotExist:
        count = 0

    return {'cart_item_count': count}

