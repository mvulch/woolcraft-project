from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse
from orders.models import Address
from .models import CustomRequest
from .forms import CustomRequestForm, CustomRequestMessageForm, OfferPriceForm
from staff.utils import notify_staff
from staff.models import Notification
from accounts.models import UserNotification
from accounts.utils import notify_user
from .utils import mark_order_paid
import stripe
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def custom_request_create_view(request):
    if request.method == 'POST':
        form = CustomRequestForm(request.POST, request.FILES)
        if form.is_valid():
            custom_request = form.save(commit=False)
            custom_request.user = request.user
            custom_request.save()
            notify_staff(
                type=Notification.Type.NEW_REQUEST,
                message=f'Нова персонализирана заявка #{custom_request.id} от {custom_request.user.get_full_name()}',
                link=reverse('custom_requests:custom_request_detail', args=[custom_request.id]),
                exclude_user=request.user,
            )
            messages.success(request, 'Заявката Ви е изпратена успешно и очаква да бъде разгледана от нашия екип.')
            return redirect('custom_requests:custom_request_detail', request_id=custom_request.id)
    else:
        form = CustomRequestForm()
    return render(request, 'custom_requests/custom_request_create.html', {'form':form})

@login_required
def custom_requests_list_view(request):
    custom_requests = CustomRequest.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(custom_requests, settings.PAGE_ITEMS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'custom_requests/custom_requests_list.html', context)

@login_required
def custom_request_detail_view(request, request_id):
    if request.user.is_staff:
        custom_request = get_object_or_404(CustomRequest.objects.select_related('user').prefetch_related('messages__user'),id=request_id)
    else:
        custom_request = get_object_or_404(CustomRequest.objects.select_related('user').prefetch_related('messages__user'),
                                          id=request_id, user=request.user)
    form = CustomRequestMessageForm()
    price_form = OfferPriceForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'message':
            form = CustomRequestMessageForm(request.POST)
            if form.is_valid():
                message = form.save(commit=False)
                message.user = request.user
                message.request = custom_request
                message.save()
                if request.user == custom_request.user:
                    notify_staff(type=Notification.Type.NEW_REQUEST,
                                 message=f'Нов отговор на заявка #{custom_request.id}',
                                 link=reverse('custom_requests:custom_request_detail', args=[custom_request.id]),
                                 exclude_user=request.user, )
                else:
                    notify_user(user=custom_request.user, type=UserNotification.Type.CUSTOM_REQUEST_MESSAGE,
                                message=f'Получен отговор на заявка #{custom_request.id}.',
                                link=reverse('custom_requests:custom_request_detail', args=[custom_request.id]), )
                messages.success(request, 'Съобщението е изпратено.')
                return redirect('custom_requests:custom_request_detail', request_id=custom_request.id)
        elif action == 'update_status':
            if not request.user.is_superuser:
                messages.error(request, 'Само администратор може да променя статуса на заявката.')
            elif custom_request.user == request.user:
                messages.error(request, 'Не можете да променяте статуса на собствена си заявка.')
            else:
                new_status = request.POST.get('status')
                if new_status in dict(CustomRequest.Status.choices):
                    custom_request.status = new_status
                    custom_request.save()
                    messages.success(request, 'Статусът е обновен успешно.')
                    notify_user(user=custom_request.user, type=UserNotification.Type.CUSTOM_REQUEST_STATUS,
                                message=f'Статусът на заявка #{custom_request.id} е сменен на {custom_request.get_status_display()}.',
                                link=reverse('custom_requests:custom_request_detail', args=[custom_request.id]), )

                    return redirect('custom_requests:custom_request_detail', request_id=custom_request.id)
                else:
                    messages.error(request, 'Невалиден статус.')

        elif action == 'offer_price':
            if not request.user.is_superuser:
                messages.error(request, 'Само администратор може да предлага цена по заявката.')
            elif custom_request.user == request.user:
                messages.error(request, 'Не можете да предлагате цена за собствената си заявка.')
            else:
                price_form = OfferPriceForm(request.POST)
                if price_form.is_valid():
                    custom_request.offered_price = price_form.cleaned_data['offered_price']
                    custom_request.status = CustomRequest.Status.PRICE_OFFERED
                    custom_request.save(update_fields=['offered_price','status','updated_at'])
                    notify_user(user=custom_request.user, type=UserNotification.Type.CUSTOM_REQUEST_PRICE,
                                message=f'Получена ценова оферта за заявка #{custom_request.id}.',
                                link=reverse('custom_requests:custom_request_detail', args=[custom_request.id]), )

                    messages.success(request, 'Цената е предложена.')
                    return redirect('custom_requests:custom_request_detail', request_id=custom_request.id)

        elif action == 'client_decline' and custom_request.user == request.user:
            if custom_request.status == CustomRequest.Status.PRICE_OFFERED:
                custom_request.status = CustomRequest.Status.DECLINED
                custom_request.save()
                notify_staff(
                    type=Notification.Type.NEW_REQUEST,
                    message=f'Отказана цена на персонализирана заявка #{custom_request.id} от клиент {custom_request.user.get_full_name()}',
                    link=reverse('custom_requests:custom_request_detail', args=[custom_request.id]),
                    exclude_user=request.user,)
                messages.info(request, 'Отказахте предложената цена.')
                return redirect('custom_requests:custom_request_detail', request_id=custom_request.id)
    context = {
        'custom_request': custom_request,
        'form': form,
        'price_form': price_form,
    }
    return render(request, 'custom_requests/custom_request_detail.html', context)

@login_required
def custom_request_address_view(request, request_id):
    custom_request = get_object_or_404(CustomRequest, id=request_id, user=request.user, status=CustomRequest.Status.PRICE_OFFERED)

    addresses = Address.objects.filter(user=request.user)
    if not addresses.exists():
        messages.error(request, 'Добавете адрес за доставка')
        return redirect('orders:address_create')
    if request.method == 'POST':
        address_id = request.POST.get('address_id')
        address = get_object_or_404(Address, id=address_id, user=request.user)
        custom_request.address = address
        custom_request.save()
        return redirect('custom_requests:custom_request_payment', request_id=custom_request.id)

    context = {
        'custom_request': custom_request,
        'addresses': addresses,
        'default_address': addresses.filter(is_default=True).first(),
    }
    return render(request, 'custom_requests/address_select.html', context)


@login_required
def custom_request_payment_view(request, request_id):
    custom_request = get_object_or_404(CustomRequest, id=request_id, user=request.user, status=CustomRequest.Status.PRICE_OFFERED)
    if custom_request.address is None:
        messages.error(request, 'Добавете адрес за доставка, преди да платите.')
        return redirect('custom_requests:address', request_id=custom_request.id)
    if custom_request.offered_price is None:
        messages.error(request, 'Все още не е предложена цена за заявката.')
        return redirect('custom_requests:custom_request_detail', request_id=custom_request.id)
    line_items = [{
        'price_data': {
            'currency': 'eur',
            'product_data': {'name': f'Персонализирана заявка - поръчка ръчна изработка #{custom_request.id} - {custom_request.title}.',},
            'unit_amount': int(custom_request.offered_price * 100),
        },
        'quantity': 1
    }]
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=request.build_absolute_uri(reverse('custom_requests:custom_request_payment_success')) + '?session_id={CHECKOUT_SESSION_ID}',
        cancel_url=request.build_absolute_uri(
            reverse('custom_requests:custom_request_detail', kwargs={'request_id': custom_request.id})
        ),
        metadata={'custom_request_id': custom_request.id},
    )
    custom_request.stripe_payment_id = session.id
    custom_request.save(update_fields=['stripe_payment_id','updated_at'])
    return redirect(session.url, code=303)

@login_required
def custom_request_payment_success_view(request):
    session_id = request.GET.get('session_id')
    if not session_id:
        return redirect('home')
    session = stripe.checkout.Session.retrieve(session_id)
    metadata = getattr(session, 'metadata', None) or {}
    custom_request_id = metadata['custom_request_id'] if 'custom_request_id' in metadata else None
    if not custom_request_id:
        logger.warning('Stripe session %s hsa no custom_request_id metadata',session_id)
        return redirect('home')
    custom_request = get_object_or_404(CustomRequest, id=custom_request_id, user=request.user)

    if session.payment_status == 'paid' and mark_order_paid(custom_request_id):
        messages.success(request, f'Поръчка #{custom_request.id} беше заплатена успешно. Очаквайте скоро да бъде изработена!')
        notify_staff(type=Notification.Type.NEW_REQUEST,
                 message=f'Персонализирана поръчка #{custom_request.id} беше заплатена от {request.user.get_full_name()}.',
                 link=reverse('custom_requests:custom_request_detail', args=[custom_request.id]),
                 exclude_user=request.user,)
    return redirect('custom_requests:custom_request_detail', request_id=custom_request.id)
