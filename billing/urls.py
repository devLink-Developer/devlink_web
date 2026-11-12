from django.urls import path
from . import views

app_name = 'billing'
urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('settings/', views.fiscal_settings, name='settings'),
    path('settings/<int:configuration_id>/check/', views.diagnostics, name='diagnostics'),
    path('customers/', views.customers, name='customers'),
    path('customers/new/', views.customer_form, name='customer_new'),
    path('customers/<int:customer_id>/', views.customer_form, name='customer_edit'),
    path('cancellations/', views.cancellations, name='cancellations'),
    path('cancellations/<uuid:invoice_id>/partial/', views.cancellation_partial, name='cancellation_partial'),
    path('new/', views.invoice_form, name='new'),
    path('<uuid:invoice_id>/', views.detail, name='detail'),
    path('<uuid:invoice_id>/edit/', views.invoice_form, name='edit'),
    path('<uuid:invoice_id>/issue/', views.issue, name='issue'),
    path('<uuid:invoice_id>/reconcile/', views.reconcile, name='reconcile'),
    path('<uuid:invoice_id>/credit-note/', views.credit_note, name='credit_note'),
    path('<uuid:invoice_id>/discard-credit/', views.credit_discard, name='credit_discard'),
    path('<uuid:invoice_id>/pdf/', views.pdf, name='pdf'),
]
