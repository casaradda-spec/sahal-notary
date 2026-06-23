from django.urls import path

from accounts.decorators import role_required
from accounts.models import User

from . import views_admin, views_client, views_notary, views_public
from .wizard import CreateDocumentWizard

urlpatterns = [
    path('', views_public.home_redirect, name='home'),

    path('app/', views_client.dashboard, name='client_dashboard'),
    path('app/documents/<str:ref>/pdf/', views_client.document_pdf, name='client_document_pdf'),

    path('notary/', views_notary.overview, name='notary_overview'),
    path('notary/templates/', views_notary.template_list, name='notary_templates'),
    path('notary/templates/new/', views_notary.template_new, name='notary_template_new'),
    path('notary/templates/<int:pk>/edit/', views_notary.template_edit, name='notary_template_edit'),
    path('notary/templates/<int:pk>/delete/', views_notary.template_delete, name='notary_template_delete'),
    path(
        'notary/create/',
        role_required(User.Role.NOTARY, User.Role.ADMIN)(CreateDocumentWizard.as_view()),
        name='notary_create',
    ),
    path('notary/create/success/<str:ref>/', views_notary.create_success, name='notary_create_success'),
    path('notary/documents/', views_notary.all_documents, name='notary_documents'),
    path('notary/documents/<str:ref>/pdf/', views_notary.document_pdf, name='notary_document_pdf'),
    path('notary/documents/<str:ref>/complete/', views_notary.document_complete, name='notary_document_complete'),
    path('notary/documents/<str:ref>/edit/', views_notary.document_edit, name='notary_document_edit'),
    path('notary/documents/<str:ref>/', views_notary.document_detail, name='notary_document_detail'),
    path('notary/profile/', views_notary.profile, name='notary_profile'),

    path('admin-panel/clients/', views_admin.clients_view, name='admin_clients'),
    path('admin-panel/clients/<int:pk>/edit/', views_admin.client_edit, name='admin_client_edit'),
    path('admin-panel/clients/<int:pk>/delete/', views_admin.client_delete, name='admin_client_delete'),
    path('admin-panel/clients/<int:pk>/signature/', views_admin.client_signature, name='admin_client_signature'),
    path('admin-panel/notaries/', views_admin.notaries_view, name='admin_notaries'),
    path('admin-panel/notaries/<int:pk>/edit/', views_admin.notary_edit, name='admin_notary_edit'),
    path('admin-panel/notaries/<int:pk>/delete/', views_admin.notary_delete, name='admin_notary_delete'),
    path('admin-panel/reports/', views_admin.reports, name='admin_reports'),

    path('verify/<uuid:qr_token>/', views_public.verify, name='verify'),
    path('verify/<uuid:qr_token>/qr.png', views_public.qr_image, name='qr_image'),
]
