from django.urls import path, include, re_path

from xamine import views, apiviews

urlpatterns = [
    path('', views.index, name='index'),  # view dashboard

    path('order/', views.public_order, name='public_order'),  # Patient viewing of orders
    path('order/<int:order_id>/', views.order, name='order'),  # Internal viewing and submitting of orders
    path('order/<int:order_id>/upload', views.upload_file, name='submit_image'),  # Uploading images for order
    path('order/<int:order_id>/send', apiviews.patient_email, name='patient_view'),  # Send patient view email
    path('order/<int:order_id>/schedule', views.schedule_order, name='schedule_time'),  # Schedule our order
    path('order/<int:order_id>/save', views.save_order, name='save_order'),  # Save radiology report without finalizing.
    path('order/<int:order_id>/med-order', views.med_order, name='med_order'),  # Internal viewing and submitting of medication orders
    path('order/<int:order_id>/mat-order', views.mat_order, name='mat_order'),  # Internal viewing and submitting of material orders
    path('order/<int:order_id>/new-med-order', views.new_med_order, name='new_med_order'),  # Start new medication order
    path('order/<int:order_id>/new-mat-order', views.new_mat_order, name='new_mat_order'),  # Start new material order
    path('order/<int:order_id>/order-invoice', views.invoice, name='order_invoice'), # Internal viewing of invoice

    path('patient/<int:pat_id>/', views.patient, name='patient'),  # View patient info
    path('patient/', views.patient_lookup, name='patient_lookup'),  # lookup patients by DOB
    path('patient/new', views.new_patient, name='new_patient'),  # Submit new patient info
    path('patient/<int:pat_id>/new-order', views.new_order, name='new_order'),  # Start new order for patient
    path('patient/<int:pat_id>/new-transaction', views.new_transaction, name='new_transaction'),
    path('patient/<int:pat_id>/transaction/', views.transaction, name='transaction'),
    path('image/<int:img_id>/remove', views.remove_file, name='remove_image'),  # Remove specified image

]