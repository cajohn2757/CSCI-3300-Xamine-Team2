from xamine.models import AppSetting
from xamine.models import Order, Patient, Image, OrderKey, MedicationOrder, ModalityOption, MaterialOrder, Balance, Transaction
from django.db.models import F
import os


def get_setting(name, default=None):
    """ Get the setting from the database """

    # We look for the provided setting.
    # If it's not found, we return the default, if given.
    # If not, we return None
    try:
        return AppSetting.objects.get(name=name).value
    except AppSetting.DoesNotExist:
        return default


def is_in_group(user, group):
    """ Check if the supplied user is in the group list """

    # If we're provided a single group name, convert it to a list.
    # This allows us to pass both a single group and a list to check against.
    if isinstance(group, str):
        group = [group]

    return user.groups.filter(name__in=group).exists()


def get_image_files(images):
    # List of thumbanilable extensions
    thumbnail_exts = ['jpg', 'png', 'bmp']

    # For each image whose type is listed above, add to our thumbnail list
    thumbnails = []
    for image in images:
        ext = image.image.path.split('.')[-1]
        if ext.lower() in thumbnail_exts:
            thumbnails.append(image)

    # Return thumbnail list established above
    return thumbnails


def get_order_cost(order_num):
    """Takes an order num as its parameters and returns information about costs of the order"""
    # Setup empty lists and get the order modality to pull from the modality table
    modality_info, medication_info, materials_info = [], [], []
    order_modality = Order.objects.values_list('modality_id').get(pk = order_num)[0]

    # Get information from other models relating to the order and the needed values.
    # try/except in case they do not exist.
    try:
        # Cost of modality to variable
        modality_info = ModalityOption.objects.values_list('name', 'price').get(pk = order_modality)
    except ModalityOption.DoesNotExist:
        pass
    try:
        medication_info = MedicationOrder.objects.values_list('name', 'quantity', 'billed', 'price').get(order_id = order_num)
    except MedicationOrder.DoesNotExist:
        pass
    try:
        materials_info = MaterialOrder.objects.values_list('material', 'quantity', 'billed', 'price').get(order_id = order_num)
    except MaterialOrder.DoesNotExist:
        pass

    # Get a preemptive total cost of the order from the information that was just pulled
    sub = 0
    try:
        sub += modality_info[1]
    except:
        pass
    try:
        sub += materials_info[3]
    except:
        pass
    try:
        sub += medication_info[3]
    except:
        pass
    # Setup the list to return
    totals_info =[modality_info, medication_info, materials_info, sub]


    return totals_info # totals info list

def update_balance(patientid):
    """Calls get_order_cost for all orders of a patient and updates database"""

    # Check and see if the patient has a record in the Balance database,
    # if not then make an entry in the database for that patient
    try:
        check = Balance.objects.values_list('totalBalance').get(patient_id=patientid)[0]
    except Balance.DoesNotExist:
        temp = Balance(patient_id=patientid)
        temp.save()
    # Setup a running cost for all orders that are being checked
    running_cost = 0
    # Get all orders of a patient
    order_list = Order.objects.values_list('id', 'modality_id', 'modality_billed').filter(patient_id=patientid)
    # Go through all orders of a patient and add costs of med/mat orders and modality to cost
    # Once billed the 'billed' section is set to 1, and saved back into the database
    # Med order and mat order in try/except as they might not exist
    for x in order_list:
        info = get_order_cost(x[0])
        try:
            if x[2] == 0: # Modality
                running_cost += info[0][1] # Checks billed value
                order_row = Order.objects.get(pk=x[0])
                order_row.modality_billed = F('modality_billed') + 1
                order_row.save()
            try:
                if info[1][2] == 0: # Medication
                    running_cost += info[1][3] # Checks billed value
                    medication_row = MedicationOrder.objects.get(order=x[0])
                    medication_row.billed = F('billed') + 1
                    medication_row.save()
            except:
                pass
            try:
                if info[2][2] == 0: # Materials
                    running_cost += info[2][3] # Checks billed value
                    material_row = MaterialOrder.objects.get(order=x[0])
                    material_row.billed = F('billed') + 1
                    material_row.save()
            except:
                pass
        except:
            pass

    # Update the patients Balance database with the new value
    balancerow = Balance.objects.get(patient_id=patientid)
    balancerow.totalBalance = F('totalBalance') + running_cost
    balancerow.save()
    return


def load_init_vals():
    """Simple function that loads all initial data"""
    # Currently setup to run in a migration
    os.system('cmd /c "python manage.py loaddata initial-data.json"')


def finalize_bill(patientid):
    """ Queries all orders that belong to a patient and calculates how much the Insurance is co-paying for modalities"""
    # Gets all orders of a patient and then runs update_balance on that patient
    check_orders = Order.objects.values_list('id', 'finished_bill', 'modality').filter(patient_id=patientid)
    update_balance(patientid)
    # Set an empty array to values to depending on the modality and setup base for insurance paying
    modality_list = [0, 0, 0]
    Ins_Paid = 0
    # Goes through all orders of a patient and updates modality_list
    for x in check_orders:
        if x[1] == 0:
            if x[2] == 1:
                modality_list[0] += 1
            if x[2] == 2:
                modality_list[1] += 1
            if x[2] == 3:
                modality_list[2] += 1
            # Set an order to be finished, and then get the amount the insurance companies pay for this order
            finishedrow = Order.objects.get(pk=x[0])
            finishedrow.finished_bill = F('finished_bill') + 1
            finishedrow.save()
            Ins_Paid = get_order_cost(x[0])[3] - ((modality_list[0] * 100) + (modality_list[1] * 75) + ( modality_list[2] * 200))
    # Update All transactions of a patient and then update the amount the insurance company pays
    update_transactions(patientid)
    total_balance = Balance.objects.values_list('totalBalance').get(patient_id=patientid)[0]
    amountInsrow = Balance.objects.get(patient_id=patientid)
    amountInsrow.amount_Ins_Paid = F('amount_Ins_Paid') + Ins_Paid
    amountInsrow.save()


def get_invoice(patientid):
    """Gets the Invoice of an order"""
    # Gets all orders of a patient
    check_orders = Order.objects.values_list('id').filter(patient_id=patientid)[0]
    # Setup an empty dict for the invoice and remove the billed values from the invoice before return
    invoice = dict()
    for x in check_orders:
        info = get_order_cost(x)
        info[1].pop('billed')
        info[2].pop('billed')
        invoice[x] = info
    return invoice

def update_transactions(patientid):
    """Gets all transactions of a patients and updates it in the Balance database"""

    # Pulls all of a patients transactions
    transaction_list = Transaction.objects.values_list('id', 'amount', 'billed').filter(patient_id=patientid)

    # Goes through all transactions, updates the Balance table, and sets that transaction to billed
    for x in transaction_list:
        if(x[2] == 0):
            patient_paying = Balance.objects.get(pk=patientid)
            patient_paying.amount_Pat_Paid = F('amount_Pat_Paid') + x[1]
            patient_paying.save()
            billed_pay = Transaction.objects.get(pk=x[0])
            billed_pay.billed = F('billed') + 1
            billed_pay.save()

