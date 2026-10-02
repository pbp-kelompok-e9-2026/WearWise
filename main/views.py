from django.shortcuts import render

# Create your views here.

def show_main(request):
    context = {
        'app_name': 'WearWise',
        'name': request.user.username if request.user.is_authenticated else 'Pengunjung',
    }
    return render(request, "index.html", context)
