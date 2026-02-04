from django.shortcuts import render,redirect, get_object_or_404
from django.http import JsonResponse
from .models import * #attempting to import all models
from django.db.models import Q

from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from django.http import FileResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required

from dotenv import load_dotenv

import os
from django.conf import settings

import random, math, requests,json

from django.urls import reverse



import uuid, random, re, socket
from uuid import uuid4

from rave_python import Rave, Misc,RaveExceptions

load_dotenv()



#initialize environment variables


beat_id_global = 0 #will chnage it later, but we have added 0 as the default.



def download_beat(request, beat_id):
    """Hande beat download nd mark as downloaded"""
    beat = get_object_or_404(Beat, pk=beat_id)

    #check if user has purchased this beat
    has_purchased = Transaction.objects.filter(
        buyer= request.user.buyer_profile or "josh",
        beat=beat,
        status='completed'
    ).exists()

    if not has_purchased:
        return HttpResponseForbidden("You have not purchased this beat.")
    
    if not beat.is_downloaded:
        return HttpResponseForbidden("This beat is not marked as downloaded yet.")
    
    #Get the file path
    file_path = beat.audio_file.path

    if os.path.exists(file_path):
        #mark the beat as downloaded
        beat.mark_as_downloaded()


        #create downlaod record,
        #need to create a download record for it here.
        DownloadHistory.objects.create(
            buyer=request.user.buyer_profile,
            beat=beat,
            download_count=beat.download_count
        )

        #serve the file for download
        response = FileResponse(open(file_path, 'rb'))
        response['Content-Type'] = 'audio/mpeg'
        response['Content-Disposition'] = f'attachment; filename="{beat.title}.mp3"'
        return response
    else:
        return HttpResponseForbidden("File does not exist.")




#====process payment function====
#===i dont need to pass the beat id from here because i only intend to handle payments.
#===from here
def process_payment(request, name,email):
    auth_token = os.getenv('SECRET_TEST') #picking the secret key starting with test
    #===check if auth token is available
    if not auth_token:
        print("ERROR: SECRET_TEST environment variable is not set!")
        # You can raise an error or return a meaningful response
        raise ValueError("Flutterwave secret key not found in environment variables.")
    hed = {
        'Authorization':'Bearer ' + auth_token,
        'Content-Type':'application/json',
        'Accept': 'application/json'
    }
    phone='0706626855'

    url = ' https://api.flutterwave.com/v3/payments'
    data = json.dumps({
        "tx_ref":''+str(math.floor(1000000 + random.random()*9000000)),
        "amount":100,
        "currency":"USD",
        "redirect_url": "http://127.0.0.1:8000/main/callback",#(Note this url must be hosted)
        "payment_options":"mobilemoneyuganda,card",
        "meta":{
            "consumer_id":23,
            "consumer_mac":"92a3-912ba-1192a"
        },
        "customer":{
            "email":email,
            "phonenumber":phone,
            "name":name
        },
        "customizations":{
            "title":"Warren Beats",
            "description":"Classic Beats",
            "logo":"https://getbootstrap.com/docs/4.0/assets/brand/bootstrap-solid.svg"
        },
        #"subaccounts": [
        #    {
        #        "id": env('SUB_ID'),
        #    }
        #],
    })
    response = requests.request("POST",url, headers=hed,data=data)
    response = response.json()
    #response = response.text
    print(response, flush=True)
    link = response['data']['link']
    return link

#====not usually good, but go ahead and declare a global scope for thebeat

@csrf_exempt
@require_http_methods(['GET', 'POST'])
def payment_response(request):

    """Handle payment response from Flutterwave"""
    status = request.GET.get('status', None)
    tx_ref = request.GET.get('tx_ref', None)
    print(status)
    print(tx_ref)

    #===get the beat using the global scope
    beat = get_object_or_404(Beat, pk=beat_id_global)
    #the above gets me the beat object.
    if status == "successful":
        #===if purchase successful go ahead and download the beat.
        #Assuming payment is successful, create transaction
        Transaction.objects.create(
            buyer=request.user.buyer_profile or "josh",
            beat=beat,
            amount=beat.price,
            status='completed'
        )

        #Mark beat as downloaded
        beat.mark_as_downloaded()

        

        #Redirect to download view

   
       
        return redirect('download_beat', beat.id)
        #take it where it can be downloaded.
    else:
        #==must tell users to try again and pay.
        pass

        
#====new function to handle processing th
def purchase_and_download_beat(request,beat_id):
    """Combine purchase and download in one view"""
    global beat_id_global #so i have made beat_id a global variable that meaans i can access it anywhere
    beat = get_object_or_404(Beat, pk=beat_id)

    #===go ahead and update the global scope so that the beat_id is stored.
    
    beat_id_global = beat.id
    #==i have the beat_id here

    if request.method == 'POST':
        #Process payment logic here (omitted for brevity)
        #====let me go ahead and work on the process payment function====
        payment_link = process_payment(
            request,"josh", "beat@beat.com",
        )
        #====i dont need to pass the beat id from here because i only intend to handle payments.
        return redirect(payment_link)#====now we are redirecting to start on the payment
    else:
            # For GET request, show purchase confirmation page
        # Create a simple purchase confirmation template
        return render(request, 'main/purchase_confirm.html', {
            'beat': beat,
            'price': beat.price,
        })  



        

# Create your views here.
#allowed file types.
AUDIO_FILE_TYPES = ['wav', 'mp3', 'ogg']
IMAGE_FILE_TYPES = ['png', 'jpg', 'jpeg']



#index page
def index(request):
    albums = Album.objects.all()
    beat_results = Beat.objects.all()
    query = request.GET.get("q")
    if query:
        albums = albums.filter(
            Q(title__icontains=query) |
            Q(genre__icontains=query)
        ).distinct()
        beat_results = beat_results.filter(
            Q(title__icontains=query)
        ).distinct()
        return render(request, 'main/index.html', {
            'albums': albums,
            'beats': beat_results,
        })
    else:
        return render(request, 'main/index.html', {'albums': albums})



def detail(request, album_id):
    album = get_object_or_404(Album, pk=album_id)
    beats = album.beats.all()  # This uses the reverse relationship
    return render(request, 'main/detail.html', {'album': album, 'beats': beats})


def favorite(request, beat_id):
    beat = get_object_or_404(Beat, pk=beat_id)
    try:
        if beat.is_favorite:
            beat.is_favorite = False
        else:
            beat.is_favorite = True
        beat.save()
    except (KeyError, Beat.DoesNotExist):
        return JsonResponse({'success': False})
    else:
        return JsonResponse({'success': True})


def favorite_album(request, album_id):
    album = get_object_or_404(Album, pk=album_id)
    try:
        if album.is_favorite:
            album.is_favorite = False
        else:
            album.is_favorite = True
        album.save()
    except (KeyError, Album.DoesNotExist):
        return JsonResponse({'success': False})
    else:
        return JsonResponse({'success': True})

