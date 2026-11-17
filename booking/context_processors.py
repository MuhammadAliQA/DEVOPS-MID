from .translations import catalog


def customer_ui(request):
    return {'ui_copy': catalog()}
