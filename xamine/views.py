import datetime
from partial_date import PartialDate

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from xamine.models import Order, Patient, Image, OrderKey, MedicationOrder, ModalityOption, MaterialOrder, Balance, Transaction
from xamine.forms import ImageUploadForm
from xamine.forms import NewOrderForm, PatientLookupForm, MedicationOrderForm, MaterialOrderForm, TransactionForm
from xamine.forms import PatientInfoForm, ScheduleForm, TeamSelectionForm, AnalysisForm
from xamine.utils import is_in_group, get_image_files, get_order_cost, finalize_bill, update_balance, update_transactions
from xamine.tasks import send_notification


@login_required
def index(request):
    """ Displays dashboard tables, depending on group membership of logged in user. """

    # Determine if current user can see all sections
    see_all = is_in_group(request.user, "Administrators")

    # Set up empty context to pass to template
    context = {}

    # Check if administrator or physician
    if see_all or is_in_group(request.user, "Physicians"):
        # Grab active orders and completed orders from database
        active_orders = Order.objects.filter(level_id__lt=6)
        complete_orders = Order.objects.filter(level_id=6)

        # If we are not an administrator, limit active and complete orders to
        # the logged in users' patients.
        if not see_all:
            active_orders = active_orders.filter(patient__doctor=request.user)
            complete_orders = complete_orders.filter(patient__doctor=request.user)

        # Add the orders we grabbed to our template context
        context['active_orders'] = active_orders
        context['complete_orders'] = complete_orders

        # Add the patient lookup form to our context
        context['patient_lookup'] = PatientLookupForm()

    # Check if administrator or receptionist
    if see_all or is_in_group(request.user, "Receptionists"):
        # Find today's appts. To filter by today's appointments, we find the datetime for today at midnight,
        # and today at 11:59 PM. We then find all appts between those two ranges. Then we add it to the context.
        today_min = datetime.datetime.combine(datetime.date.today(), datetime.time.min)
        today_max = datetime.datetime.combine(datetime.date.today(), datetime.time.max)
        context['todays_orders'] = Order.objects.filter(level_id=1, appointment__range=(today_min, today_max))

        # Find unscheduled appointments
        context['unsched_orders'] = Order.objects.filter(level_id=1, appointment__isnull=True)

        # Find completed appointments for today
        context['complt_orders'] = Order.objects.filter(level_id=6, appointment__range=(today_min, today_max))

    # Check if administrator or technician
    if see_all or is_in_group(request.user, "Technicians"):
        # Pass into context all checked in orders for any team where the logged in user is a technician.
        context['checked_in_orders'] = Order.objects.filter(level_id=2, team__technicians=request.user)

    if see_all or is_in_group(request.user, "Radiologists"):
        # Pass into context all imaging complete orders for teams where logged in user is a radiologist.
        context['radiologist_orders'] = Order.objects.filter(level_id=5, team__radiologists=request.user)

    # Render the dashoboard with any context we've passed in.
    return render(request, 'index.html', context)


@login_required
def save_order(request, order_id):
    """ Saves radiology report but does not complete order """

    # Attempt to grab order via order_id from url. 404 if not found.
    try:
        cur_order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        raise Http404

    # Ensure request method is POST
    if request.method == 'POST':
        # Check if Order is at radiologist level and request user is a radiologist and is on the order's team.
        if cur_order.level_id == 5 and is_in_group(request.user, ['Radiologists']):
            if request.user in cur_order.team.radiologists.all():
                # Set up form with our data and save if valid
                form = AnalysisForm(data=request.POST, instance=cur_order)
                if form.is_valid():
                    form.save()

    # Always redirect to specified order
    return redirect('order', order_id=order_id)
    

@login_required
def upload_file(request, order_id):
    """ Uploads file to specified order """

    # Check if we have a POST request
    if request.method == 'POST':
        # Create a malleable copy of our POST data, add the order id to it.
        data = request.POST.copy()
        data['order'] = order_id

        # Check if our form is valid
        form = ImageUploadForm(data, request.FILES)
        if form.is_valid():
            # File is saved
            new_image = form.save()

            # Record who uploaded the file
            new_image.user = request.user.get_username()
            new_image.save()

    # Regardless of the result of our post request, reload order page
    return redirect('order', order_id=order_id)


@login_required
def order(request, order_id):

    # Attempt to grab order via order_id from url. 404 if not found.
    try:
        cur_order = Order.objects.get(pk=order_id)
    except Order.DoesNotExist:
        raise Http404

    # Check if we have a POST request
    if request.method == 'POST':

        # Check if level and permissions for the logged in user are both receptionists or admins
        if cur_order.level_id == 1 and is_in_group(request.user, ['Receptionists', 'Administrators']):

            # Assign POST data to selection form, check if it's valid, and save if so
            form = TeamSelectionForm(data=request.POST, instance=cur_order)
            if form.is_valid():
                form.save()
            else:
                # Show errors
                messages = {
                    'headline1': 'Invalid Form',
                    'headline2': 'Please try again.',
                    'headline3': f"{form.errors}"
                }
                return show_message(request, messages)

        # Check if level and permissions for the logged in user are both technicians
        elif cur_order.level_id == 2 and is_in_group(request.user, ['Technicians', 'Radiologists']):
            if request.user in cur_order.team.technicians.all() | cur_order.team.technicians.all():
                # Save image complete info
                cur_order.imaged = request.user.get_username()
                cur_order.imaged_time = timezone.now()
                cur_order.save()
            else:
                # Show auth error
                messages = {
                    'headline1': 'Not Authorized',
                    'headline2': '',
                    'headline3': '',
                }
                return show_message(request, messages)

        elif cur_order.level_id == 3 and is_in_group(request.user, ['Technicians', 'Radiologists','Physicians']):
            if request.user in cur_order.team.technicians.all() | cur_order.team.technicians.all():
                # Save order with med order info
                cur_order.save()
            else:
                # Show auth error
                messages = {
                    'headline1': 'Not Authorized',
                    'headline2': '',
                    'headline3': '',
                }
                return show_message(request, messages)

        elif cur_order.level_id == 4 and is_in_group(request.user, ['Technicians', 'Radiologists','Physicians']):
            if request.user in cur_order.team.technicians.all() | cur_order.team.technicians.all():
                # Save order with med order info
                cur_order.save()
            else:
                # Show auth error
                messages = {
                    'headline1': 'Not Authorized',
                    'headline2': '',
                    'headline3': '',
                }
                return show_message(request, messages)

        # Check if level and permissions for the logged in user are both radiology
        elif cur_order.level_id == 5 and is_in_group(request.user, ['Radiologists']):
            if request.user in cur_order.team.radiologists.all():
                # Set up data in our form and check validity of data.
                form = AnalysisForm(data=request.POST, instance=cur_order)
                if form.is_valid():

                    # Save form, then grab saved item
                    form.save()
                    cur_order.refresh_from_db()

                    # Add completed user and completed time to record, then save
                    cur_order.completed = request.user.get_username()
                    cur_order.completed_time = timezone.now()
                    cur_order.save()

                else:
                    # Show form errors
                    messages = {
                        'headline1': 'Invalid Form',
                        'headline2': 'Please try again.',
                        'headline3': f"{form.errors}"
                    }
                    return show_message(request, messages)
            else:
                # Show auth error
                messages = {
                    'headline1': 'Not Authorized',
                    'headline2': '',
                    'headline3': '',
                }
                return show_message(request, messages)
        else:
            # Show invalid request error
            messages = {
                'headline1': 'Order already complete.',
                'headline2': '',
                'headline3': '',
            }
            return show_message(request, messages)

        # If we've made it to there, that means we've successfully submitted the order.
        # Therefore, we'll re-grab it from the DB and increment it's level by one.
        cur_order.refresh_from_db()
        cur_order.level_id += 1
        cur_order.save()

        # Send an email notification to the correct user(s)
        #send_notification.now(order_id)

    # Set up the variables for our template
    context = {
        'cur_order': cur_order,
    }

    # Check for user permission and level order. Add appropriate elements for template rendering.
    if cur_order.level_id == 1 and is_in_group(request.user, ['Receptionists', 'Administrators']):
        # Add scheduler form if not yet checked in
        context['schedule_form'] = ScheduleForm(instance=cur_order)
        context['checkin_form'] = TeamSelectionForm(instance=cur_order)
    elif cur_order.level_id == 2 and is_in_group(request.user, ['Technicians', 'Radiologists']):
        # Prepare context for template if at checked in step
        if request.user in cur_order.team.radiologists.all() | cur_order.team.technicians.all():
            context['image_form'] = ImageUploadForm(instance=cur_order)
    elif cur_order.level_id == 3 and is_in_group(request.user, ['Technicians', 'Radiologists','Physicians']):
        # Prepare context for template if at imaging complete step
        if request.user in cur_order.team.radiologists.all() | cur_order.team.technicians.all():
            context['mat_form'] = MaterialOrderForm(instance=cur_order)
    elif cur_order.level_id == 4 and is_in_group(request.user, ['Technicians', 'Radiologists','Physicians']):
        # Prepare context for template if at imaging complete step
        if request.user in cur_order.team.radiologists.all() | cur_order.team.technicians.all():
            context['med_form'] = MedicationOrderForm(instance=cur_order)
    elif cur_order.level_id == 5 and is_in_group(request.user, ['Radiologists']):
        # Prepare context for template if at medication and material order step
        if request.user in cur_order.team.radiologists.all():
            context['analysis_form'] = AnalysisForm(instance=cur_order)
    elif cur_order.level_id == 6:
        # Prepare context for template if at analysis complete step
        pass
    elif cur_order.level_id == 7:
        # Prepare context for template if archived
        pass

    # Define which user groups can see medical info, add to context
    medical_groups = ['Technicians', 'Radiologists', 'Physicians']
    context['show_medical'] = is_in_group(request.user, medical_groups)
    context['sub_cost'] = get_order_cost(order_id)[3]
    # Send thumbnails into context and render HTML
    context['thumbnails'] = get_image_files(cur_order.images.all())
    return render(request, 'order.html', context)



@login_required
def patient(request, pat_id=None):
    """ Displays the patient info and orders """

    # Grab patient from the database
    patient_rec = Patient.objects.get(pk=pat_id)

    # Check if it is a post request. If so, build our form with the post data.
    if request.method == 'POST':
        form = PatientInfoForm(data=request.POST, instance=patient_rec)

        # Ensure form is valid. If so, save. If not, show error.
        if form.is_valid():
            form.save()
        else:
            messages = {
                'headline1': 'Invalid Form',
                'headline2': 'Please try again.',
                'headline3': f"{form.errors}"
            }
            return show_message(request, messages)

    # Set up variables for our template and render it

    finalize_bill(pat_id)
    context = {
        'patient_info': patient_rec,
        'form': PatientInfoForm(instance=patient_rec),
        'active_orders': patient_rec.orders.filter(level_id__lt=6),
        'complete_orders': patient_rec.orders.filter(level_id__gte=6),
        'transactions': Transaction.objects.filter(patient_id=pat_id),
        'amount_due': Balance.get_patient_paying(pat_id),
    }
    context['transaction_form'] = TransactionForm(instance=patient_rec)
    return render(request, 'patient.html', context)


@login_required
def schedule_order(request, order_id):
    """ Schedules our appointment if available """

    # Check if this is a post request
    if request.method == 'POST':

        # Grab our requested order from the DB
        order = Order.objects.get(pk=order_id)

        # If we have an appointment key in our post data, check if there are appointments within two hours.
        if request.POST['appointment']:
            appt = datetime.datetime.strptime(request.POST['appointment'], '%Y-%m-%d %I:%M %p')
            twohrslater = appt + datetime.timedelta(hours=2)

            if appt.date() < datetime.date.today():
                messages = {
                    'headline1': 'Appointment is in the past.',
                    'headline2': '',
                    'headline3': f"Orders can only be assigned to today or in the future."
                }
                return show_message(request, messages)

            conflict = Order.objects.filter(appointment__gte=appt, appointment__lt=twohrslater).exists()
        else:
            # We did not get an appointment key in our POST data, so we're going to blank out our appt time.
            appt = None
            conflict = False

        # If there is a conflict, show an error. Otherwise, save our appt info.
        if conflict:
            messages = {
                'headline1': 'Appointment conflict',
                'headline2': 'Please try again.',
                'headline3': f""
            }
            return show_message(request, messages)
        else:
            order.appointment = appt
            order.save()

    # Alwyas redirect to the order
    return redirect('order', order_id=order_id)


@login_required
def patient_lookup(request):
    """ Handles patient lookup and order creation """

    # Grab a data object from our DateWidget
    dob = datetime.datetime.strptime(request.POST['birth_date'], '%Y-%m-%d').date()

    if dob > datetime.date.today():
        messages = {
            'headline1': 'Birth date must be in the past',
            'headline2': 'Please try again.',
            'headline3': f""
        }
        return show_message(request, messages)

    # Grab a list of patients with that DOB from DB
    patient_list = Patient.objects.filter(birth_date=dob)

    # Prepare empty lookup form
    new_form = PatientLookupForm(initial={'birth_date': dob})

    # prepare context for our page and then render it
    context = {
        'patient_list': patient_list,
        'date_selected': dob,
        'new_patient_form': PatientInfoForm(),
        'patient_lookup': new_form,
    }
    return render(request, 'patient_lookup.html', context)


@login_required
def new_patient(request):
    """ Handles creation of a new patient """

    # if not post request, redirect to 404
    if not request.method == 'POST':
        raise Http404

    # set up new patient request form with POST data
    new_form = PatientInfoForm(data=request.POST)

    # Check if form is valid. If so, assign doctor and save, the redir to a new order. Otherwise, show error.
    if new_form.is_valid():
        new_patient = new_form.save()

        new_patient.doctor_id = request.user.pk
        new_patient.save()

        return redirect('new_order', pat_id=new_patient.pk)

    else:
        context = {
            'patient_list': None,
            'date_selected': None,
            'new_patient_form': new_form,
            'show_modal': True,
        }
        return render(request, 'patient_lookup.html', context)


@login_required
def new_order(request, pat_id):
    """ Handles creation of a new order """

    # if not post request, redirect to 404
    if request.method == 'POST':
        # Copy form data and assign patient to order
        form_data = request.POST.copy()
        form_data['patient'] = pat_id

        # Set up form with our copied data
        new_form = NewOrderForm(data=form_data)

        # Check validity. If valid, save order and set workflow. Otherwise, reload page with errors.
        if new_form.is_valid():
            new_order = new_form.save()
            new_order.level_id = 1
            new_order.save()

            return redirect('order', order_id=new_order.pk)
    else:
        new_form = NewOrderForm()

    # Either we're reloading form with errors, or we didn't have a post request.
    # If it's not a post request, we'll load a blank form. Otherwise, load error form.
    context = {
        'new_order_form': new_form,
        'patient': Patient.objects.get(pk=pat_id),
    }
    return render(request, 'new_order.html', context)


@login_required
def remove_file(request, img_id):
    """ Removes image from our order model """

    # Grab image in question
    img = Image.objects.get(pk=img_id)

    # Check auth for deletion. If authorized, delete. Otherwise, show error.
    if request.user in img.order.team.technicians.all() | img.order.team.radiologists.all():
        img.delete()
    else:
        messages = {
            'headline1': 'Not authorized',
            'headline2': '',
            'headline3': f""
        }
        return show_message(request, messages)

    return redirect('order', order_id=img.order_id)


def public_order(request):
    """ Handles displaying order based on secret key """

    # Get secret key from GET parameters
    key = request.GET.get('key')

    # If there's no key, show 404
    if not key:
        raise Http404('bad key')

    # If we have a key, try to find a matching OrderKey and grab the corresponding order
    order_key = get_object_or_404(OrderKey, secret_key=key)
    cur_order = order_key.order

    # Prepare variables for template and display
    context = {
        "cur_order": cur_order,
        "thumbnails": get_image_files(cur_order.images.all()),
        'show_medical': True,
    }
    return render(request, 'order_pub.html', context)


@login_required
def show_message(request, headlines):
    """ Handles showing error messages """
    return render(request, 'message.html', headlines)

@login_required
def med_order(request, med_order_id=None, order_id=None):
    """ Displays the medication info and orders """

    # Grab medication order from the database
    cur_order = Order.objects.get(pk=order_id)
    medication_order_info = MedicationOrder.objects.get(pk=order_id)

    # Check if it is a post request. If so, build our form with the post data.
    if request.method == 'POST':
        form = MedicationOrderForm(data=request.POST, instance=medication_order_info)

        # Ensure form is valid. If so, save. If not, show error.
        if form.is_valid():
            form.save()
        else:
            messages = {
                'headline1': 'Invalid Form',
                'headline2': 'Please try again.',
                'headline3': f"{form.errors}"
            }
            return show_message(request, messages)

    # Set up variables for our template and render it
    context = {
        'medication_info': medication_order_info,
        'cur_order': cur_order,
        'med_form': MedicationOrderForm(instance=medication_order_info),
    }
    return render(request, 'med_order.html', context)


@login_required()
def new_med_order(request, order_id):
    """ Handles creation of a new medication order """

    # if not post request, redirect to 404
    if not request.method == 'POST':
        raise Http404

    cur_order = Order.objects.get(pk=order_id)
    # set up new patient request form with POST data
    new_form = MedicationOrderForm(data=request.POST)

    # Check if form is valid. If so, assign doctor and save, the redir to a new order. Otherwise, show error.
    if new_form.is_valid():
        new_medication_order = new_form.save()
        new_medication_order.order = cur_order
        cur_order.level_id = 5
        new_medication_order.save()
        cur_order.save()

        return redirect('order', order_id=cur_order.pk)

    else:
        context = {
            'new_medication_form': new_form,
            'show_modal': True,
            'order': cur_order,
        }
        return render(request, 'new_med_order.html', context)


def mat_order(request, order_id=None, mat_order_id=None):
    """ Displays the material info and orders """

    # Grab material order from the database
    cur_order = Order.objects.get(pk=order_id)
    material_order_info = MaterialOrder.objects.get(pk=order_id)

    # Check if it is a post request. If so, build our form with the post data.
    if request.method == 'POST':
        form = MaterialOrderForm(data=request.POST, instance=material_order_info)

        # Ensure form is valid. If so, save. If not, show error.
        if form.is_valid():
            form.save()
        else:
            messages = {
                'headline1': 'Invalid Form',
                'headline2': 'Please try again.',
                'headline3': f"{form.errors}"
            }
            return show_message(request, messages)

    # Set up variables for our template and render it
    context = {
        'material_info': material_order_info,
        'cur_order': cur_order,
        'mat_form': MaterialOrderForm(instance=material_order_info),
    }
    return render(request, 'mat_order.html', context)


@login_required()
def new_mat_order(request, order_id):
    """ Handles creation of a new material order """

    # if not post request, redirect to 404
    if not request.method == 'POST':
        raise Http404

    cur_order = Order.objects.get(pk=order_id)
    # set up new patient request form with POST data
    new_form = MaterialOrderForm(data=request.POST)

    # Check if form is valid. If so, assign doctor and save, the redir to a new order. Otherwise, show error.
    if new_form.is_valid():
        new_material_order = new_form.save()
        new_material_order.order = cur_order
        cur_order.level_id = 4
        new_material_order.save()
        cur_order.save()

        return redirect('order', order_id=cur_order.pk)

    else:
        context = {
            'new_material_form': new_form,
            'show_modal': True,
            'order': cur_order,
        }
        return render(request, 'new_mat_order.html', context)


@login_required()
def invoice(request, order_id=None):
    """View Invoice of the current order"""
    cur_order = Order.objects.get(pk=order_id)
    finalize_bill(cur_order.patient_id)
    invoice_info = get_order_cost(order_id)
    modality_info = {
        'name': invoice_info[0][0],
        'price': invoice_info[0][1]
    }
    context = {
        'modality_info': modality_info,
        'medication_info': MedicationOrder.objects.get(pk=order_id),
        'materials_info': MaterialOrder.objects.get(pk=order_id),
        'final_price': invoice_info[3],
        'cur_order': cur_order,
    }
    return render(request, 'order_invoice.html', context)


def new_transaction(request, pat_id):
    """Handles Creation of a transaction"""
    if not request.method == 'POST':
        raise Http404
    cur_patient = Patient.objects.get(pk=pat_id)

    new_form = TransactionForm(data=request.POST)

    if new_form.is_valid():
        new_transaction = new_form.save()
        new_transaction.patient = cur_patient
        new_transaction.save()
        return redirect('patient', pat_id=cur_patient.pk)

    else:
        context = {
            'new_transaction': new_form,
            'show_modal': True,
            'cur_patient': cur_patient,
        }
        return render(request, 'new_transaction.html', context)

def transaction(request, pat_id, transaction_id):
    cur_transaction = Transaction.objects.get(pk=transaction_id)
    cur_patient = Patient.objects.get(pk=pat_id)
    if request.method == 'POST':
        form = TransactionForm(data=request.POST, instance=cur_transaction)

        # Ensure form is valid. If so, save. If not, show error.
        if form.is_valid():
            form.save()
        else:
            messages = {
                'headline1': 'Invalid Form',
                'headline2': 'Please try again.',
                'headline3': f"{form.errors}"
            }
            return show_message(request, messages)

    context = {
        'transaction_info': cur_transaction,
        'transaction_form': TransactionForm(instance=cur_transaction),
        'cur_patient': cur_patient,
    }

    return render(request, 'transaction.html', context)