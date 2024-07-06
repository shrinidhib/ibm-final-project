from django.contrib.auth.models import User
from django.contrib.auth import logout, login, authenticate
from django.http import JsonResponse
import logging
import json
from django.views.decorators.csrf import csrf_exempt

from .models import CarMake, CarModel
from .populate import initiate
from .restapis import get_request, analyze_review_sentiments, post_review

# Get an instance of a logger
logger = logging.getLogger(__name__)

# Create your views here.

@csrf_exempt
def login_user(request):
    """Handle sign-in requests"""
    data = json.loads(request.body)
    username = data['userName']
    password = data['password']
    
    user = authenticate(username=username, password=password)
    response_data = {"userName": username}
    
    if user is not None:
        login(request, user)
        response_data["status"] = "Authenticated"
    
    return JsonResponse(response_data)

def logout_request(request):
    """Handle logout requests"""
    logout(request)
    return JsonResponse({"userName": ""})

@csrf_exempt
def registration(request):
    """Handle sign-up requests"""
    data = json.loads(request.body)
    username = data['userName']
    password = data['password']
    first_name = data['firstName']
    last_name = data['lastName']
    email = data['email']
    
    try:
        User.objects.get(username=username)
        return JsonResponse({'username': username, 'error': "Already Registered"})
    except User.DoesNotExist:
        logger.debug(f'{username} is a new User')
        user = User.objects.create_user(
            username=username, 
            first_name=first_name, 
            last_name=last_name, 
            password=password, 
            email=email
        )
        login(request, user)
        return JsonResponse({'username': username, 'status': 'Authenticated'})

def get_cars(request):
    """Retrieve car models"""
    if CarMake.objects.count() == 0:
        initiate()
    
    car_models = CarModel.objects.select_related('car_make')
    cars = [{"CarModel": car_model.name, "CarMake": car_model.car_make.name} for car_model in car_models]
    
    return JsonResponse({"CarModels": cars})

def get_dealerships(request, state="All"):
    """Render list of dealerships"""
    endpoint = "/fetchDealers" if state == "All" else f"/fetchDealers/{state}"
    dealerships = get_request(endpoint)
    return JsonResponse({"status": 200, "dealers": dealerships})

def get_dealer_reviews(request, dealer_id):
    """Fetch reviews for a given dealer"""
    if dealer_id:
        endpoint = f"/fetchReviews/dealer/{dealer_id}"
        reviews = get_request(endpoint)
        for review_detail in reviews:
            response = analyze_review_sentiments(review_detail['review'])
            review_detail['sentiment'] = response['sentiment']
        return JsonResponse({"status": 200, "reviews": reviews})
    return JsonResponse({"status": 400, "message": "Bad Request"})

def get_dealer_details(request, dealer_id):
    """Fetch details for a given dealer"""
    if dealer_id:
        endpoint = f"/fetchDealer/{dealer_id}"
        dealership = get_request(endpoint)
        return JsonResponse({"status": 200, "dealer": dealership})
    return JsonResponse({"status": 400, "message": "Bad Request"})

def add_review(request):
    """Add a review for a dealer"""
    if not request.user.is_anonymous:
        data = json.loads(request.body)
        try:
            post_review(data)
            return JsonResponse({"status": 200})
        except Exception as e:
            logger.error(f"Error in posting review: {e}")
            return JsonResponse({"status": 401, "message": "Error in posting review"})
    return JsonResponse({"status": 403, "message": "Unauthorized"})
