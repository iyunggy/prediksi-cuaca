from django.shortcuts import render

# Create your views here.

def sunshine_control_view(request):
    # Logika backend Anda di sini
    
    context = {
        'active_tab': 'sunshine' # Ini kuncinya agar sidebar 'Sunshine' menyala biru
    }
    return render(request, 'sunshine.html', context)