from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import Http404
from django.shortcuts import render, get_object_or_404
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from .models import ContactMessage, Article, ArticleImage
from .forms import ContactMessageForm, ContactMessageReplyForm
from staff.utils import notify_staff
from staff.models import Notification
from accounts.models import UserNotification
from accounts.utils import notify_user
from django.conf import settings


# Create your views here.
@login_required
def contact_messages_list_view(request):
    contact_messages = ContactMessage.objects.filter(user=request.user)
    paginator = Paginator(contact_messages, settings.PAGE_ITEMS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'is_staff_view': False,
        'page_obj': page_obj,
    }
    return render(request, 'communication/contact_messages.html', context)

@login_required
def create_contact_view(request):
    if request.method == 'POST':
        form = ContactMessageForm(request.POST)
        if form.is_valid():
            contact_message = form.save(commit=False)
            contact_message.user = request.user
            contact_message.save()
            messages.success(request,"Съобщението Ви е изпратено успешно.")
            notify_staff(type=Notification.Type.NEW_CONTACT,
                         message=f'Ново запитване от {request.user.get_full_name()} на тема {contact_message.subject}.',
                         link=reverse('communication:contact_detail', args=[contact_message.id]),
                         exclude_user=request.user,)

            return redirect('communication:contact_detail', contact_message_id=contact_message.id)
    else:
        form = ContactMessageForm()
    return render(request, 'communication/create_contact.html', {'form': form})

@login_required
def contact_detail_view(request, contact_message_id):
    contact_message = get_object_or_404(ContactMessage.objects
                                        .prefetch_related('replies'),
                                        id=contact_message_id)
    if contact_message.user != request.user and not request.user.is_staff:
        raise Http404("Нямате достъп до това съобщение.")
    form = ContactMessageReplyForm()
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'resolve':
            if request.user.is_staff and contact_message.user != request.user:
                contact_message.is_resolved = True
                contact_message.save()
                messages.success(request,'Казусът е отбелязан като приключен.')
                return redirect('staff:staff_contact_messages')
            messages.error(request, 'Нямате право да приключите този казус.')
            return redirect('communication:contact_detail', contact_message_id=contact_message_id)

        if action == 'reply' and not contact_message.is_resolved:
            form = ContactMessageReplyForm(request.POST)
            if form.is_valid():
                reply = form.save(commit=False)
                reply.user = request.user
                reply.message = contact_message
                reply.save()
                if request.user == contact_message.user:
                    notify_staff(type=Notification.Type.NEW_CONTACT,
                                 message=f'Отговор от {request.user.get_full_name()} на запитване {contact_message.id}.',
                                 link=reverse('communication:contact_detail', args=[contact_message.id]),
                                 exclude_user=request.user, )
                else:
                    notify_user(user=contact_message.user, type=UserNotification.Type.CONTACT_REPLY,
                                message=f'Получен отговор на съобщение #{contact_message.id}.',
                                link=reverse('communication:contact_detail', args=[contact_message.id]), )

                messages.success(request, "Съобщението Ви е добавено успешно.")
                return redirect('communication:contact_detail', contact_message_id=contact_message_id)

        if contact_message.is_resolved:
            messages.error(request, "Този казус е отбелязан като приключен.")
            return redirect('communication:contact_detail', contact_message_id=contact_message_id)

    context = {
        'contact_message': contact_message,
        'form': form,
    }
    return render(request, 'communication/contact_detail.html', context)

def article_list_view(request):
    articles = Article.objects.filter(is_published=True).prefetch_related('images')
    paginator = Paginator(articles, settings.PAGE_ITEMS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'articles': articles,
        'page_obj':page_obj,
    }
    return render(request, 'communication/article_list.html', context)

def article_detail_view(request, slug):
    article = get_object_or_404(Article.objects.prefetch_related('images'), slug=slug, is_published=True)
    return render(request, 'communication/article_detail.html', {'article':article})
