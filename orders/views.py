from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import ProtectedError, Count
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import Cart, CartItem, Address, Order
from django.contrib import messages
from .utils import update_cart_count, fulfill_cart_checkout, build_order_timeline
from products.models import Product
from custom_requests.models import CustomRequest
from .forms import AddressForm
from staff.utils import notify_staff
from staff.models import Notification
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


@require_POST
def create_and_add_cart_view(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    requested_quantity = int(request.POST.get('quantity', 1))
    if request.user.is_authenticated:
        cart, cart_created = Cart.objects.get_or_create(user=request.user)
        # no sessionkey param in case of an anonymous user who authenticates later
    else:
        if not request.session.session_key:
            request.session.create()
        cart, cart_created = Cart.objects.get_or_create(session_key=request.session.session_key)

    cart_item, item_created = CartItem.objects.get_or_create(cart=cart, product=product, defaults={'quantity': 0})

    new_quantity = cart_item.quantity + requested_quantity
    #print(f"DEBUG: new_quantity = {new_quantity} cart_item.quantity = {cart_item.quantity} requested_quantity = {requested_quantity}")
    if new_quantity > product.stock_quantity:
        messages.warning(request, f"Недостатъчна наличност от артикул {product.name} - "
                                  f"брой налични продукти в магазина: {product.stock_quantity} - брой продукти във вашата кошница: {cart_item.quantity}")
    else:
        cart_item.quantity = new_quantity
        cart_item.save()
        #print(f"DEBUG: updating count, cart={cart.id}")
        update_cart_count(request, cart)
        messages.success(request, f"Артикул {product.name} беше добавен в количката.")

    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('products:all_products')


def cart_detail_view(request):
    cart = None
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).prefetch_related('item__product__images').first()
    else:
        session_key = request.session.session_key
        if not session_key:
            return render(request, 'orders/cart_detail.html', {'cart': None, 'items': []})

        cart = Cart.objects.filter(session_key=request.session.session_key).prefetch_related('item__product__images').first()
    if cart:
        deleted_items = cart.item.filter(product__isnull=True)
        if deleted_items.exists():
            messages.warning(request, "Някои артикули бяха премахнати от количката, поради настояща неналичност.")
            deleted_items.delete()
        items = cart.item.all()
        update_cart_count(request, cart)
    else:
        items = []
    context = {
        'cart': cart,
        'items': items
    }
    return render(request, 'orders/cart_detail.html', context)


def _owns_cart(request, cart):
    if request.user.is_authenticated:
        return cart.user_id == request.user.id
    session_key = request.session.session_key
    return bool(session_key) and cart.session_key == session_key


@require_POST
def remove_from_cart_view(request, cart_item_id):
    cart_item = get_object_or_404(CartItem.objects.select_related('cart'), id=cart_item_id)
    if _owns_cart(request, cart_item.cart):
        cart_item.delete()
    return redirect('orders:cart_detail')


@require_POST
def update_cart_view(request, cart_item_id):
    cart_item = get_object_or_404(CartItem.objects.select_related('cart'), id=cart_item_id)
    action = request.POST.get('action')
    if _owns_cart(request, cart_item.cart):
        if cart_item.product is None:
            cart_item.delete()
            messages.warning(request, "Артикулът вече не се предлага и беше премахнат от количката.")
            return redirect('orders:cart_detail')
        if action == 'increase':
            if cart_item.product.stock_quantity > cart_item.quantity:
                cart_item.quantity += 1
                cart_item.save()
            else:
                messages.warning(request,f"Достигната е максималната наличност от {cart_item.product.name}.")
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
            else:
                cart_item.delete()
        update_cart_count(request, cart_item.cart)
    return redirect('orders:cart_detail')


@login_required
def address_list_view(request):
    addresses = Address.objects.filter(user=request.user).annotate(
        orders_count=Count('order', distinct=True),
        requests_count=Count('custom_requests', distinct=True),
    )
    return render(request, 'orders/address_list.html', {'addresses': addresses})


@login_required
def address_create_view(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            if not Address.objects.filter(user=request.user).exists():
                address.is_default = True
            address.save()
            messages.success(request, "Адресът беше запазен.")
            return redirect('orders:address_list')
    else:
        form = AddressForm()
    return render(request, 'orders/address_form.html', {'form': form, 'title': 'Нов адрес'})


@login_required
def address_edit_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if address.order_set.exists() or address.custom_requests.exists():
        messages.error(request, "Адресът е използван в поръчка или заявка и не може да бъде редактиран.")
        return redirect('orders:address_list')
    if request.method == 'POST':
        form = AddressForm(request.POST, instance=address)
        if form.is_valid():
            form.save()
            messages.success(request, "Адресът беше обновен успешно.")
            return redirect('orders:address_list')
    else:
        form = AddressForm(instance=address)
    return render(request, 'orders/address_form.html', {'form': form, 'title': 'Редактирай адрес'})


@login_required
def address_usage_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    orders = Order.objects.filter(address=address).order_by('-created_at')
    custom_requests = CustomRequest.objects.filter(address=address).order_by('-created_at')

    orders_page_obj = Paginator(orders, 2).get_page(request.GET.get('orders_page'))
    requests_page_obj = Paginator(custom_requests, 2).get_page(request.GET.get('requests_page'))
    context = {
        'address': address,
        'orders_page_obj': orders_page_obj,
        'requests_page_obj': requests_page_obj,
    }
    return render(request, 'orders/address_usage.html', context)


@login_required
def address_delete_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    if request.method == 'POST':
        try:
            address.delete()
            messages.success(request, "Адресът беше премахнат успешно.")
        except ProtectedError:
            messages.error(request, "Адресът не може да бъде изтрит, тъй като е използван в поръчка или заявка.")
    return redirect('orders:address_list')


@login_required
@require_POST
def address_set_default_view(request, address_id):
    address = get_object_or_404(Address, id=address_id, user=request.user)
    Address.objects.filter(user=request.user).update(is_default=False)
    address.is_default = True
    address.save()
    return redirect('orders:address_list')


@login_required
def check_out_view(request):
    cart = Cart.objects.filter(user=request.user).prefetch_related('item__product').first()
    if not cart or not cart.item.exists():
        messages.error(request, 'Количката Ви е празна.')
        return redirect('orders:cart_detail')

    addresses = Address.objects.filter(user=request.user)
    if not addresses.exists():
        messages.error(request, 'Добавете адрес за доставка')
        return redirect('orders:address_create')
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        address = get_object_or_404(Address, id=address_id, user=request.user)

        cart_items = list(cart.item.select_related('product').exclude(product__isnull=True))
        if not cart_items:
            messages.error(request, 'Количката Ви е празна.')
            return redirect('orders:cart_detail')

        for item in cart_items:
            if item.quantity > item.product.stock_quantity:
                messages.error(request, f'Продукт - {item.product.name} е изчерпан.')
                return redirect('orders:cart_detail')

        line_items = []
        for item in cart_items:
            line_items.append({
                'price_data': {
                    'currency': 'eur',
                    'product_data': {'name': item.product.name},
                    'unit_amount': int(item.product.price * 100),
                },
                'quantity': item.quantity,
            })

        items_json = json.dumps([[item.product_id, item.quantity] for item in cart_items])
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=request.build_absolute_uri(reverse('orders:payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=request.build_absolute_uri(reverse('orders:cart_detail')),
            metadata={
                'kind': 'cart_order',
                'user_id': request.user.id,
                'address_id': address.id,
                'items': items_json,
            },
        )
        return redirect(session.url, code=303)

    context = {'cart': cart, 'items': cart.item.all(), 'addresses': addresses,
               'default_address': addresses.filter(is_default=True).first()}
    return render(request, 'orders/check_out.html', context)

@login_required
def order_detail_view(request, order_id):
    order = get_object_or_404(Order.objects.select_related('address').prefetch_related('items__product'),
                              id=order_id, user=request.user)
    context = {'order': order, 'is_staff_view': False, 'timeline': build_order_timeline(order)}
    return render(request, 'orders/order_detail.html', context)

@login_required
def order_list_view(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items').order_by('-created_at')
    paginator = Paginator(orders, settings.PAGE_ITEMS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'is_staff_view': False,
    }
    return render(request, 'orders/order_list.html', context)

@login_required
def payment_success_view(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return redirect('home')
    session = stripe.checkout.Session.retrieve(session_id)
    order, created = fulfill_cart_checkout(session)
    if not order or order.user_id != request.user.id:
        messages.error(request, 'Плащането не можа да бъде потвърдено. Ако сумата е била удържана, моля, свържете се с нас.')
        return redirect('orders:cart_detail')
    cart = Cart.objects.filter(user=request.user).first()
    if cart:
        update_cart_count(request, cart)
    if created:
        messages.success(request, f'Поръчка #{order.id} беше заплатена успешно.')
        notify_staff(type=Notification.Type.NEW_ORDER,
                     message=f'Поръчка #{order.id} беше заплатена от {request.user.get_full_name()}.',
                     link=reverse('staff:staff_order_detail', args=[order.id]),
                     exclude_user=request.user,)
    return redirect('orders:order_detail', order_id=order.id)

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    #print(f"DEBUG: sig_header = {sig_header}")
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
        #print(f"DEBUG: event type = {event['type']}")
    except ValueError:
        logger.warning('Stripe webhook: malformed payload')
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        logger.warning('Stripe webhook: signature verification failed')
        return HttpResponse(status=400)
    if event['type'] != 'checkout.session.completed':
        return HttpResponse(status=200)
    session = event['data']['object']
    if session.payment_status != 'paid':
        return HttpResponse(status=200)

    metadata = getattr(session, 'metadata', None) or {}
    try:
        if 'kind' in metadata and metadata['kind'] == 'cart_order':
            order, created = fulfill_cart_checkout(session)
            if created:
                logger.info('Order %s created by webhook', order.id)
                notify_staff(
                    type=Notification.Type.NEW_ORDER,
                    message=f'Поръчка #{order.id} беше заплатена.',
                    link=reverse('staff:staff_order_detail', args=[order.id]),)
            else:
                logger.info('Stripe session %s not fulfilled by webhook (already fulfilled or unavailable)', session.id)
        elif 'custom_request_id' in metadata:
            request_id = metadata['custom_request_id']
            updated = CustomRequest.objects.filter(id=request_id, status=CustomRequest.Status.PRICE_OFFERED).update(status=CustomRequest.Status.PAID)
            if updated:
                logger.info('Custom request %s marked PAID by webhook', request_id)
                notify_staff(
                    type=Notification.Type.NEW_REQUEST,
                    message=f'Персонализирана поръчка #{request_id} беше заплатена.',
                    link=reverse('custom_requests:custom_request_detail', args=[request_id]),
                )
            else:
                logger.info('Custom request %s not transitioned by webhook (already paid or missing)', request_id)
        else:
            logger.warning('Stripe webhook: session %s has no recognised metadata', session.id)
    except Exception:
        logger.exception('Stripe webhook: failed to process session %s', session.id)
        return HttpResponse(status=500)
    return HttpResponse(status=200)