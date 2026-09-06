from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse

from .models import Product, Category, ProductReview, VideoCourse
from django.core.paginator import Paginator
from orders.models import Cart, Order, OrderItem
from .forms import ProductReviewForm
from staff.utils import notify_staff
from django.contrib import messages
from staff.models import Notification
from communication.models import Article
from django.contrib.auth.decorators import login_required
from django.conf import settings


# Create your views here.
def home_view(request):
    latest_products = Product.objects.filter(is_active=True).order_by('-created_at').prefetch_related('images')[:8]
    recommended_articles = Article.objects.filter(is_published=True).order_by('-created_at').prefetch_related('images')[:4]
    return render(request, 'home.html', {
        'latest_products': latest_products,
        'recommended_articles': recommended_articles,
    })
def product_detail_view(request,category_slug,slug):
    product_detail = get_object_or_404(Product.objects
                                       .select_related('category','video_course')
                                       .prefetch_related('attributes', 'images'), is_active=True,slug=slug, category__slug=category_slug)
    reviews = ProductReview.objects.filter(product=product_detail, is_published=True).select_related('user')
    can_review = False
    existing_review = None
    review_form = None
    if request.user.is_authenticated:
        can_review = OrderItem.objects.filter(
            order__user=request.user,product=product_detail,
            order__status=Order.OrderStatus.DELIVERED).exists()
        existing_review = ProductReview.objects.filter(user=request.user,product=product_detail).first()
    if can_review and not existing_review:
        if request.method == 'POST' and 'review_submit' in request.POST:
            review_form = ProductReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.user = request.user
                review.product = product_detail
                review.save()
                notify_staff(type=Notification.Type.NEW_REVIEW,
                             message=f'Нов коментар от {request.user.get_full_name()} за продукт {product_detail}.',
                             link=reverse('staff:staff_approve_review', args=[review.id]),
                             exclude_user=request.user,)
                messages.success(request, f'Коментарът е създаден успешно и очаква одобрение от нашия екип.')
                return redirect('products:product_detail', category_slug=category_slug, slug=slug)
        else:
            review_form = ProductReviewForm()

    quantity_in_cart = 0
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user).first()
    else:
        cart = Cart.objects.filter(session_key=request.session.session_key).first()

    if cart:
        cart_item = cart.item.filter(product=product_detail).first()
        if cart_item:
            quantity_in_cart = cart_item.quantity
    has_video_access = False
    if request.user.is_authenticated and hasattr(product_detail, 'video_course'):
        has_video_access = request.user.is_staff or OrderItem.objects.filter(
            order__user=request.user,
            product=product_detail,
            order__status__in=(Order.OrderStatus.PAID, Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED,),
        ).exists()
    context = {
        'product': product_detail,
        'max_quantity': product_detail.stock_quantity - quantity_in_cart,
        'reviews': reviews,
        'review_form': review_form,
        'can_review': can_review,
        'existing_review': existing_review,
        'has_video_access': has_video_access,
    }
    return render(request, 'products/product_detail.html', context)

def category_products_view(request, category_slug=None):
    # all main categories
    categories = Category.objects.filter(parent=None).prefetch_related('subcategories')
    products = Product.objects.filter(is_active=True).select_related('category').prefetch_related('attributes', 'images')
    category=None
    if category_slug:
        # the chosen category at the moment
        category = get_object_or_404(Category,slug=category_slug)
        subcategory_id = category.subcategories.values('id')
        products = products.filter(Q(category=category) | Q(category_id__in=subcategory_id))
    sort_options = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'price_asc': 'price',
        'price_desc': '-price',
        'name_asc': 'name',
        'name_desc': '-name',
    }
    current_sort = request.GET.get('sort', 'newest')
    products = products.order_by(sort_options.get(current_sort, '-created_at'))

    paginator = Paginator(products, settings.PAGE_ITEMS)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'category': category,
        'categories': categories,
        'current_sort': current_sort,
        'page_obj': page_obj
    }
    return render(request, 'products/category_products.html', context)

def quick_view(request, product_id):
    product = get_object_or_404(Product.objects.select_related('category').prefetch_related('images','reviews'),
                                id=product_id, is_active=True)
    return render(request, 'includes/quick_view.html',{'product':product})

def search_engine_view(request):
    query = request.GET.get('query', '').strip()
    products = Product.objects.none()
    if query:
        products = Product.objects.filter(
            is_active=True).filter(
            Q(name__icontains=query) | Q(description__icontains=query) | Q(category__name__icontains=query)
        ).select_related('category').prefetch_related('images').distinct()

    paginator = Paginator(products, settings.PAGE_ITEMS)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'query': query,
        'page_obj': page_obj,
    }
    return render(request, 'products/search_results.html', context)

@login_required
def review_edit_view(request, review_id):
    review = get_object_or_404(ProductReview, id=review_id, user=request.user)
    if request.method == 'POST':
        form = ProductReviewForm(request.POST, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.is_published = False
            review.is_rejected = False
            review.save()
            notify_staff(type=Notification.Type.NEW_REVIEW,
                         message=f'Редактиран коментар от {request.user.get_full_name()} за продукт {review.product}.',
                         link=reverse('staff:staff_approve_review', args=[review.id]),
                         exclude_user=request.user,)
            messages.success(request, 'Отзивът е обновен и изчаква одобрение от нашия екип.')
            return redirect('products:product_detail', category_slug=review.product.category.slug, slug=review.product.slug)
    else:
        form = ProductReviewForm(instance=review)
    return render(request,'products/review_edit.html',{'review':review,'form':form})

@login_required
def my_courses_view(request):
    purchased_product_ids = OrderItem.objects.filter(
        order__user=request.user,
        order__status__in=(Order.OrderStatus.PAID, Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED),
    ).values_list('product_id', flat=True)
    # course should be visible immediately after being paid
    courses = VideoCourse.objects.filter(product_id__in=purchased_product_ids).select_related('product')
    paginator = Paginator(courses, settings.PAGE_ITEMS)
    page_obj = paginator.get_page(request.GET.get('page'))
    context = {
        'courses': courses,
        'page_obj': page_obj,
    }
    return render(request, 'products/my_courses.html',context)

@login_required
def course_watch_view(request, course_id):
    course = get_object_or_404(VideoCourse.objects.select_related('product'), id=course_id)
    has_access = OrderItem.objects.filter(
        order__user=request.user,
        product=course.product,
        order__status__in=(Order.OrderStatus.PAID, Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED),
    ).exists()
    if not has_access:
        messages.error(request, 'Нямате достъп до този курс.')
        return redirect('products:my_courses')
    return render(request, 'products/course_watch.html', {'course': course})
