from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.utils.http import urlencode, url_has_allowed_host_and_scheme
from django.contrib import messages
from communication.models import ContactMessage
from django.urls import reverse
from orders.models import Order
from products.models import ProductReview
from custom_requests.models import CustomRequest
from .models import Notification, NotificationRecipient
from orders.models import OrderStatusHistory
from orders.utils import build_order_timeline
from django.db import transaction
from django.db.models import F, Q, Sum
from accounts.models import UserNotification
from accounts.utils import notify_user
from .utils import superuser_required, staff_required
from django.conf import settings

User = get_user_model()


# Create your views here.
@staff_required
def staff_dashboard_view(request):
    contact_messages = ContactMessage.objects.filter(is_resolved=False).count()
    orders = Order.objects.filter(status=Order.OrderStatus.PAID).count()
    pending_reviews = ProductReview.objects.filter(is_published=False, is_rejected=False).count()
    custom_requests = CustomRequest.objects.exclude(status=CustomRequest.Status.REJECTED).count()

    recent_custom_requests = CustomRequest.objects.exclude(status=CustomRequest.Status.REJECTED).select_related('user').order_by('-created_at')[:4]
    last_messages = ContactMessage.objects.exclude(is_resolved=True).select_related('user').order_by('-created_at')[:4]
    last_orders = Order.objects.all().select_related('user','address').order_by('-created_at')[:4]
    recent_notifications = NotificationRecipient.objects.filter(recipient=request.user).select_related('notification').order_by('-notification__created_at')[:4]
    recent_reviews = ProductReview.objects.all().select_related('user','product').order_by('-created_at')[:4]
    context = {
        'contact_messages': contact_messages,
        'orders': orders,
        'last_orders': last_orders,
        'last_messages':last_messages,
        'recent_notifications': recent_notifications,
        'pending_reviews':pending_reviews,
        'recent_reviews':recent_reviews,
        'custom_requests': custom_requests,
        'recent_custom_requests': recent_custom_requests,
    }
    return render(request, 'staff/staff_dashboard.html', context)

@staff_required
def staff_contact_messages_list_view(request):
    staff_contact_messages = ContactMessage.objects.select_related('user').all()
    filter_resolvance = request.GET.get('filter', '')
    if filter_resolvance == 'unresolved':
        staff_contact_messages = staff_contact_messages.filter(is_resolved=False)
    elif filter_resolvance == 'resolved':
        staff_contact_messages = staff_contact_messages.filter(is_resolved=True)
    #elif filter_resolvance == 'all':
    #    contact_messages = contact_messages.all()

    paginator = Paginator(staff_contact_messages, settings.PAGE_ITEMS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'current_filter': filter_resolvance,
        'is_staff_view': True,
    }
    return render(request,'communication/contact_messages.html', context)

@staff_required
def staff_orders_list_view(request):
    orders = Order.objects.select_related('user', 'address').order_by('-created_at')
    filter_status = request.GET.get('status','')
    if filter_status:
        orders = orders.filter(status=filter_status)
    paginator = Paginator(orders, settings.PAGE_ITEMS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'status_choices': Order.OrderStatus.choices,
        'current_status': filter_status,
        'is_staff_view':True,
    }
    return render(request,'orders/order_list.html', context)

@staff_required
def staff_order_detail_view(request, order_id):
    order = get_object_or_404(Order.objects.select_related('user','address').prefetch_related('items__product'),
         id=order_id)
    if request.method == 'POST':
        if order.user == request.user:
            messages.error(request, 'Не можете да променяте статуса на собствената си поръчка.')
        else:
            new_status = request.POST.get('status')
            if new_status in dict(Order.OrderStatus.choices):
                with transaction.atomic():
                    locked_order = Order.objects.select_for_update().get(id=order.id)
                    old_status = locked_order.status
                    if old_status != new_status:
                        if new_status == Order.OrderStatus.CANCELLED and old_status != Order.OrderStatus.CANCELLED:
                            locked_order.restock_items()

                        locked_order.status = new_status
                        locked_order.save(update_fields=['status', 'updated_at'])
                        OrderStatusHistory.objects.create(
                            order=locked_order,
                            old_status=old_status,
                            new_status=new_status,
                            changed_by=request.user,
                        )
                order.refresh_from_db()
                messages.success(request, f'Статусът на поръчка #{order.id} е обновен на {order.get_status_display()}.')
                notify_user(user=order.user, type=UserNotification.Type.ORDER_STATUS,
                            message=f'Статусът на поръчка #{order.id} е обновен на {order.get_status_display()}.',
                            link=reverse('orders:order_detail', args=[order.id]),)
        return redirect('staff:staff_order_detail', order_id=order.id)
    context = {'order': order, 'is_staff_view': True, 'timeline': build_order_timeline(order)}
    return render(request, 'orders/order_detail.html', context)

@staff_required
def notifications_view(request):
    notification_recipient = NotificationRecipient.objects.filter(
        recipient=request.user).select_related('notification').order_by('-notification__created_at')
    filter_read = request.GET.get('read', '')
    filter_type = request.GET.get('type', '')
    if filter_type:
        notification_recipient = notification_recipient.filter(notification__type=filter_type)
    if filter_read == 'unread':
        notification_recipient = notification_recipient.filter(is_read=False)
    elif filter_read == 'read':
        notification_recipient = notification_recipient.filter(is_read=True)
    paginator = Paginator(notification_recipient, settings.PAGE_ITEMS)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj':page_obj,
        'type_choices': Notification.Type.choices,
        'current_type': filter_type,
        'current_read': filter_read,
    }
    return render(request, 'staff/notifications.html', context)

@staff_required
def notification_is_read_view(request, notification_id):
    notification_recipient = get_object_or_404(NotificationRecipient, notification__id=notification_id, recipient=request.user)
    notification_recipient.is_read=True
    notification_recipient.save()
    if notification_recipient.notification.link:
        return redirect(notification_recipient.notification.link)
    return redirect('staff:staff_notifications')

@staff_required
def reviews_view(request):
    reviews_list = ProductReview.objects.select_related('user', 'product')
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'not_published':
        reviews_list = reviews_list.filter(is_published=False, is_rejected=False)
    elif filter_type == 'published':
        reviews_list = reviews_list.filter(is_published=True)
    elif filter_type == 'rejected':
        reviews_list = reviews_list.filter(is_rejected=True)
    paginator = Paginator(reviews_list, settings.PAGE_ITEMS)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj':page_obj,
        'current_filter':filter_type,
    }
    return render(request, 'staff/staff_reviews_list.html', context)

@staff_required
def review_approve_view(request, review_id):
    review = get_object_or_404(ProductReview.objects.select_related('user', 'product__category'), id=review_id)
    if request.method == 'POST':
        if review.user == request.user:
            messages.error(request, 'Не можете да одобрявате или отхвърляте собствения си коментар.')
        else:
            action = request.POST.get('action')
            if action == 'approve':
                review.is_published = True
                review.is_rejected = False
                review.save(update_fields=['is_published', 'is_rejected'])
                messages.success(request, f'Коментарът е одобрен.')
                notify_user(user=review.user, type=UserNotification.Type.REVIEW_APPROVED,
                            message=f'Отзив #{review.id} за продукт {review.product.name} беше одобрен.',
                            link=reverse('products:product_detail',
                                         args=[review.product.category.slug, review.product.slug]),)
            elif action == 'disapprove':
                review.is_published = False
                review.is_rejected = True
                review.rejection_count = F('rejection_count') + 1
                review.save(update_fields=['is_published', 'is_rejected', 'rejection_count'])
                review.refresh_from_db(fields=['rejection_count'])
                messages.error(request, f'Коментарът е отхвърлен.')
                notify_user(user=review.user, type=UserNotification.Type.REVIEW_APPROVED,
                            message=f'Отзив #{review.id} за продукт {review.product.name} беше отхвърлен. '
                                    f'Можете да го редактирате и да го изпратите отново за преглед.',
                            link=reverse('products:review_edit', args=[review.id]),)
        next_url = request.POST.get('next')
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()},
                                                          require_https=request.is_secure()):
            return redirect(next_url)
        return redirect('staff:staff_approve_review', review_id=review.id)
    total_rejections = ProductReview.objects.filter(user=review.user).aggregate(
        total=Sum('rejection_count'))['total'] or 0
    context = {'review': review, 'total_rejections': total_rejections}
    return render(request, 'staff/staff_review_detail.html', context)

@staff_required
def custom_requests_list_view(request):
    filter_status = request.GET.get('status','')
    custom_requests = CustomRequest.objects.select_related('user').order_by('-created_at')
    if filter_status:
        custom_requests = custom_requests.filter(status=filter_status)
    paginator = Paginator(custom_requests, settings.PAGE_ITEMS)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'type_choices': CustomRequest.Status.choices,
        'current_status': filter_status,
    }
    return render(request, 'staff/staff_custom_requests.html', context)

@superuser_required
def manage_staff_view(request):
    query = request.GET.get('q', '').strip()
    show_all = request.GET.get('all') == '1'
    if query:
        users = User.objects.filter(
            Q(email__icontains=query) | Q(first_name__icontains=query) | Q(last_name__icontains=query)
        )
    elif show_all:
        users = User.objects.all()
    else:
        users = User.objects.filter(is_staff=True)
    users = users.order_by('email')
    paginator = Paginator(users, settings.PAGE_ITEMS)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'page_obj': page_obj,
        'query': query,
        'show_all': show_all,
        'all_param': '1' if show_all else '',
    }
    return render(request, 'staff/staff_manage_staff.html', context)

@superuser_required
@require_POST
def toggle_staff_status_view(request, user_id):
    target = get_object_or_404(User, id=user_id)
    if target.is_superuser:
        messages.error(request, 'Не можете да променяте правата на администратор оттук.')
    elif target == request.user:
        messages.error(request, 'Не можете да премахнете собствения си достъп.')
    else:
        target.is_staff = not target.is_staff
        target.save(update_fields=['is_staff'])
        if target.is_staff:
            messages.success(request, f'{target.email} вече е част от персонала.')
            notify_user(user=target, type=UserNotification.Type.STAFF_STATUS,
                        message='Вече сте част от екипа на WoolCraft. Може да достъпите административния панел от тук.',
                        link=reverse('staff:staff_dashboard'), )
        else:
            messages.success(request, f'{target.email} вече не е част от персонала.')
            notify_user(user=target, type=UserNotification.Type.STAFF_STATUS,
                        message='Вече не сте част от екипа на WoolCraft и достъпът Ви до административния панел е премахнат.',
                        link=reverse('accounts:profile'), )
    query = request.GET.get('q', '')
    params = {}
    if query:
        params['q'] = query
    if request.GET.get('all') == '1':
        params['all'] = '1'
    redirect_url = reverse('staff:staff_manage_staff')
    if params:
        redirect_url += f'?{urlencode(params)}'
    return redirect(redirect_url)