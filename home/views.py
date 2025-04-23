from django.shortcuts import render


def index(request):
    """
    View for the home page (front page of the site)
    """
    return render(request, 'home/index.html')


def about(request):
    """
    View for the about page
    """
    return render(request, 'home/about.html')


def contact(request):
    """
    View for the contact page
    """
    return render(request, 'home/contact.html')