from django.urls import path
from .views import FreeSlotsView, CarEntryView, CarExitView

urlpatterns = [
    path("slots/", FreeSlotsView.as_view(), name="free_slots"),
    path("entry/", CarEntryView.as_view(), name="car_entry"),
    path("exit/", CarExitView.as_view(), name="car_exit"),
]
