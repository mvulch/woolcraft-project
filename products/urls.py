from django.urls import path
from .views import product_detail_view, category_products_view, quick_view, search_engine_view, review_edit_view, my_courses_view, course_watch_view

app_name = 'products'
urlpatterns = [
    path('',  category_products_view, name='all_products'),
    path('quick-view/<int:product_id>/', quick_view, name='quick_view'),
    path('search', search_engine_view, name='search'),
    path('review/edit/<int:review_id>', review_edit_view, name='review_edit'),
    path('my-courses/', my_courses_view, name='my_courses'),
    path('my-courses/<int:course_id>/', course_watch_view, name='course_watch'),
    path('my-courses/<int:course_id>/lesson/<int:lesson_id>/', course_watch_view, name='course_watch_lesson'),
    path('<slug:category_slug>/<slug:slug>/', product_detail_view, name='product_detail'),
    path('<slug:category_slug>/', category_products_view, name='category_products'),


]