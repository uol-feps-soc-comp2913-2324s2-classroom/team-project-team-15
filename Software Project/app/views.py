from app import app
from flask import render_template, redirect, url_for, request, flash
from app.models import
from app.forms import 
from sqlalchemy import func
from app import db



@app.route('/')
def index():
   
    