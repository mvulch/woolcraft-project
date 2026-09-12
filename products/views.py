from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from .models import Product, Category, ProductReview, ProductReviewImage, VideoCourse, Lesson, LessonProgress, CourseQuestion
from django.core.paginator import Paginator
from orders.models import Cart, Order, OrderItem
from .forms import ProductReviewForm, CourseQuestionForm, CourseQuestionReplyForm
from staff.utils import notify_staff
from django.contrib import messages
from staff.models import Notification
from accounts.utils import notify_user
from accounts.models import UserNotification
from communication.models import Article
from django.contrib.auth.decorators import login_required
from django.conf import settings


MONTH_TO_SEASON = {
    12: Product.Season.WINTER, 1: Product.Season.WINTER, 2: Product.Season.WINTER,
    3: Product.Season.SPRING, 4: Product.Season.SPRING, 5: Product.Season.SPRING,
    6: Product.Season.SUMMER, 7: Product.Season.SUMMER, 8: Product.Season.SUMMER,
    9: Product.Season.AUTUMN, 10: Product.Season.AUTUMN, 11: Product.Season.AUTUMN,
}

# Create your views here.
def home_view(request):
    latest_products = Product.objects.filter(is_active=True).order_by('-created_at').prefetch_related('images')[:8]
    recommended_articles = Article.objects.filter(is_published=True).order_by('-created_at').prefetch_related('images')[:4]
    current_season = MONTH_TO_SEASON[timezone.now().month]
    seasonal_products = Product.objects.filter(
        is_active=True, season__in=[current_season]
    ).order_by('-created_at').prefetch_related('images')[:4]
    return render(request, 'home.html', {
        'latest_products': latest_products,
        'recommended_articles': recommended_articles,
        'seasonal_products': seasonal_products,
        'current_season_label': Product.Season(current_season).label,
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
            review_form = ProductReviewForm(request.POST, request.FILES)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.user = request.user
                review.product = product_detail
                review.save()
                for image in review_form.cleaned_data.get('images', []):
                    ProductReviewImage.objects.create(review=review, image=image)
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
    preview_lesson = None
    if hasattr(product_detail, 'video_course'):
        if request.user.is_authenticated:
            has_video_access = OrderItem.objects.filter(
                order__user=request.user,
                product=product_detail,
                order__status__in=(Order.OrderStatus.PAID, Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED,),
            ).exists()
        if not has_video_access:
            preview_lesson = product_detail.video_course.lessons.filter(is_free_preview=True).first()
    context = {
        'product': product_detail,
        'max_quantity': product_detail.stock_quantity - quantity_in_cart,
        'reviews': reviews,
        'review_form': review_form,
        'can_review': can_review,
        'existing_review': existing_review,
        'has_video_access': has_video_access,
        'preview_lesson': preview_lesson,
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

    current_season = request.GET.get('season', '')
    if current_season in Product.Season.values:
        products = products.filter(season=current_season)
    else:
        current_season = ''

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
        'current_season': current_season,
        'season_choices': Product.Season.choices,
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
        form = ProductReviewForm(request.POST, request.FILES, instance=review)
        if form.is_valid():
            review = form.save(commit=False)
            review.is_published = False
            review.is_rejected = False
            review.save()
            for image in form.cleaned_data.get('images', []):
                ProductReviewImage.objects.create(review=review, image=image)
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
    courses = VideoCourse.objects.filter(product_id__in=purchased_product_ids).select_related('product').prefetch_related('lessons')
    paginator = Paginator(courses, settings.PAGE_ITEMS)
    page_obj = paginator.get_page(request.GET.get('page'))
    for course in page_obj:
        course.completed_lessons, course.total_lessons = course.get_progress_for_user(request.user)
    context = {
        'courses': courses,
        'page_obj': page_obj,
    }
    return render(request, 'products/my_courses.html',context)

def _submit_course_question(request, current_lesson):
    """handles the ask question action -> returns (form, was_created)"""
    if not (request.method == 'POST' and 'question_submit' in request.POST):
        return CourseQuestionForm(), False
    form = CourseQuestionForm(request.POST, request.FILES)
    if not form.is_valid():
        return form, False
    question = form.save(commit=False)
    question.lesson = current_lesson
    question.user = request.user
    question.save()
    notify_staff(
        type=Notification.Type.NEW_COURSE_QUESTION,
        message=f'Нов въпрос от {request.user.get_full_name()} към урок "{current_lesson.title}".',
        link=current_lesson.get_url(),
        exclude_user=request.user,
        superusers_only=True,
    )
    messages.success(request, 'Въпросът е изпратен.')
    return form, True


def _submit_course_question_reply(request, current_lesson):
    """handles the reply question action -> returns (form, was_created)"""
    if not (request.method == 'POST' and 'reply_submit' in request.POST):
        return CourseQuestionReplyForm(), False
    question = get_object_or_404(CourseQuestion, id=request.POST.get('question_id'), lesson=current_lesson)
    form = CourseQuestionReplyForm(request.POST, request.FILES)
    if not form.is_valid():
        return form, False
    reply = form.save(commit=False)
    reply.question = question
    reply.user = request.user
    reply.save()
    notify_user(
        user=question.user,
        type=UserNotification.Type.COURSE_QUESTION_REPLY,
        message=f'Получихте отговор на въпроса си към урок "{current_lesson.title}".',
        link=current_lesson.get_url(),
    )
    messages.success(request, 'Отговорът е публикуван.')
    return form, True


def _submit_lesson_complete(request, current_lesson):
    """handles the complete lesson action -> returns if it was marked complete"""
    if not (request.method == 'POST' and 'complete_submit' in request.POST):
        return False
    LessonProgress.objects.update_or_create(
        user=request.user, lesson=current_lesson,
        defaults={'is_completed': True, 'completed_at': timezone.now()},
    )
    messages.success(request, 'Урокът е отбелязан като завършен.')
    return True


def course_watch_view(request, course_id, lesson_id=None):
    course = get_object_or_404(VideoCourse.objects.select_related('product').prefetch_related('lessons'), id=course_id)
    lessons = list(course.lessons.all())
    if lesson_id:
        current_lesson = get_object_or_404(course.lessons, id=lesson_id)
    else:
        current_lesson = lessons[0] if lessons else None

    has_access = request.user.is_authenticated and (
        request.user.is_staff or OrderItem.objects.filter(
            order__user=request.user,
            product=course.product,
            order__status__in=(Order.OrderStatus.PAID, Order.OrderStatus.SHIPPED, Order.OrderStatus.DELIVERED),
        ).exists()
    )

    if not has_access and not (current_lesson and current_lesson.is_free_preview):
        if not request.user.is_authenticated:
            messages.info(request, 'Влезте в профила си, за да гледате този урок.')
            return redirect('accounts:login')
        messages.error(request, 'Нямате достъп до този урок.')
        return redirect('products:my_courses')

    if current_lesson is None:
        messages.info(request, 'Курсът все още няма добавени уроци.')
        return render(request, 'products/course_watch.html', {'course': course, 'lessons': lessons, 'current_lesson': None})

    redirect_url = reverse('products:course_watch_lesson', args=[course.id, current_lesson.id])

    question_form = None
    if has_access:
        question_form, created = _submit_course_question(request, current_lesson)
        if created:
            return redirect(redirect_url)

    reply_form = None
    if request.user.is_superuser:
        reply_form, created = _submit_course_question_reply(request, current_lesson)
        if created:
            return redirect(redirect_url)

    if has_access and _submit_lesson_complete(request, current_lesson):
        return redirect(redirect_url)

    completed_lesson_ids = set()
    if has_access:
        completed_lesson_ids = set(LessonProgress.objects.filter(
            user=request.user, lesson__course=course, is_completed=True
        ).values_list('lesson_id', flat=True))

    questions = []
    if has_access:
        questions = current_lesson.questions.select_related('user').prefetch_related('replies__user').order_by('-created_at')

    context = {
        'course': course,
        'lessons': lessons,
        'current_lesson': current_lesson,
        'has_access': has_access,
        'completed_lesson_ids': completed_lesson_ids,
        'is_current_completed': current_lesson.id in completed_lesson_ids,
        'questions': questions,
        'question_form': question_form,
        'reply_form': reply_form,
    }
    return render(request, 'products/course_watch.html', context)
