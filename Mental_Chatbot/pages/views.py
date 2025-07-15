from django.shortcuts import render

# Create your views here.
from django.shortcuts import render

# Create your views here.
from django.shortcuts import render
from django.shortcuts import render, redirect 
from src.helper import download_hugging_face_embeddings
from langchain_pinecone import PineconeVectorStore
from langchain_openai import OpenAI
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from src.prompt import *
import os

 

load_dotenv()

PINECONE_API_KEY=os.environ.get('PINECONE_API_KEY')
OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY')

os.environ["PINECONE_API_KEY"] = PINECONE_API_KEY
os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY

embeddings = download_hugging_face_embeddings()


index_name = "mentalbot"

# Embed each chunk and upsert the embeddings into your Pinecone index.
docsearch = PineconeVectorStore.from_existing_index(
    index_name=index_name,
    embedding=embeddings
)

retriever = docsearch.as_retriever(search_type="similarity", search_kwargs={"k":3})


llm = OpenAI(temperature=0.4, max_tokens=500)
prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system_prompt),
        ("human", "{input}"),
    ]
)

question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)


 


from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse,HttpResponse
from django.views.decorators.csrf import csrf_exempt
import json



def home (request):
    return render (request, 'index.html')


def chatbot_page(request):
    return render(request, 'chat.html')

def get_response(request):
    if request.method == 'POST':
        msg = request.POST.get('msg')
        if msg:
            response = rag_chain.invoke({"input": msg})
            return HttpResponse(response["answer"])
    else:
        return HttpResponse("Invalid request")


def booking ( request):
    return render (request, 'book.html')



#boioking view
# pages/views.py
from django.shortcuts import render
from django.core.mail import send_mail
from django.http import HttpResponse
from datetime import datetime, timedelta
from .models import Booking, TIME_SLOTS
from .forms import BookingForm

def get_available_time_slots(date):
    booked_times = Booking.objects.filter(date=date).values_list('time', flat=True)
    return [(time, label) for time, label in TIME_SLOTS if time not in booked_times]

def book_view(request):
    date_str = request.POST.get('date') or request.GET.get('date')
    date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.today().date()
    available_slots = get_available_time_slots(date)
    fully_booked = len(available_slots) == 0

    if request.method == 'POST':
        form = BookingForm(request.POST, available_slots=available_slots)
        if form.is_valid():
            booking = form.save()
            send_mail(
                'Booking Confirmed',
                f'Your booking for {booking.date} at {booking.time} is confirmed.',
                'noreply@example.com',
                [booking.email]
            )
            return render(request, 'booking_success.html', {'booking': booking})
    else:
        form = BookingForm(available_slots=available_slots)

    return render(request, 'book.html', {
        'form': form,
        'date': date,
        'fully_booked': fully_booked,
        'next_day': date + timedelta(days=1)
    })

# HTMX partial view
def load_time_slots(request):
    date_str = request.GET.get('date')
    date = datetime.strptime(date_str, "%Y-%m-%d").date()
    available_slots = get_available_time_slots(date)
    form = BookingForm(available_slots=available_slots)
    return render(request, 'time_slots.html', {'form': form})

from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import messages

def send_message(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        full_message = f"From: {name} <{email}>\n\nMessage:\n{message}"

        try:
            send_mail(
                subject,
                full_message,
                email,  # From email
                ['alphaastudios92@gmail.com'],  # Replace with your receiving email
                fail_silently=False,
            )
            messages.success(request, "Your message was sent successfully.")
        except Exception as e:
            messages.error(request, "There was an error sending your message.")

        return redirect('home')  # Or wherever you want to redirect
    else:
        return redirect('home')

