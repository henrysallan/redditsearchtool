import functions_framework
from flask import Flask

@functions_framework.http
def hello_world(request):
    return 'Hello, Firebase Functions!'