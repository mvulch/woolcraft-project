from django.urls import path
from .views import custom_request_create_view, custom_requests_list_view, custom_request_detail_view, custom_request_payment_view, custom_request_payment_success_view, custom_request_address_view, custom_request_info_view

app_name = 'custom_requests'
urlpatterns = [
    path('custom-request-info/', custom_request_info_view, name='custom_request_info'),
    path('custom-request-create',custom_request_create_view, name='custom_request_create'),
    path('custom-request-detail/<int:request_id>/', custom_request_detail_view, name='custom_request_detail'),
    path('custom-requests-list', custom_requests_list_view, name='custom_requests_list'),
    path('<int:request_id>/payment/', custom_request_payment_view, name='custom_request_payment'),
    path('payment-success/', custom_request_payment_success_view, name='custom_request_payment_success'),
    path('<int:request_id>/address/', custom_request_address_view, name='address'),
]