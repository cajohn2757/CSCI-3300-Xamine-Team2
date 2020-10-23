from xamine.models import AppSetting
from xamine.models import Order, Patient, Image, OrderKey, MedicationOrder, ModalityOption, MaterialOrder, Balance
from django.db.models import F

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
    running_order_cost = 0
    cur_order = Order.objects.filter(pk=order_num)
    # Check if we have a POST request
    modality_info, medication_info, materials_info = [], [], []
    order_modality = Order.objects.values_list('modality_id').get(pk = order_num)[0]
    try:
        modality_info = ModalityOption.objects.values_list('name', 'price').get(pk = order_modality) #cost of modality to variable
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
    totals_info =(modality_info, medication_info, materials_info)


    # Still need to setup context and reference .html document

    return totals_info # totals info list

def update_balance(patientid):
    """Calls get_order_cost for all orders of a patient and updates database"""
   # if request.method == 'POST':
    try:
        initial_cost = Balance.objects.values_list('totalBalance').get(patient=patientid)
        running_cost = 0
        order_list =  Order.objects.values_list('id', 'modality_id', 'modality_billed').filter(patient_id = patientid)
        totalinfo = []
        for x in order_list:
            info = get_order_cost(x[0])
            print(info)
            if x[2] == 0: # Modality
                running_cost += info[0][1]
                order_row = Order.objects.get(pk = x[0])
                order_row.modality_billed = F('modality_billed') + 1
                order_row.save()
            try:
                if info[1][2] == 0: # Medication
                    running_cost += info[1][3]
                    medication_row = MedicationOrder.objects.get(order = x[0])
                    medication_row.billed = F('billed') + 1
                    medication_row.save()
            except:
                pass
            try:
                if info[2][2] == 0: # Materials
                    running_cost += info[2][3]
                    material_row = MaterialOrder.objects.get(order = x[0])
                    material_row.billed = F('billed') + 1
                    material_row.save()
            except:
                pass



            # totalinfo.append(info)
    except Balance.DoesNotExist:
        return "no" #fill balance database
