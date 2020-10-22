from xamine.models import AppSetting
from xamine.models import Order, Patient, Image, OrderKey, MedicationOrder, ModalityOption, MaterialOrder, Balance

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
    cur_order = Order.objects.get(pk=order_num)
    # Check if we have a POST request

    order_modality = Order.objects.values_list('modality_id').get(pk = order_num)[0]
    modality_info = ModalityOption.objects.values_list('name', 'price').get(pk = order_modality) #cost of modality to variable
    medication_info = MedicationOrder.objects.values_list('name', 'quantity', 'price').get(order_id = order_num)
    materials_info = MaterialOrder.objects.values_list('name', 'price').get(order_id = order_num)
    totals_info =(modality_info, medication_info, materials_info)


    # Still need to setup context and reference .html document

    return totals_info # totals info list

def update_balance(patientid):

   # if request.method == 'POST':
    try:
        initial_cost = Balance.objects.values_list('totalBalance').get(patient=patientid)
        order_list =  Order.objects.values_list('id', 'modality_id').filter(patient_id = patientid)
        for x in order_list.count():
            print(order_list[0])
    except Balance.DoesNotExist:
        return "no" #fill balance database
